#!/bin/sh
# dyad installer (d-work #721; plan 721 revisions 1 and 2; dyad/surface.md S9). POSIX sh, published as the release
# asset `install.sh` of a core Release (`dyad-operator-vX.Y.Z`), its sha256 in that Release's text and note.
#
#   curl -fsSLO https://github.com/<owner>/<repo>/releases/download/<tag>/install.sh   # then check its sha256
#   sh install.sh [--dir <path>] [--repo <url>] [--yes] [--no-launch] [--rc-name <name>]
#                 [--tag <tag>] [--release-repo <owner>/<repo>] [--archive <path> --sha256 <hex>]
#                 [--attention-clone <path>]
#
# It brings a host from nothing to a running maintenance unit, doing nothing a `dyad` verb already does:
#   1. checks git, a Python 3.12+ (the kernel pin, Rule-14 property 2), claude, and curl when it fetches;
#   2. asks two things, each with a default, from /dev/tty so `curl ... | sh` still asks: the directory (default the
#      cwd), and a URL to clone into it or none to reuse the checkout there; `--dir`, `--repo` and `--yes` answer them;
#      with no URL, a missing directory or one that is not a git checkout is created and `git init`ed, its path named
#      first (d-work #734);
#   3. where the directory holds no `dyad/`, fetches the release archive and its note, checks the archive's sha256
#      against the note before the core is written (a clone, when asked, comes first), and runs the archive's own `dyad/bin/dyad install <dir> --from <archive>`,
#      the one install path (Rule-11 property 5);
#   4. writes the launcher `<git common dir>/dyad-launch`, rewritten only when its bytes differ, so a second run
#      changes nothing; it runs claude in the directory with `$DYAD_CLAUDE_FLAGS` (default
#      `--dangerously-skip-permissions --resume --chrome`) and `--remote-control <rc-name>` (default `maintain`, the
#      maintenance unit's provisional name, its final name taken at registration, #728), passing `--resume` only once
#      its marker `<git common dir>/dyad-launched` exists, so a first launch never opens the session picker; the
#      first launch alone ends with the seed prompt, the installer's standing instruction to run the first-boot
#      play-book (`dyad/playbooks/first-boot.md`, #728), never an operator prompt: it opens no row and is recorded nowhere;
#   5. names what to attend, then execs the launcher; under `--no-launch` (E2: an app session's agent installing into
#      its own working directory) it starts nothing and that session continues as the maintenance unit, at the
#      play-book's step 2.
# `--attention-clone <path>` (or `DYAD_ATTENTION_CLONE`) writes `git config dyad.attention.clone` in the checkout,
# never a tracked file, so the central repository's name is never asked in chat (#728, plan F4).
#
# Run by an agent it is a reversible host action (Rule-8), authorized by the plan-Y that names it. Undo: remove
# `<git common dir>/dyad-launch` and `<git common dir>/dyad-launched`; for a fresh install, `git checkout` and
# `git clean` exactly the paths `dyad install` printed; for a clone, remove the directory.
# For a directory it initialized, remove its `.git`. For `--attention-clone`: `git config --unset dyad.attention.clone`.
set -eu

# RELEASE_TAG and RELEASE_REPO (<owner>/<repo>) are stamped by `dyad release` when it publishes this file (release.py)
RELEASE_TAG=''
RELEASE_REPO=''
DEFAULT_FLAGS='--dangerously-skip-permissions --resume --chrome'
SEED=$(echo 'This session is the maintenance unit of the dyad system installed here: follow dyad/playbooks/first-boot.md.')

dir='' repo='' yes='' nolaunch='' rcname='maintain' tag="$RELEASE_TAG" relrepo="$RELEASE_REPO" archive='' want=''
clone=${DYAD_ATTENTION_CLONE-}
while [ $# -gt 0 ]; do
    arg=$1
    shift
    if [ "$arg" = --yes ]; then yes=1
    elif [ "$arg" = --no-launch ]; then nolaunch=1
    elif [ $# -lt 1 ]; then echo "install.sh: refused: unknown or incomplete argument $arg" >&2; exit 2
    elif [ "$arg" = --dir ]; then dir=$1; shift
    elif [ "$arg" = --repo ]; then repo=$1; shift
    elif [ "$arg" = --rc-name ]; then rcname=$1; shift
    elif [ "$arg" = --tag ]; then tag=$1; shift
    elif [ "$arg" = --release-repo ]; then relrepo=$1; shift
    elif [ "$arg" = --archive ]; then archive=$1; shift
    elif [ "$arg" = --sha256 ]; then want=$1; shift
    elif [ "$arg" = --attention-clone ]; then clone=$1; shift
    else echo "install.sh: refused: unknown argument $arg" >&2; exit 2
    fi
done

# 1. prerequisites
missing=''
git --version >/dev/null 2>&1 || missing="$missing git"
py=''
for cand in python3.13 python3.12 python3; do
    if [ -z "$py" ] && "$cand" -c 'raise SystemExit(__import__("sys").version_info[:2] < (3, 12))' >/dev/null 2>&1; then py=$cand; fi
done
pyname=python3.12+
[ -n "$py" ] || missing="$missing $pyname"
claude --version >/dev/null 2>&1 || missing="$missing claude"
if [ -z "$archive" ]; then curl --version >/dev/null 2>&1 || missing="$missing curl"; fi
if [ -n "$missing" ]; then echo "install.sh: refused: missing prerequisite(s):$missing" >&2; exit 1; fi

# 2. the two prompts, from /dev/tty unless --yes or a flag answers them
if [ -z "$yes" ] && { [ -z "$dir" ] || [ -z "$repo" ]; }; then
    if ! sh -c 'exec </dev/tty' 2>/dev/null; then
        echo "install.sh: refused: no terminal to ask the directory and clone-or-reuse - give --dir and --repo, or --yes" >&2
        exit 2
    fi
    if [ -z "$dir" ]; then
        printf 'install directory [%s]: ' "$PWD" >/dev/tty; read -r dir </dev/tty || dir=''
    fi
    if [ -z "$repo" ]; then
        printf 'clone a repository URL into it, or Enter to reuse the checkout there: ' >/dev/tty
        read -r repo </dev/tty || repo=''
    fi
fi
[ -n "$dir" ] || dir=$PWD

need=1
if [ -n "$repo" ]; then
    if [ -e "$dir" ] && [ -n "$(ls -A "$dir")" ]; then
        echo "install.sh: refused: $dir exists and is not empty - nothing cloned" >&2; exit 1
    fi
    git clone -q "$repo" "$dir"
fi
if [ -f "$dir/dyad/VERSION" ]; then need=''; fi
# with no --repo, a missing directory or one that is not a git checkout is initialized here, its path named first
# (d-work #734): nothing in it is moved or overwritten, and the archive check below still runs before any other write
if ! git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
    mkdir -p "$dir"
    git init -q "$dir"
    echo "install.sh: initialized $dir as a new git checkout"
fi
# 3. fetch and verify before the core is written, when the directory will need it
tmp=''
if [ -n "$need" ]; then
    tmp=$(mktemp -d)
    if [ -z "$archive" ]; then
        if [ -z "$tag" ] || [ -z "$relrepo" ]; then
            echo "install.sh: refused: no release named - give --tag <tag> and --release-repo <owner>/<repo>" >&2; exit 2
        fi
        base="https://github.com/$relrepo/releases/download/$tag"
        archive="$tmp/dyad-${tag##*-v}.tar.gz"
        curl -fsSL -o "$archive" "$base/dyad-${tag##*-v}.tar.gz"
        curl -fsSL -o "$tmp/note.json" "$base/$tag.release.json"
        want=$("$py" -c 'print(__import__("json").load(open(__import__("sys").argv[1]))["sha256"])' "$tmp/note.json")
    fi
    if [ -z "$want" ]; then echo "install.sh: refused: --archive needs --sha256 <hex>" >&2; exit 2; fi
    got=$("$py" -c 'print(__import__("hashlib").sha256(open(__import__("sys").argv[1], "rb").read()).hexdigest())' "$archive")
    if [ "$got" != "$want" ]; then
        echo "install.sh: refused: archive sha256 $got is not $want - nothing written" >&2; exit 1
    fi
fi

dir=$(cd "$dir" && pwd -P)

if [ -n "$need" ]; then
    "$py" -c '__import__("tarfile").open(__import__("sys").argv[1]).extractall(__import__("sys").argv[2], filter="data")' "$archive" "$tmp/src"
    git init -q "$tmp/src"
    "$tmp/src/dyad/bin/dyad" install "$dir" --from "$archive"
    git -C "$dir" config core.hooksPath dyad/hooks
else
    echo "install.sh: $dir holds dyad/ $(cat "$dir/dyad/VERSION"), not reinstalled"
fi
[ -z "$tmp" ] || rm -rf "$tmp"
if [ -n "$clone" ]; then
    git -C "$dir" config dyad.attention.clone "$clone"
    echo "install.sh: the attention clone is set in this checkout's git config (dyad.attention.clone), no tracked file"
fi

# 4. the launcher, written only when its bytes differ
gcd=$(cd "$dir" && cd "$(git rev-parse --git-common-dir)" && pwd -P)
flags=${DYAD_CLAUDE_FLAGS-$DEFAULT_FLAGS}
first=''
for f in $flags; do [ "$f" = --resume ] || first="$first $f"; done
q=$(printf '%s' "$dir" | sed "s/'/'\\\\''/g")
rq=$(printf '%s' "$rcname" | sed "s/'/'\\\\''/g")
launcher="$gcd/dyad-launch"
new="$launcher.new"
mq=$(printf '%s' "$gcd" | sed "s/'/'\\\\''/g")
printf '#!/bin/sh\n' >"$new"
printf '# dyad launcher, written by install.sh (d-work #721), run by path and never from PATH\n' >>"$new"
printf 'set -eu\n' >>"$new"
printf "cd '%s'\n" "$q" >>"$new"
# #747 (fix C2): the unit's provisional name, never an inherited one and never none, so first-boot's `name`
# step has the function it reads (an empty DYAD_SESSION made it exit 2)
printf "DYAD_SESSION='%s'\n" "$rq" >>"$new"
printf 'export DYAD_SESSION\n' >>"$new"
printf "marker='%s/dyad-launched'\n" "$mq" >>"$new"
printf 'if [ -e "$marker" ]\n' >>"$new"
printf "then set --%s --remote-control '%s'\n" " $flags" "$rq" >>"$new"
printf "else set --%s --remote-control '%s' '%s'\n" "$first" "$rq" "$SEED" >>"$new"
printf '    printf "" >"$marker"\n' >>"$new"
printf 'fi\n' >>"$new"
printf 'echo "launch: claude $*"\n' >>"$new"
printf 'exec claude "$@"\n' >>"$new"
if [ -f "$launcher" ] && [ "$(cat "$launcher")" = "$(cat "$new")" ]; then
    rm -f "$new"
    echo "install.sh: launcher $launcher unchanged"
else
    mv "$new" "$launcher"
    chmod +x "$launcher"
    echo "install.sh: launcher $launcher written"
fi

# 5. what to attend, then launch
if [ -n "$nolaunch" ]; then
    echo "install.sh: this session is the maintenance unit, next follow dyad/playbooks/first-boot.md from its step 2 (#728)"
    exit 0
fi
echo "open the app and attend $rcname"
exec "$launcher"

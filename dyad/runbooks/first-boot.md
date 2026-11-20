# Run-book: first-boot (the maintenance unit's first acts) — play-book `dyad/playbooks/first-boot.md`, #728
# sections: Report, Name, Attention, Commit, Home, Relay

A core run-book (agent zone): the first-boot play-book's commands, run by the maintenance unit through the core runner
from the root of the installed checkout, each recording an event in `<runbooks>/events/first-boot.jsonl`. `UNIT` names
the unit (`maintain-<hp>`), `ROW` the first row, `HOME_UNIT` the home's unit name.

```text
dyad runbook run first-boot report
UNIT=maintain-0123abcd ROW=1 dyad runbook run first-boot commit-zones
```

## Report
What was installed, for the greeting (play-book step 1):
```dyad-cmd
name: report
class: read-only
role: any
undo: none
postcondition: none
scope: the installed tree and its registry (read)

dyad/bin/dyad craft list && git rev-parse --show-toplevel && git status --short | wc -l
```

## Name
The unit's name from the harness session (play-book step 2):
```dyad-cmd
name: name
class: read-only
role: any
undo: none
postcondition: none
scope: the environment (read)

dyad/bin/dyad session name
```

## Attention
The first sync, only when the checkout names a clone (play-book step 2):
```dyad-cmd
name: attention
class: reversible
role: any
undo: none, the central repository's entries are append-only references; a later sync derives them again
postcondition: ! git config --get dyad.attention.clone >/dev/null || dyad/bin/dyad attention >/dev/null
scope: the central repository the checkout's git config names (never a tracked path)

if git config --get dyad.attention.clone >/dev/null; then DYAD_SESSION="${UNIT:?maintain-<hp>}" dyad/bin/dyad attention sync --since "$(git rev-list --max-parents=0 HEAD | tail -1)"; else echo "attention: this checkout names no central repository; not registered"; fi
```

## Commit
The installed tree, one zone per commit, on a local branch (play-book step 3a; the plan-`Y` authorizes it). On a
repository whose `main` is unborn the step first makes `main` one empty root commit, so the first row's done-`Y` has a
`main` to merge `first-boot` into with `--no-ff` (#747):
```dyad-cmd
name: commit-zones
class: reversible
role: any
undo: git checkout main && git branch -D first-boot
postcondition: git diff --quiet && git diff --cached --quiet
scope: the local branch first-boot (repo transactions, Rule-1)

{ git rev-parse -q --verify refs/heads/main >/dev/null || { git symbolic-ref HEAD refs/heads/main && git update-ref refs/heads/main "$(git commit-tree "$(git mktree </dev/null)" -m "first boot: the root commit main starts from, so the first row's done-Y has a main to merge into (d-work #${ROW:?1})")"; }; } && git checkout -B first-boot && git add -A && python3 -c "import sys,subprocess,collections; sys.path.insert(0,'dyad/guards/infra'); import containment as c; ps=subprocess.run(['git','diff','--cached','--name-only'],capture_output=True,text=True).stdout.split(); g=collections.defaultdict(list); [g[c.classify(p)].append(p) for p in ps]; subprocess.run(['git','reset','-q']); [(subprocess.run(['git','add','--']+v,check=True), subprocess.run(['git','commit','-q','-m',f'first boot: install, {z} zone (d-work #'+'${ROW:?1}'+')'],check=True)) for z,v in sorted(g.items())]"
```

## Home
The home's launcher, of the maintenance launcher's form: its own marker, `--remote-control program`, and on its first
launch a seed that points the home at its inbox in place of the first-boot play-book (play-book step 3b, a terminal or
local host). The start runs it in the background; the launcher execs claude, so the postcondition looks for that
process. Whether a background claude with no terminal starts is unverified (plan F2): if it does not, the step stops
and the home's start is delivered as an ops script (Rule-18).
```dyad-cmd
name: home-launcher
class: reversible
role: any
undo: rm "$(git rev-parse --git-common-dir)/dyad-launch-home"
postcondition: test -x "$(git rev-parse --git-common-dir)/dyad-launch-home"
scope: <git common dir>/dyad-launch-home

g=$(git rev-parse --git-common-dir); sed "s/--remote-control '[^']*'/--remote-control 'program'/; s/^DYAD_SESSION='[^']*'\$/DYAD_SESSION='program'/; s#dyad-launched#dyad-launched-home#; s#'This session is the maintenance unit[^']*'#'Read your inbox: this session is the home of the dyad system installed here, and its first message is the configuration batch to ask.'#" "$g/dyad-launch" > "$g/dyad-launch-home" && chmod +x "$g/dyad-launch-home"
```

```dyad-cmd
name: home-start
class: reversible
role: any
undo: stop the home's claude process (its pid is printed)
postcondition: ps -eo args | grep -q "[c]laude .*--remote-control program"
scope: one background process on this host

g=$(git rev-parse --git-common-dir); nohup "$g/dyad-launch-home" >"$g/dyad-home.log" 2>&1 & echo "home: pid $!"
```

## Relay
The configuration handed to the home (play-book step 5):
```dyad-cmd
name: relay
class: read-only
role: any
undo: none
postcondition: none
scope: the inbox of HOME_UNIT (a ledger-only commit)

DYAD_SESSION="${UNIT:?maintain-<hp>}" dyad/bin/dyad inbox post "${HOME_UNIT:?program-<hp>}" --row "${ROW:?1}" --kind relay "First boot: the install is committed and this unit is registered. Ask the configuration batch: every preference the operator has not set, the template's defaults shown, and the playground offer beside them."
```

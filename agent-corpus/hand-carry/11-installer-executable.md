# Hand-carry: an installer executable for the dyad core craft

**To** `pltrinh1122/dyad-system` (ptolemy) · **From** the steward of `The-Dyad-Practice-Commons/the-dyad-system`
· **Operator** common to both · **Reference base** `7f8e1cc` (core `VERSION` 1.6.1)

*Recorded under d-work #11 after the fact: the operator carried this text to ptolemy from the reply that
proposed it, and ptolemy opened its row #756 (`installer-py`, `planned`, `Y intent; Y plan`) against it before
this file existed. It is written here unchanged, as the baseline the steward's review of ptolemy's offer is
checked against — a brief held only by the party being reviewed is no brief (plan #11, step 1).*

## 1. What is wanted, in the operator's words

> we need an installer "executable" (.py) that is a full running automaton that will understand the current
> installation steps and recover and clean.  it also needs to be idempotent.  in the world of windows, it was
> the "installer.exe" or "setup.exe"

One `.py` file a stranger fetches from a core Release and runs on an empty machine. **"Automaton" here is the
plain sense, and deliberately not this system's term** — the vocabulary's automaton executes a `Y` the ledger
already holds, and an installer runs before any ledger exists. Build the gloss the same entry gives:
*automatic, not autonomous.* One command, no second question, no human judgement in the middle.

## 2. What exists today

`dyad/scripts/install.sh`, 186 lines of POSIX sh, published as the release asset `install.sh` with its sha256
in the Release text and note. Five steps: prerequisites (git, Python 3.12+, claude, curl); two questions from
`/dev/tty` (directory, clone-or-reuse); fetch the archive, verify its sha256 against the note, run the
archive's own `dyad/bin/dyad install`; write `<git common dir>/dyad-launch`, rewritten only when its bytes
differ; name what to attend and `exec` the launcher.

Read before you write: `dyad/surface.md` (the `installer` row — **frozen**, with every flag and variable it
must keep), `dyad/tests/test_installer.py` (224 lines, the contract in tests), `dyad/dmc/install-refusal.jsonld`
(when an install must refuse rather than proceed — also frozen), `crafts/sysadmin/rules/host-install.md`
(prerequisites, verification before the act, authorization and record, postcondition) and
`crafts/sysadmin/dmc/install-step-class.jsonld` (how each step is classed read-only / reversible / destructive).

## 3. The six recovery cases — all drawn from one real install

These are not hypotheticals. They are what happened on this operator's machine on 2026-11-20, which is why
this row exists at all.

1. **No tree.** The directory holds no `dyad/`. Install.
2. **Tree, no launcher.** `dyad/` present, `<git common dir>/dyad-launch` missing. Write it.
3. **Launcher, no marker.** The launcher exists, `dyad-launched` does not, so the first launch would pass
   `--resume` and open a session picker instead of the seed prompt.
4. **An `origin` that exists and is empty.** `land.fetch` branches on `has_origin` alone: with no origin it
   uses the local `main`, but an origin that exists with no `main` takes the fetch path and dies on
   `fatal: couldn't find remote ref refs/heads/main`. **This is the fault that broke this system's first boot
   at step 5** — no ledger-only write could reach `main`, the install stopped, and a human had to notice.
   Detect and complete it.
5. **An install left on a branch**, `main` at its root commit, zone commits stranded on `first-boot`. Report
   the exact state and finish the landing.
6. **A home that ran one turn and exited.** Started without a tty, so the CLI takes its `--print` path; the
   postcondition cannot tell a one-turn process from a persisting one. Either start it correctly or say that a
   terminal is required — never report success.

Every case: **read, report what you found, then act.** Print the state before changing it. No destructive step
automatic — a step `install-step-class` cannot class must refuse and say so, per `install-refusal`.

## 4. The clean set

`--clean` must execute what is today only a comment in the script's header: the launcher and its marker (both
`dyad-launch*`), `git config --unset dyad.attention.clone`, a `.git` the installer itself created, the exact
paths `dyad install` printed, and **the installer's own logs**. On that last point, look at this operator's
home directory: nine stray `*.sh` and `*.log` files from five different rows across four systems, because ops
scripts are run from a terminal and a terminal opens in `~`, and nothing says where a script runs from or
where its log goes. An installer that litters and cannot sweep is half the complaint.

## 5. Idempotence

A second run reports `0 changes` — the discipline is already written:
`crafts/syseng/rules/idempotence.md`.

## 6. Acceptance criteria — commands, with expected output

The steward will review against these, run in a clone of your fork. Adjectives are not acceptance.

```
# 1. install on an empty directory, then again
python3 install.py --dir /tmp/t1 --repo <url> --yes --no-launch    # installs, prints what it wrote
python3 install.py --dir /tmp/t1 --repo <url> --yes --no-launch    # "0 changes"
# 2. each of the six states of §3, broken deliberately, then
python3 install.py --dir /tmp/t1 --recover --yes                   # prints the state found, repairs, "0 changes" on a rerun
# 3. an unclassifiable state
python3 install.py --dir /tmp/t1 --recover --yes                   # refuses, names what it could not class, exit non-zero
# 4. clean
python3 install.py --dir /tmp/t1 --clean --yes                     # host reads as it did pre-install; a second --clean is "0 changes"
# 5. the contract
dyad check --tests dyad.tests.test_installer                       # green, extended for .py
dyad check --evidence                                              # fail=0 on your fork's head
```

## 7. The version — and the one thing not to do

`dyad/surface.md` marks `installer` **frozen**: removing, renaming or narrowing it needs a **major**; adding
beside it is a **minor**. So: **add `install.py` beside `install.sh`, and make it a minor.** `install.py` holds
the whole implementation; `install.sh` becomes a short bootstrap that finds the pinned Python — which it
already requires — and `exec`s `install.py` with every flag and variable unchanged (`--dir --repo --yes
--no-launch --rc-name --tag --release-repo --archive --sha256 --attention-clone`, `DYAD_CLAUDE_FLAGS`,
`DYAD_ATTENTION_CLONE`). One implementation, two entrypoints, no install contract broken, and the shell keeps
giving the readable refusal when Python is absent. **Do not delete `install.sh`** — that is a major, and it
belongs with the open proposal to retire `dyad-release.yml`.

**Amendment, after the operator's disposition of 2026-11-21** (recorded as #4 entry 5, and verified by the
steward against the guard): **carry no `dyad/VERSION` change at all** — no number, not even a proposed one. The
steward owns every version bump and release label. State the intended *level* in the PR body in words ("a
minor: it adds beside a frozen surface row"), which is the judgement the steward wants; the number is not.
Keep the `dyad/surface.md` row, which is the change describing itself. The mechanical reason this matters: once
`dyad-operator-v1.6.1` is tagged, a core tree differing from its tag under an unchanged `VERSION` **fails the
push** (`FAIL [guards] infra/bundle 'dyad-operator': dyad/ differs from tag … — bump VERSION`), observed by the
steward on 2026-11-21; narrowing that guard to the ref being pushed is the steward's row #13, and until it
lands a contributor's branch push passes only because the reference sits mid-cut.

## 8. The route

A pull request **from a fork** of `The-Dyad-Practice-Commons/the-dyad-system`, base `main`, one zone (agent —
everything under `dyad/`), commits citing your own ledger's row, plus a **`request` post on
`…/the-dyad-system-channels`** linking it and carrying the operator's words above. The steward reads the
channel, removes duplicates, and admits in the weekly batch or earlier on the operator's word; an admitted PR
is merged **as is, keeping you as its author**, revised only where it must be and with the reason said on the
PR.

Two warnings from the week of 2026-11-21, so you do not lose a day to them. The reference's pre-push gate
refused *every* contributor branch until `7f8e1cc` (a ledgerless base now warns instead of failing), so
**clone at or after `7f8e1cc`**. And `dyad-sweep.yml` fails on every push to the reference's `main` —
`refused: no run-book workstation-corpus/runbooks/automaton.md` — which is a known open defect, not yours, and
not a signal about your PR.

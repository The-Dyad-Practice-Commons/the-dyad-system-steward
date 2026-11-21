# Host change log (Rule-8)

One row per reversible or destructive host action, written in the same d-work. Read-only
actions are not logged. `actor` is `operator` or `agent` — the party whose hands executed
it; a divergent credential is named in `outcome`.

| date | d-work | class | action | undo | outcome | actor |
|------|--------|-------|--------|------|---------|-------|
| 2026-11-20 | #1 | reversible | write the home's launcher `<git common dir>/dyad-launch-home` (`dyad runbook run first-boot home-launcher`) | `rm "$(git rev-parse --git-common-dir)/dyad-launch-home"` | exit 0, postcondition ok; event: first-boot-20261120T204940Z-home-launcher | agent |
| 2026-11-20 | #1 | reversible | start the home's process in the background (`dyad runbook run first-boot home-start`) | stop the process (pid 701045); its presence file stays, the store's history | exit 0, postcondition ok; pid 701045 observed as `claude … --remote-control program` 30 s later; event: first-boot-20261120T204944Z-home-start | agent |
| 2026-11-21 | #5 | reversible | clone the reference (`The-Dyad-Practice-Commons/the-dyad-system`) into the session scratchpad and set `user.email`, `user.name` and `core.hooksPath dyad/hooks` in that clone, to reproduce D1 and D2 and to carry the fix's own push | `rm -rf "$SCRATCHPAD/d1/ref"` | the reproduction of plan #5's Observed section; then the fix branch, pushed from it with the hook active (`ok [guards] agent/prs transaction`), and `check --evidence` on the PR head (`bb508d98…`) and on the merge head (`d14006571…`). Taken before plan #5 was written, which that plan records as an incident | agent |
| 2026-11-21 | #5 | reversible | clone the reference again, at the merged `main` (`7f8e1cc`), for plan #5 step 6's demonstration, with `core.hooksPath dyad/hooks` and a contributor identity | `rm -rf "$SCRATCHPAD/demo/ref"` | exit 0, no FAIL line: a README commit citing no `d-work #N` is judged green and `git push --dry-run` reports `* [new branch] contrib/readme`. Nothing was pushed to the reference from it | agent |

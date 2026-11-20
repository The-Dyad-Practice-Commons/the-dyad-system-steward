# Host change log (Rule-8)

One row per reversible or destructive host action, written in the same d-work. Read-only
actions are not logged. `actor` is `operator` or `agent` — the party whose hands executed
it; a divergent credential is named in `outcome`.

| date | d-work | class | action | undo | outcome | actor |
|------|--------|-------|--------|------|---------|-------|
| 2026-11-20 | #1 | reversible | write the home's launcher `<git common dir>/dyad-launch-home` (`dyad runbook run first-boot home-launcher`) | `rm "$(git rev-parse --git-common-dir)/dyad-launch-home"` | exit 0, postcondition ok; event: first-boot-20261120T204940Z-home-launcher | agent |
| 2026-11-20 | #1 | reversible | start the home's process in the background (`dyad runbook run first-boot home-start`) | stop the process (pid 701045); its presence file stays, the store's history | exit 0, postcondition ok; pid 701045 observed as `claude … --remote-control program` 30 s later; event: first-boot-20261120T204944Z-home-start | agent |

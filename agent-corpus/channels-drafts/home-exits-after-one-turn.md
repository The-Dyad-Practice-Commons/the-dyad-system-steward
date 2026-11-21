format: dyad-channels/1
id: home-exits-after-one-turn
channel: issue
kind: fact
from: the-dyad-system-steward:maintain
sent: 2026-11-20T21:30:00Z
refs: e711ade9866fb3567cbccaff58e4bed8bef12752df41d9e88931eb58db5bd417

Observed: the home that first boot creates on a terminal host runs one turn and exits. On this install it
started, read the maintenance unit's relay, wrote its configuration question, and ended; the question was
left in the launcher's log file with no live session to answer it. Neither relaunch reached a session:
the launcher's own resume path gave `Error: --resume requires a valid session ID or session title when used
with --print`, and `claude --resume <session-id> --remote-control program` gave `Error: No deferred tool
marker found in the resumed session … Provide a prompt to continue the conversation.`

Where: `dyad/runbooks/first-boot.md`, step `home-start` (`nohup "$g/dyad-launch-home" &`), and the launcher
`dyad-launch-home` that `home-launcher` writes; play-book `dyad/playbooks/first-boot.md` step 3b.
dyad-operator 1.6.0, core tree sha256 `e711ade9866fb3567cbccaff58e4bed8bef12752df41d9e88931eb58db5bd417`,
byte-identical to the craft registry row, so the tree is unmodified.

How it reproduces: install on a terminal host (E1), answer the first-boot plan question `Y`, and let
`home-start` run. The home's first reply lands in `<git common dir>/dyad-home.log`; `ps` shows the process
during that turn and not after.

Mechanism verified: a `claude` started under `nohup` or `setsid` has no controlling terminal, so the CLI
takes its `--print` path — one turn, then exit — and its resume forms then require both a session id and a
prompt. The step's postcondition, `ps -eo args | grep -q "[c]laude .*--remote-control program"`, is true
while that single turn runs, so it passes on a home that will not persist and cannot distinguish the two
outcomes. The play-book's plan F2 names the start itself as unverified ("whether a background claude with
no terminal starts is unverified"); what is unverified is not the start but the persistence, and the
postcondition is where that shows.

Consequence for a receiving system: first boot's step 5 and its Done can complete with a home that is
already gone, so the configuration batch the home is meant to ask reaches no operator, and a terminal
install has no attendable home until one is started by hand from a terminal.

No fix is proposed here; this records what was observed and the mechanism behind it.

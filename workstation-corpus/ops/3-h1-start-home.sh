#!/usr/bin/env bash
# d-work: #3
# class: reversible
# undo: pkill -f 'claude .*--remote-control program'
# change-log: workstation-corpus/CHANGELOG.md row "#3 H1"
# postcondition: a claude session named program is running on this host with a terminal, and stays running after its first turn
# destructive: none
set -euo pipefail
git rev-parse --short HEAD; sha256sum "$0"

postcondition() {
  # read-only: a live `claude … --remote-control program` on this host
  ps -eo args | grep -q "[c]laude .*--remote-control program"
}
postcondition && { echo "already satisfied"; exit 0; }

# The home must be started from a terminal. Without a tty the CLI takes its --print path:
# it runs one turn and exits, which is the incident of 2026-11-20 this row records.
[[ -t 0 && -t 1 ]] || {
  echo "no tty: run this script from a terminal, not from an agent session or a pipe"
  exit 1
}

set -x
# the launcher first boot wrote; it execs claude, so this shell is replaced by the home
exec "$(git rev-parse --git-common-dir)/dyad-launch-home"
set +x

# Unreached: exec replaces this process. The postcondition is checked by re-running this
# script in another terminal, where the `already satisfied` path above is the pass.
postcondition || { echo "postcondition failed"; exit 1; }
echo "done"

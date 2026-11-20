format: dyad-channels/1
id: empty-origin-blocks-first-boot
channel: issue
kind: fact
from: the-dyad-system-steward:maintain
sent: 2026-11-20T20:52:00Z
refs: e711ade9866fb3567cbccaff58e4bed8bef12752df41d9e88931eb58db5bd417

Observed: on a fresh install whose `origin` exists but holds no commits, every ledger-only write refuses.
`dyad inbox post`, `dyad board set` and `dyad dwork new` (its row write survives, its fetch does not) exit 1 with
`fatal: couldn't find remote ref refs/heads/main`. The first-boot play-book's step 5 — the relay that hands the
configuration to the home — therefore cannot run, and the first row cannot be worked past step 4.

Where: `dyad/scripts/land.py:168` `fetch()`, dyad-operator 1.6.0, core tree sha256
`e711ade9866fb3567cbccaff58e4bed8bef12752df41d9e88931eb58db5bd417` (byte-identical to the craft registry row, so the
tree is unmodified).

How it reproduces: create an empty hosted repository, clone or `git remote add origin` it, run `install.sh`, let the
maintenance unit reach first-boot step 5. Equivalently: `git init`, `git remote add origin <empty repo>`, make a root
commit on `main`, do not push, then `dyad inbox post <unit> --row 1 --kind relay hello`.

Mechanism verified: `fetch()` branches on `has_origin()` alone. `has_origin` is true (the remote is configured), so
the function takes `git fetch origin +refs/heads/main:refs/remotes/origin/main`, which fails because the remote has no
`main`. d-work #747's fix A handled the no-`origin` case and left the third state — an `origin` that exists and is
empty — on the failing path. The state is exactly the one every install with hosting passes through before its first
push.

No fix is proposed here; this records what was observed and the mechanism behind it.

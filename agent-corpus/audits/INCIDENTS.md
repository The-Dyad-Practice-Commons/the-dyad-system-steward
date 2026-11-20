# Incidents (Rule-3)

One row per incident: what departed from the plan, why, and what it cost. Rows before
2026-09-12 #66 are backfilled from the session transcript and memory, and say so.

| date | d-work | what | cause | consequence |
|------|--------|------|-------|-------------|
| 2026-11-20 | #1 | first boot step 5 refused: `dyad inbox post` and `dyad board set` both exit 1 with `fatal: couldn't find remote ref refs/heads/main`, so the relay to the home and the board entry could not be written, and no ledger-only write can reach `main` on this install | `land.fetch` (`dyad/scripts/land.py:168`) branches on `has_origin` alone: with no `origin` it uses the local `main` (#747 fix A), but an `origin` that exists and is **empty** — a fresh install whose hosting was created and never pushed — takes the fetch path and fails. The case between "no hosting" and "hosting with a `main`" is unhandled | step 5 stopped and is reported here with its next step (first-boot play-book); the install sits on the local branch `first-boot`, five zone commits plus the plan's base commit, with `main` at its root commit. The core craft's tree is byte-identical to its craft registry `sha256` (`e711ade9…`), so the fix is upstream's as well as this system's (Rule-11 property 2); this system has **no channels membership** — no channels repository is known — so the drafted `issue` post is handed to the operator instead of posted (Rule-3 Incidents, #747) |

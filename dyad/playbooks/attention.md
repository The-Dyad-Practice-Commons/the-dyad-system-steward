# Play-book: the operator's attention (core craft, `dyad-operator`; #705)

How the home orders what reaches the operator. What is owed comes first; then the operator's standing goals rank the
choices; today's focus, the operator's mood, moves the order within that and fades. The criterion is
`dmc:attention-strategy`; this play-book says when the home reads and records each of its inputs. The mechanism is the
same for every operator. Each operator's goals, focus, settings and own overlay records are that operator's, kept in
the operator's store, never in a craft or the core. The order authorizes nothing: an item still becomes work only by
its own question or an operator prompt.

Steps with a command run through `dyad attention`; the rest are the home's inference, recorded before it is shown.

## The store
- **Where.** In the operator's central repository (#700), under `operator/`, when the checkout names one (`git config
  dyad.attention.clone`). Otherwise the goals and the settings live in `preferences-corpus/ATTENTION.md`, changed only by a
  preferences-zone PR the home presents as its own question, and the focus lives as the `focus` key on the home's
  cross-row board entry. The fallback is in this repository and so public: the home says so once, when the first goal
  is entered there.
- **What.** `goals.md` holds one block per goal, `## G<n> <long-term|intermediate> review <date>`, then the operator's words
  in a fenced body and a `status` line; ids are never reused. `focus.md` is append-only, one block per focus, stated or
  inferred. `settings.md` holds `key: value` lines. `dmc/` holds the operator's own overlay records.
- **Never copied.** A goal's words appear only in that store and in the chat. The board, a plan, a row and every other
  public record name a goal by its id, `G<n>`, alone.

## Steps
- **A1 Enter a goal.** Only on the operator's prompt naming a goal: `dyad attention goal add --horizon <h> --review
  <date> --said-file <f>`, the file holding the operator's words verbatim. The agent never composes a goal, and a goal
  the operator retires is marked `retired`, never deleted (`dyad attention goal retire G<n>`).
- **A2 Read today's focus.** At the home's first operator prompt of a UTC day, and whenever the operator states one. A
  stated focus, "today: …" or the like, is recorded as the operator's words (`dyad attention focus --said-file <f>`).
  With none stated, the home may record one inferred line from the day's prompts (`--inferred "<line>"`) and shows it
  once as "reading today's focus as …", for the operator to correct. An inferred focus is the home's reading, never the
  operator's words, and weighs `inferred-focus-weight`.
- **A3 Ground the candidates.** Before showing or proposing a row, the home records which goal it serves, `serves:` on its
  cross-row board entry, `#<id> G<n>|none (<reason>) @<ISO time>`, write-ahead. A line the row has changed past is
  re-recorded before it is used.
- **A4 Order.** `dyad attention order` prints the candidates in the criterion's order, each with its tier, its grounding
  and today's focus weight. Promotion and Recommended for next read the same order (their own records cite it).
- **A5 A focus that departs.** When today's stated focus matches only rows serving no goal, the home shows it once with
  the goals it departs from, so the operator adopts it as a goal (A1) or keeps it for today.
- **A6 Attention work, under the mandate.** Attention is back-office work: the ledger of what waits on the operator,
  which the operator owns and does not attend. Data writes (sync, replay, a re-run backfill, a pairing) are clerical
  and open no row (Rule-2 Not ratification). A fix to the ledger's own code is a row: filed `backlog` when found, its
  class read by `dmc:attention-work`. Under `attention-mandate: on`, at each sync failure, replay gap and weekly review
  the home reads `dmc:attention-due`, and opens a due row with `dyad dwork state <id> open --mandate-preference
  attention-mandate`, no intent or plan question asked, at most `attention-ceiling` in flight. A row whose plan fails
  A2–A4 is ordinary: the home reports it and asks every question (the escalate edge). Under `off` every attention row
  is asked as any row is (#707).
- **A7 Read the calendar.** At the home's first operator prompt of a day, and whenever a question would otherwise be
  held, the home reads the operator's bound calendar through the calendar connector its session holds (#740).
  - **The binding** is read from the central repository's `operator/settings.md` key `calendar.<work-owner>` (or
    `calendar`), else the checkout's `git config dyad.attention.calendar`. It is never written in a tracked file. The
    preference `work-owner` says whose work this is.
  - **Several bindings** (#749), one per calendar, are read from the checkout's git config,
    `dyad.attention.calendar.<name>` set to its modes and the calendar's id, which never leaves git config:
    `windows`, the calendar this step reads windows from; `busy`, a calendar read for its busy times only; and
    `write`, on one `windows` binding at most, the one calendar the home may write. How much of a calendar may be read
    at all is `dmc:calendar-access-direction`: another system's work calendar is read as busy times, start and end
    only, for the run that reads it, and never stored. `dyad attention bindings` prints each binding's name and modes.
  - **The daily overlap read** (#749). At the same first prompt of a day the home reads the busy times of every bound
    calendar through its connectors and passes them to `dyad attention overlaps --busy-file <f>`, one
    `<binding> <ISO start> <ISO end>` line each, which names every overlap between and within the calendars, compared
    in UTC, and stores nothing. An overlap is an owed question for the operator; nothing moves without one.
  - **A window** is an event carrying the operator's marker, the setting `calendar-marker` (default `dyad`). Only its
    start and end are read, and only the marker test reads its title.
  - **The window list** is written with `dyad attention windows --set-file <f>`, one `<ISO start> <ISO end>` line per
    window and one `horizon:` line. Any other text is refused, so no title, attendee or calendar id can reach the store.
    The store is the central repository's `operator/windows.md`, else an untracked file in the git common dir.
  - **Presenting.** Questions are then presented by `dmc:attention-calendar`. A red PR this unit owns, and a question an
    operator prompt asks for directly, are never held: the home presents them now, whatever the record reads, since
    the code that reads the record does not see them. `dyad attention calendar` prints the next
    windows, and the closing line names the next one when it holds a question.
  - **No calendar.** With no connector, no binding or a refusal, nothing is written, and every question is presented as
    before.
  - **Writing to the calendar**, a block held for a batch for example, is no host action (Rule-8: the machine). It is a
    change to the operator's own record outside the system, so it is its own question each time, written only on the
    operator's `Y` and never carried by a plan-`Y`; its undo is deleting the event. Under the preference
    `calendar-mandate: on` (#749; Rule-2 Binding) the home may create, move and delete events with no attendees on the
    one binding marked `write` with no question, each event marked as the home's and each reported in the next reply
    with its undo, and created with an explicit time zone. Never under the mandate: an event with attendees, an answer
    to an invitation, a change to an event the home did not make, or a write to any other calendar; each of those stays
    its own question.
- **A8 The brief** (#750). Every 15 minutes the home re-arms a self-check-in bound to its own session. Each firing
  builds the brief and writes it, overwritten, to the untracked file `<git common dir>/dyad-brief.md`. The brief has
  two halves:
  - **The mechanical half** comes from `dyad attention brief`: the questions waiting, by the unit whose chat holds
    each; blocked rows; done-ready rows; the PRs this unit owns that no longer merge onto `main`; unread inbox items;
    and the next attention window.
  - **The calendars' half** the home adds from its connectors, together with each PR's CI colour, which only the
    hosting knows.

  A firing replies in chat only when the brief changed **and** an item needs the operator within the hour; otherwise it
  ends silently. Each brief prints when it was made, and the time of the next firing. A gap past 20 minutes is named in
  the next reply the operator sees. Work-calendar content is read into a session and an untracked brief only, never
  into a tracked file (`dmc:calendar-access-direction`, D2). On a hop, the new holder re-arms the check-ins from the
  board's note.

## The weekly goal review
It rides the backlog grooming (`dyad/playbooks/backlog-groom.md`), whose report gains the `goals:` lines: each goal, its
review date (marked `overdue` when past), and the rows it served since the last review. It also carries the **uptake**
count: of the items recommended or promoted since the last review, how many the operator took up, by goal. Uptake is a
proxy for the strategy's effect, stated as a proxy. The count of replies per disposition (the cabinet Guide §12 item 7)
stays the measure of attention. A goal past its review date is shown to the operator once, for keeping, revising or
retiring, all by the operator's words. Under `attention-mandate: on` it also asks every attention Done held for it
as one batch Done question, and reports attention work in one line: rows
opened, delivered and in flight under the mandate since the last review.

## Defaults
With no goal recorded, every candidate is in one tier and today's order stands, moved only by focus, and the home says
once that no goals are recorded. A setting absent everywhere reads the criterion's default; `attention-conflict` reads
`goals-first`.

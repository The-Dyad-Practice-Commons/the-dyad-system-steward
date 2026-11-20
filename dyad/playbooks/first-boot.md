# Play-book: first boot (core craft, `dyad-operator`; #728, spec `installer-updater` C4)

What the maintenance unit does as its first act, the moment an install hands it a session. Run by the installer's
first launch (its seed prompt names this file) or, under E2, by the app session that ran `install.sh --yes
--no-launch`. Its commands are `dyad/runbooks/first-boot.md`, run as `dyad runbook run first-boot <step>`, each leaving
an event. Every other step is the agent's reading. A refused step stops: it is reported in this chat with its next
step, and retried only by a new `Y`.

The seed prompt is the installer's text, a standing instruction like the frame's import line. It is no operator prompt:
it opens no row and is never a provenance entry (Rule-7 property 4). The first row opens on the operator's `Y` to step
3's question.

## Entry points
- **E1, the terminal.** The installer's launcher started this session under the provisional remote-control name
  `maintain`. The operator attends it in the app.
- **E2, an app session.** The agent of an existing session (cloud, local or remote-control) ran the installer in its
  working directory. That session is the maintenance unit, and the operator is already in its chat.

## Steps
1. **Greet and report** — `report` (read-only). The first reply names the installed versions, the directory, the entry
   point, and what the unit will ask next. It asks nothing but the question of step 3. Where the system has no hosted
   repository others can read, so step 3(c) cannot register it as a member, the greeting says so, and that an upstream
   incident's drafted post will be handed to the operator, who may have any member system they attend post it under
   that system's own posting question (Rule-3 Incidents, #747).
2. **Take the unit name** — `name` (read-only), then `touch` once step 3's row exists.
   - The name is `maintain-<hp>`, from the harness session id. The function `maintain` is the cabinet's to define; until
     its charter row exists, the name form's reading warns, and that reading is advisory (Rule-16 Presence).
   - **The attention ledger** is registered only when the checkout already names a clone, which the installer writes
     into git config from its `--attention-clone` flag or `DYAD_ATTENTION_CLONE`: `attention` runs the first sync. With
     none named, one line says so. The unit never asks for the central repository's name in chat: the operator's answer
     would be recorded verbatim in a tracked provenance record (Rule-7 property 1).
3. **Ask one plan question** — the plan file written first as this system's first row's plan, then
   `Y/N: open and plan #1 first-boot as planned?`. Its mutation names, in this order:
   - (a) **the installed tree, committed one zone per commit** on a local branch `first-boot` — `commit-zones`. An
     install spans the agent, craft and infra zones, and the pre-commit hook refuses one commit across them (Rule-1).
     On a repository whose `main` is unborn the step first makes `main` one empty root commit, which touches no path
     and so is no change the main fence refuses (#747);
   - (b) **the home's creation**:
     - on a terminal or a local or remote-control host (E1, and E2 local), a second launcher of the first one's form,
       `--remote-control program`, started in the background — `home-launcher`, `home-start`;
     - in a cloud session (E2 cloud), a session made by the remote-session tools in the same environment;
   - (c) **the channels subscription and member registration**, by the channels craft's own play-book
     (`crafts/channels/playbooks/channel-member.md`). The craft is bundled with the core (#747), so every install has it,
     and the registration is what lets an incident whose fix lies upstream be reported there (Rule-3 Incidents);
   - (d) under E2 cloud, **the repository**, when the working directory has no remote the session can push to.

   Each host action is stated with its class and undo (Rule-8):

   | act | class | undo |
   |---|---|---|
   | write the home's launcher | reversible | remove it |
   | start the home's process | reversible | stop the process; its presence file stays, the store's history |
   | make a cloud session | reversible | archive it |
   | create the repository | reversible | its deletion is destructive and its own question |
   | the channels clone and member branch | reversible | remove the clone; close the member PR |
   | name the attention clone | reversible | `git config --unset dyad.attention.clone` |
4. **On `Y`, run them** in that order, each host action with its row in the change log (Rule-8), the log created from
   its template if absent. Commits on `first-boot` are repo transactions, not host actions (Rule-1). If the home's
   background start fails, the step stops and the unit delivers the start as an ops script the operator runs once
   (Rule-18).
5. **Hand the configuration to the home** — `relay`: one relay to the home's inbox naming the preferences whose values
   the operator has not set. The home's first message asks them as one batch, the template's defaults shown, with the
   playground offer beside them. The first row's Done is asked by this unit in the same batch window: its `merges`
   clause lands `first-boot` on `main` (Rule-2: a merge into `main` is ratified only by a done-`Y`). That is how the
   install reaches `main`: never by a direct commit, which the main fence refuses (Rule-3, Mechanisms), but by the
   `--no-ff` merge of `first-boot` the done-`Y` ratifies, executed locally when the repository has no hosting (Rule-14
   property 3).

## Evidence
The run-book's events, the plan file and the row; the change-log rows; the home's presence file once it registers.

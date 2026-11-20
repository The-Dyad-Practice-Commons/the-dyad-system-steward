# channels — messages between dyad systems over a shared repository (Tended craft, `crafts/channels/`, zone `craft`)

Dyad systems that install this craft subscribe to a shared, public channels repository and exchange messages there:
a release channel each upgrade is read from, request and back-port channels for enhancements and offered fixes, and
an issue channel for defects. A message carries information, never authority: what a system receives is an intake its
own operator admits or not (Rule-3 Intake). The craft defines the canonical message format, `dyad-channels/1`, kept
general — few required fields, any unknown field kept — so another system's records conform to it. Authored in
dyad-system under d-work #682, a clean-room implementation; it requires the core only (`MANIFEST.md`). Version
`VERSION` (0.2.0). Bundled with the core (Rule-11 property 2, criterion (a), d-work #747): Rule-3 (Incidents)
cites `playbooks/channel-post.md`, so every installed system can report an incident whose fix lies in a craft it
installed unmodified as an `issue` post upstream, each post asked as its own posting question. The declaration is
`BUNDLED_WITH_CORE` in `guards/posts.py`.

| path | holds |
|------|-------|
| `templates/message.md` | the message record, `channels/<channel>/<system>/<id>.md`: required `format`, `id`, `channel`, `kind`, `from`, `sent`; optional `holder`, `in-reply-to`, `refs`, `attachments` (each file `<name> <sha256> <bytes>`, held in `<id>/` beside the message; d-work #752); then the body |
| `templates/channel.md` | a channel's registry entry, `registry/channels/<channel>.md`: creator, owner, sources and the policy slots (admission, posting, monitor, limits, decision-rights), and the optional `visibility` (`public` or `private`) and `attachment-limit` |
| `templates/member.md` | a member's registry entry, `registry/members/<system>.md`: system, units, bound repository, play-book version |
| `guards/posts.py` | the guard (entity `post`, corpus `craft`), over the clone `<instance>/channels.local.txt` names (`clone:`): record shape, kinds, membership, replies, paths, size limits, attachments (sha256, size, listing, limit, binaries and personal data only on a private channel, the hosting's visibility where readable), append-only, and the world-facing fence (credentials, private names by hash, disposition shapes); its `check_text` is the check a post passes before it is written |
| `scripts/channels.py` | the verbs `subscribe`, `read` (by each channel's monitor slot; the marker under the git common dir), `post` (checked, printed, written on a branch with any `--attach` files, never pushed) and `breach` (findings on received messages, recorded by the agent) |
| `runbooks/channels.md` | the verbs as the run-book `channels:channels`, run through the core runner |
| `tests/` | the guard and the verbs |

# Fence (channels craft, Tended rule): the channels repository is public, unless it says otherwise

Read by `../guards/posts.py` (its `check_text`) and by every unit before it posts. Record:
`../falsification/rules/channels.md`. Source: dyad-system plan #682, revision 1 point 3 and revision 2 (M3, L1).

## 1. Everything posted is world-readable
A message holds only what every member may already read (M3), and the channels repository is public, so what it holds
anyone may read and keep. Hence, for this system:
- every post is shown to this system's operator whole before it is sent, and is sent only by a pull request merged on
  its own question;
- no post carries client data, personal data, a private repository's name or a credential (L1).

## 2. What the guard refuses, before any write
`check_text`, which the `post` step runs on a draft and the guard runs on every record, refuses:
1. a credential shape: the core provenance guard's list (`FAIL_SHAPES`), imported, never restated;
2. a private name: an `owner/repo` token whose sha256 the instance lists in `<instance>/private_repos.local.txt`, read
   by the core's `dyad/scripts/privatecite.py` (#518); the list holds hashes, so the names it protects are written
   nowhere, this craft and its tests included;
3. a disposition shape: the core inbox's `DISPOSITION` pattern, since a message carries no authority (`channels.md`
   §3).

## 3. What only reading catches
A private name written another way (in prose, misspelled, or as a description) or personal data in free text is not a
shape the guard can see. That is why every post is read whole before it is sent, and why a receiver who finds such a
slip records it as a breach (`channels.md` §5) and never quotes it back.

## 4. Attachments, and a private channel
A message may carry files (`channels.md` §1). The fence reads them as it reads a message (d-work #752):
1. every text attachment passes §2's three refusals, whatever the channel;
2. a binary attachment, which the guard cannot read, and a text attachment holding a personal-data shape (an email
   address, a phone number: `PERSONAL_SHAPES`), are admitted only on a channel whose entry says `visibility: private`
   (J2);
3. a `private` entry holds only while the hosting does not say the repository is public: the guard reads the hosting's
   own flag where the clone's `origin` answers and fails the entry on a mismatch; where it cannot be read, the entry is
   trusted and one warning says so (J1);
4. a message's attachments together stay within its channel's `attachment-limit`, by default small on a public
   channel (J3).
A transcript of a person, the case that asked for attachments, is therefore posted only to a private channel of a
private repository, and is read whole before it is sent like every post (§1, §3).

"""posts.py (the channels craft's guard, entity `post`; d-work #682): the absent checkout, the instance file naming the clone (relative and absolute), each template parsing to its
field list, a well-formed store, each failing shape (missing field, wrong format, unknown kind, id or channel off its
path, a channel with no entry, a sender off its path or no member, an unresolved reply, over the size limit, a policy
slot of no allowed value, a member entry naming another system, the content-rules slot: missing, malformed, without layer 1, naming a heading
CONTENT-RULES.md lacks, or with no CONTENT-RULES.md at all, and the member's adopted version), an unknown field kept, the fence (a credential, a
private name by hash, a disposition shape), append-only against the clone's origin, and the invariants; attachments
(d-work #752): listed files that match pass, an absent, changed, unlisted or unfielded file fails, the limit, the fence
on text, a binary and personal data refused off a private channel and admitted on one, the hosting's flag overruling a
`private` entry or trusted with a warning when unread, a file added under a landed message, and the field read back."""
import hashlib, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "dyad" / "scripts"))
import dyadlib
CRAFT = Path(__file__).resolve().parents[2]
posts = dyadlib.load_guard_file(CRAFT / "guards" / "posts.py")
pc = dyadlib.load_module(dyadlib.PKG / "scripts" / "privatecite.py", "privatecite")
CHANNEL = ("id: release\ncreator: up:home\nowner: up\nsources: up's releases\nadmission: open\nposting: members\n"
           "monitor: session-start\nlimits: 4 KiB, 10 per hour\ndecision-rights: none\n"
           "content-rules: CONTENT-RULES.md#post-content #release-post, channels 0.1.0\n\nReleases.\n")
MEMBER = "system: {s}\nunits: home\nbound-repository: private\nplay-book: 0.1.0\ncontent-rules: channels 0.1.0\n\nA system.\n"
RULES = "content-rules: channels 0.1.0\n\n# Content rules\n\n## post-content\n\nEvery post.\n\n## release-post\n\nA release.\n"

def message(mid="m1", channel="release", sender="up:home", kind="fact", body="A tag was cut.", **extra) -> str:
    head = {"format": "dyad-channels/1", "id": mid, "channel": channel, "kind": kind, "from": sender,
            "sent": "2026-11-11T00:00:00Z", **extra}
    return "".join(f"{k}: {v}\n" for k, v in head.items()) + "\n" + body + "\n"

class Store(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.base = self.root / "clone"
        (self.base / "registry" / "channels").mkdir(parents=True); (self.base / "registry" / "members").mkdir()
        (self.base / "registry" / "channels" / "release.md").write_text(CHANNEL)
        for s in ("up", "down"):
            (self.base / "registry" / "members" / f"{s}.md").write_text(MEMBER.format(s=s))
        (self.base / posts.RULES).write_text(RULES)
        (self.root / "agent-corpus").mkdir()
        (self.root / "agent-corpus" / posts.LOCAL).write_text("clone: clone\nsystem: up\n")
        env = {k: v for k, v in os.environ.items() if k != "DYAD_INSTANCE"}
        p = mock.patch.dict(os.environ, env, clear=True); p.start(); self.addCleanup(p.stop)

    def put(self, text, channel="release", system="up", mid="m1"):
        d = self.base / "channels" / channel / system; d.mkdir(parents=True, exist_ok=True)
        (d / f"{mid}.md").write_text(text)

    def fails(self):
        return [m for m in posts.check_package(self.root) if not m.startswith("warning:")]

class Absent(unittest.TestCase):
    def test_no_checkout_skips(self):
        root = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        with mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "DYAD_INSTANCE"}, clear=True):
            msgs = posts.check_package(root)
            self.assertIsNone(posts.store(root))
        self.assertEqual(len(msgs), 1); self.assertTrue(msgs[0].startswith("warning: skip posts"))

class Local(Store):
    def test_clone_relative_and_absolute(self):
        self.assertEqual(posts.store(self.root), self.root / "clone")
        (self.root / "agent-corpus" / posts.LOCAL).write_text(f"clone: {self.base}\n")
        self.assertEqual(posts.store(self.root), self.base); self.assertEqual(posts.local(self.root), {"clone": str(self.base)})

class Templates(unittest.TestCase):
    def test_message_template_fields(self):
        head, _ = posts.parse((CRAFT / "templates" / "message.md").read_text())
        self.assertEqual(tuple(head), posts.FIELDS + posts.OPTIONAL)
    def test_channel_template_fields(self):
        head, _ = posts.parse((CRAFT / "templates" / "channel.md").read_text())
        self.assertEqual(tuple(head), posts.CHANNEL_FIELDS + posts.CHANNEL_OPTIONAL)
    def test_member_template_fields(self):
        head, _ = posts.parse((CRAFT / "templates" / "member.md").read_text())
        self.assertEqual(tuple(head), posts.MEMBER_FIELDS)

class Shapes(Store):
    def test_good_store_passes_and_unknown_field_kept(self):
        self.put(message(extra_field="kept"))
        self.put(message(mid="r1", sender="down:home", kind="reply", **{"in-reply-to": "m1"}), system="down", mid="r1")
        self.assertEqual(self.fails(), [])
        self.assertIn("1 channel(s), 2 member(s), 2 message(s)", posts.summary(self.root))

    def test_missing_field(self):
        self.put(message().replace("sent: 2026-11-11T00:00:00Z\n", ""))
        self.assertTrue(any("lacks `sent:`" in m for m in self.fails()))

    def test_wrong_format_and_kind(self):
        self.put(message(kind="order").replace("dyad-channels/1", "dyad-channels/9"))
        f = self.fails()
        self.assertTrue(any("format" in m for m in f)); self.assertTrue(any("kind 'order'" in m for m in f))

    def test_id_and_channel_off_path(self):
        self.put(message(mid="other", channel="issue"), mid="m1")
        f = self.fails()
        self.assertTrue(any("id 'other'" in m for m in f)); self.assertTrue(any("channel 'issue'" in m for m in f))

    def test_channel_without_entry(self):
        self.put(message(channel="issue"), channel="issue")
        self.assertTrue(any("no registry entry" in m for m in self.fails()))

    def test_sender_off_path_or_not_member(self):
        self.put(message(sender="down:home"))
        self.assertTrue(any("not its own system's path" in m for m in self.fails()))
        shutil.rmtree(self.base / "channels")
        self.put(message(sender="stranger:home"), system="stranger")
        self.assertTrue(any("no member entry" in m for m in self.fails()))

    def test_sender_not_system_and_unit(self):
        self.put(message(sender="home"))
        self.assertTrue(any("is not `<system>:<unit>`" in m for m in self.fails()))

    def test_unresolved_reply(self):
        self.put(message(kind="reply", **{"in-reply-to": "nowhere"}))
        self.assertTrue(any("names no message" in m for m in self.fails()))

    def test_size_limit(self):
        self.put(message(body="x" * 5000))
        self.assertTrue(any("over its channel's limit of 4096" in m for m in self.fails()))

    def test_policy_slot_value(self):
        (self.base / "registry" / "channels" / "release.md").write_text(CHANNEL.replace("session-start", "hourly"))
        self.assertTrue(any("monitor 'hourly' is no allowed value" in m for m in self.fails()))
        (self.base / "registry" / "channels" / "release.md").write_text(CHANNEL.replace("session-start", "interval 64-2"))
        self.assertTrue(any("floor 64 is above its ceiling 2" in m for m in self.fails()))

    def test_member_names_another_system(self):
        (self.base / "registry" / "members" / "down.md").write_text(MEMBER.format(s="up"))
        self.assertTrue(any("is not the file's name" in m for m in self.fails()))

class ContentRules(Store):
    def chan(self, slot):
        text = CHANNEL.replace("content-rules: CONTENT-RULES.md#post-content #release-post, channels 0.1.0\n", slot)
        (self.base / "registry" / "channels" / "release.md").write_text(text)

    def test_slot_passes_with_its_headings(self):
        self.assertEqual(self.fails(), [])
        self.assertTrue({"post-content", "release-post"} <= posts.anchors(self.base))

    def test_missing_slot(self):
        self.chan("")
        self.assertTrue(any("lacks `content-rules:`" in m for m in self.fails()))

    def test_malformed_slot(self):
        self.chan("content-rules: see the rules\n")
        self.assertTrue(any("is not `CONTENT-RULES.md#post-content" in m for m in self.fails()))

    def test_slot_without_layer_one(self):
        self.chan("content-rules: CONTENT-RULES.md#release-post, channels 0.1.0\n")
        self.assertTrue(any("names no #post-content" in m for m in self.fails()))

    def test_slot_naming_an_absent_heading(self):
        self.chan("content-rules: CONTENT-RULES.md#post-content #issue-post, channels 0.1.0\n")
        self.assertTrue(any("#issue-post is no heading" in m for m in self.fails()))

    def test_no_rules_file(self):
        (self.base / posts.RULES).unlink()
        self.assertTrue(any("does not hold" in m for m in self.fails()))

    def test_member_version(self):
        (self.base / "registry" / "members" / "down.md").write_text(MEMBER.format(s="down").replace("channels 0.1.0", "latest"))
        self.assertTrue(any("is not `channels <version>`" in m for m in self.fails()))

class Fence(Store):
    def test_credential_refused(self):
        self.put(message(body="token ghp_" + "a" * 36))
        self.assertTrue(any("GitHub token shape" in m for m in self.fails()))

    def test_private_name_refused_by_hash(self):
        (self.root / "agent-corpus" / pc.PRIVATE).write_text(pc.repo_hash("someone/hidden-repo") + "\n")
        self.put(message(body="see someone/hidden-repo for the fix"))
        f = self.fails()
        self.assertTrue(any("lists as private" in m for m in f))
        self.assertFalse(any("hidden-repo" in m for m in f))           # the name itself is never printed

    def test_public_name_passes(self):
        (self.root / "agent-corpus" / pc.PRIVATE).write_text(pc.repo_hash("someone/hidden-repo") + "\n")
        self.put(message(body="see someone/open-repo"))
        self.assertEqual(self.fails(), [])

    def test_disposition_shape_refused(self):
        self.put(message(body="Y/N: merge it?"))
        self.assertTrue(any("disposition-shaped" in m for m in self.fails()))

    def test_check_text_is_the_draft_check(self):
        self.assertEqual(posts.check_text(message(), self.root), [])
        self.assertTrue(posts.check_text(message(body="Y/N: go?"), self.root))

class AppendOnly(Store):
    def git(self, *a, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.base), *a], capture_output=True, text=True, check=True)

    def test_edit_after_landing_fails(self):
        self.put(message())
        g = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        with mock.patch.dict(os.environ, g):
            self.git("init", "-q", "-b", "main"); self.git("add", "."); self.git("commit", "-q", "-m", "seed")
            self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.assertEqual(posts.append_only(self.base), [])
        self.put(message(body="changed"))
        self.assertTrue(any("edited after it landed" in m for m in posts.append_only(self.base)))
        (self.base / "channels" / "release" / "up" / "m1.md").unlink()
        self.assertTrue(any("deleted after it landed" in m for m in posts.append_only(self.base)))

def line(name, data):
    return f"{name} {hashlib.sha256(data).hexdigest()} {len(data)}"

class Attachments(Store):
    def post(self, files, channel_extra="", field=None):
        if channel_extra:
            (self.base / "registry" / "channels" / "release.md").write_text(CHANNEL.replace("\n\nReleases.", channel_extra + "\n\nReleases."))
        lines = [line(n, d) for n, d in files.items()] if field is None else field
        extra = {"attachments": "\n  ".join(lines)} if lines else {}
        self.put(message(**extra))
        d = self.base / "channels" / "release" / "up" / "m1"
        for n, data in files.items():
            d.mkdir(exist_ok=True); (d / n).write_bytes(data)
        return d

    def test_listed_text_passes_and_field_reads_back(self):
        self.post({"notes.txt": b"A tag was cut.\n", "b.md": b"more\n"})
        self.assertEqual(self.fails(), [])
        text = (self.base / "channels" / "release" / "up" / "m1.md").read_text()
        self.assertEqual([l.split()[0] for l in posts.attachment_lines(text)], ["notes.txt", "b.md"])
        self.assertIsNone(posts.attachment_lines(message()))

    def test_absent_changed_unlisted_and_unfielded(self):
        d = self.post({"a.txt": b"one\n"})
        (d / "a.txt").write_bytes(b"two\n")
        (d / "extra.txt").write_bytes(b"x\n")
        f = self.fails()
        self.assertTrue(any("not the listed" in m for m in f)); self.assertTrue(any("extra.txt is in its attachments" in m for m in f))
        (d / "a.txt").unlink()
        self.assertTrue(any("listed but absent" in m for m in self.fails()))
        shutil.rmtree(self.base / "channels"); self.put(message())
        (self.base / "channels" / "release" / "up" / "m1").mkdir(); (self.base / "channels" / "release" / "up" / "m1" / "x").write_text("x")
        self.assertTrue(any("lists no `attachments:`" in m for m in self.fails()))

    def test_malformed_line(self):
        self.post({}, field=["../a.txt 00 3"])
        self.assertTrue(any("is not `<name> <sha256> <bytes>`" in m for m in self.fails()))

    def test_limit(self):
        self.post({"big.txt": b"x" * 70000})
        self.assertTrue(any("over its channel's attachment-limit of 65536" in m for m in self.fails()))
        shutil.rmtree(self.base / "channels")
        self.post({"big.txt": b"x" * 70000}, channel_extra="\nattachment-limit: 100000")
        self.assertEqual(self.fails(), [])

    def test_fence_on_text_attachment(self):
        self.post({"t.txt": b"Y/N: merge it?\n"})
        self.assertTrue(any("attachment t.txt: holds a disposition-shaped line" in m for m in self.fails()))

    def test_binary_and_personal_only_on_private(self):
        self.post({"img.bin": b"\x00\x01\x02", "tr.txt": b"call +1 555 123 4567 or mail someone@example.org\n"})
        f = self.fails()
        self.assertTrue(any("is binary" in m for m in f))
        self.assertTrue(any("email address shape" in m for m in f)); self.assertTrue(any("phone number shape" in m for m in f))
        with mock.patch.object(posts, "hosting_visibility", return_value=("private", "the hosting's flag")):
            (self.base / "registry" / "channels" / "release.md").write_text(CHANNEL.replace("\n\nReleases.", "\nvisibility: private\n\nReleases."))
            self.assertEqual(self.fails(), [])

    def test_hosting_overrules_a_private_entry(self):
        self.post({"img.bin": b"\x00"}, channel_extra="\nvisibility: private")
        with mock.patch.object(posts, "hosting_visibility", return_value=("public", "the hosting's flag")):
            f = self.fails()
        self.assertTrue(any("hosting says the repository is public (J1)" in m for m in f)); self.assertTrue(any("is binary" in m for m in f))
        with mock.patch.object(posts, "hosting_visibility", return_value=(None, "the hosting answered 404")):
            msgs = posts.check_package(self.root)
        self.assertTrue(any(m.startswith("warning:") and "trusted (J1)" in m for m in msgs))
        self.assertEqual([m for m in msgs if not m.startswith("warning:")], [])

    def test_hosting_slug_and_unread_hosting(self):
        self.assertIsNone(posts.hosting_slug(self.base))
        self.assertEqual(posts.hosting_visibility(self.base)[0], None)
        subprocess.run(["git", "-C", str(self.base), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.base), "remote", "add", "origin", "https://github.com/someone/chan.git"], check=True)
        self.assertEqual(posts.hosting_slug(self.base), "someone/chan")

    def test_file_added_after_landing(self):
        self.post({"a.txt": b"one\n"})
        g = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        with mock.patch.dict(os.environ, g):
            for a in (("init", "-q", "-b", "main"), ("add", "."), ("commit", "-q", "-m", "seed"),
                      ("update-ref", "refs/remotes/origin/main", "HEAD")):
                subprocess.run(["git", "-C", str(self.base), *a], check=True, capture_output=True)
        self.assertEqual(posts.append_only(self.base), [])
        (self.base / "channels" / "release" / "up" / "m1" / "late.txt").write_text("late\n")
        self.assertTrue(any("late.txt: added to the attachments of" in m for m in posts.append_only(self.base)))

class Invariants(unittest.TestCase):
    def test_invariants_hold(self):
        self.assertEqual([n for n, f in posts.INVARIANTS if not f()], [])

if __name__ == "__main__":
    unittest.main()

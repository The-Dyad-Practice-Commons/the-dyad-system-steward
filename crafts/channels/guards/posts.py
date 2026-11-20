#!/usr/bin/env python3
"""Post guard (entity `post`, corpus `craft`; the channels craft's guard — its rules `crafts/channels/rules/`; placed
per `crafts/sysarch/rules/guards.md` under `crafts/channels/guards/`; d-work #682). Kernel: Python 3.12+.
Reads a checkout of a channels repository named by the instance file `<instance>/channels.local.txt` (`clone: <path>`,
relative to the repo root or absolute, and `system: <name>`; absent: one `warning: skip` line) and fails what
the protocol's records cannot hold (the canonical message format `dyad-channels/1`, `../templates/message.md`):
- a channel record (`registry/channels/<channel>.md`) lacking a required slot, or a policy slot of no allowed value;
- a channel's `content-rules` slot not naming `CONTENT-RULES.md#post-content` and its own rule, or naming a heading
  the root `CONTENT-RULES.md` lacks (the self-imposed content rules travel with the channels, plan #682 revision 5);
- a member record (`registry/members/<system>.md`) lacking a required slot, naming another system than its file, or
  a `content-rules` slot that is not `channels <version>`;
- a message (`channels/<channel>/<system>/<id>.md`) lacking a required field, of a `kind` the format does not list,
  whose `id`, `channel` or `from` system disagrees with its path, whose sender is no member, whose `in-reply-to`
  names no message, or that is larger than its channel's limit;
- a message's attachments (`attachments:`, one `<name> <sha256> <bytes>` per line, the files in
  `channels/<channel>/<system>/<id>/`, d-work #752): a listed file absent or of another sha256 or size, a file in the
  directory the field does not list, a directory with no field, a total over the channel's `attachment-limit`, a text
  attachment the fence refuses, and a binary or a personal-data shape (`PERSONAL_SHAPES`) on a channel that is not
  `private`;
- a channel entry calling itself `private` while the hosting says its repository is public (J1); where the hosting
  cannot be read the entry is trusted and one `warning:` line says so;
- a message the clone's `origin` main line holds, edited or deleted in the checkout, or a file added to its
  attachments' directory after it landed (append-only);
- the world-facing fence on every record (`check_text`): a credential shape (the core provenance guard's
  `FAIL_SHAPES`), an `owner/repo` whose sha256 the instance lists as private (`<instance>/private_repos.local.txt`,
  read by `dyad/scripts/privatecite.py`, #518), and a disposition-shaped line (the core inbox's `DISPOSITION`).
An unknown field is kept and never refused (the format's generality, plan #682 revision 3). `check_text` is the
function the `post` step calls before it writes a draft into the clone, so the fence holds before any push.
Left to inference, stated: whether a post's claims are its sender's own, and whether a proposal is one (M4, M7).
  posts.py [repo-root]
"""
import sys
if sys.version_info < (3, 12):
    sys.exit("posts.py: Python 3.12+ required")
import hashlib, json, os, re, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "dyad" / "scripts"))   # crafts/channels/guards/ -> dyad/scripts
import dyadlib

ENTITY, CORPUS, TRANSACTION = "post", "craft", False
# Bundled with the core (Rule-11 property 2, criterion (a), d-work #747): core Rule-3 (Incidents) cites
# `crafts/channels/playbooks/channel-post.md` by path, so every install can report an upstream incident as an `issue`
# post, and a core-only install must carry this craft or ship a Rule that cites a tree it lacks. One declaration per
# craft; the core keeps no list (`package.bundled_crafts`). The `PURPOSE` line is ground (b), so this declaration passes
# before Rule-3's citation lands, and it stays beside ground (a) afterwards (plan #747 revision 2).
BUNDLED_WITH_CORE = True
PURPOSE = "every installing operator reports upstream incidents and receives releases over the channels repository"
NAME, OWNER = "post (a channels message or registry record)", "crafts/channels/rules/channels.md"
FORMAT = "dyad-channels/1"                                                 # the canonical message format's version
FIELDS = ("format", "id", "channel", "kind", "from", "sent")               # a message's required fields
OPTIONAL = ("holder", "in-reply-to", "refs", "attachments")                # named optional fields; any other is kept
KINDS = ("fact", "proposal", "reported-disposition", "question", "reply")  # every class of the member play-book's S1
CHANNEL_FIELDS = ("id", "creator", "owner", "sources", "admission", "posting", "monitor", "limits", "decision-rights",
                  "content-rules")
CHANNEL_OPTIONAL = ("visibility", "attachment-limit")                   # absent: `public`, DEFAULT_LIMIT (#752)
VISIBILITY = ("public", "private")
DEFAULT_LIMIT = {"public": 64 * 1024, "private": 1024 * 1024}              # bytes of attachments per message (J3)
PERSONAL_SHAPES = (                                                       # personal data a public channel refuses (#752)
    ("email address", re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")),
    ("phone number", re.compile(r"(?<![\w+])\+?\d{1,3}[ .-]?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\w)")),
)
HOSTING_TIMEOUT_S = 5
MEMBER_FIELDS = ("system", "units", "bound-repository", "play-book", "content-rules")
RULES = "CONTENT-RULES.md"                                                  # the content rules rendered at the root (plan #682 rev 5)
LAYER1 = "post-content"                                                    # every channel's rules name layer 1
POLICY = {"admission": re.compile(r"open"), "posting": re.compile(r"members|named( [\w.-]+:[\w.-]+)+"),
          "monitor": re.compile(r"session-start|interval \d+-\d+"), "limits": re.compile(r"\d+ KiB, \d+ per hour"),
          "decision-rights": re.compile(r"none"),
          "visibility": re.compile("|".join(VISIBILITY)), "attachment-limit": re.compile(r"\d+")}
LOCAL, REGISTRY, STORE = "channels.local.txt", "registry", "channels"   # the instance file (Rule-11 p1: instance data)
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_SENDER = re.compile(r"([A-Za-z0-9][\w.-]*):([A-Za-z0-9][\w.-]*)")      # `<system>:<unit>`, never a session
_REPO = re.compile(r"(?<![\w.-])([A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*)(?![\w/-])")
_INTERVAL = re.compile(r"interval (\d+)-(\d+)")
_CHANNEL_RULES = re.compile(rf"{re.escape(RULES)}((?: ?#[a-z0-9-]+)+), channels (\d+\.\d+\.\d+)")
_MEMBER_RULES = re.compile(r"channels (\d+\.\d+\.\d+)")
_HEADING = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*$")
_ATTACHMENT = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]{0,79}) ([0-9a-f]{64}) (\d+)")
_GITHUB = re.compile(r"(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?/?$")
INVARIANTS = [   # crafts/syseng/rules/invariants.md
    ("fields-open-with-format", lambda: FIELDS[0] == "format" and len(set(FIELDS + OPTIONAL)) == len(FIELDS + OPTIONAL)),
    ("kinds-are-five", lambda: len(set(KINDS)) == 5 and "reported-disposition" in KINDS),
    ("policy-slots-are-channel-fields", lambda: set(POLICY) <= set(CHANNEL_FIELDS + CHANNEL_OPTIONAL)),
    ("every-visibility-has-a-limit", lambda: set(DEFAULT_LIMIT) == set(VISIBILITY)
     and DEFAULT_LIMIT["public"] < DEFAULT_LIMIT["private"]),
    ("attachment-line-is-name-sha-bytes", lambda: bool(_ATTACHMENT.fullmatch("t.txt " + "0" * 64 + " 12"))
     and not _ATTACHMENT.fullmatch("../t.txt " + "0" * 64 + " 12")),
    ("content-rules-in-both-registries", lambda: "content-rules" in CHANNEL_FIELDS and "content-rules" in MEMBER_FIELDS),
    ("session-start-is-a-monitor-value", lambda: bool(POLICY["monitor"].fullmatch("session-start"))
     and bool(POLICY["monitor"].fullmatch("interval 2-64"))),
    ("sender-is-system-and-unit", lambda: bool(_SENDER.fullmatch("dyad-system:engineer")) and not _SENDER.fullmatch("engineer")),
]
dyadlib.enforce(INVARIANTS, __name__)

def local(root: Path | None = None) -> dict[str, str]:
    """The instance file's `key: value` lines (`clone`, `system`), or {} when it is absent."""
    p = dyadlib.instance(root or dyadlib.repo_root()) / LOCAL
    return parse(p.read_text(errors="replace") + "\n\n")[0] if p.is_file() else {}

def store(root: Path | None = None) -> Path | None:
    """The channels checkout the instance file's `clone:` names, or None; a relative path reads from `root`."""
    v = local(root).get("clone")
    if not v:
        return None
    p = Path(v)
    return p if p.is_absolute() else (root or dyadlib.repo_root()) / p

def parse(text: str) -> tuple[dict[str, str], str]:
    """(header, body): the leading `key: value` lines up to the first blank line, then everything after it."""
    head, _, body = text.partition("\n\n")
    out = {}
    for line in head.splitlines():
        k, sep, v = line.partition(":")
        if sep and k.strip() and not k.startswith(" "):
            out[k.strip()] = v.strip()
    return out, body

def private_hashes(root: Path) -> set[str]:
    pc = dyadlib.load_module(dyadlib.PKG / "scripts" / "privatecite.py", "privatecite")
    return pc.read_lists(root)[1] or set()

def check_text(text: str, root: Path, where: str = "draft", private: set[str] | None = None) -> list[str]:
    """The world-facing fence on one record's whole text (plan #682, rules/fence.md): credentials, private names by
    hash, and disposition-shaped lines. [] when it may be shown to every member."""
    prov = dyadlib.load_guard("agent", "provenance")
    pc = dyadlib.load_module(dyadlib.PKG / "scripts" / "privatecite.py", "privatecite")
    private = private_hashes(root) if private is None else private
    msgs = [f"{where}: holds a {name} shape; a channel is public (fence)" for name, pat in prov.FAIL_SHAPES if pat.search(text)]
    msgs += [f"{where}: names a repository the instance lists as private (sha256 {pc.repo_hash(r)[:12]}…); a channel is public (fence)"
             for r in sorted({m[1].removesuffix(".git") for m in _REPO.finditer(text)}) if pc.repo_hash(r) in private]
    if dyadlib.load_guard("agent", "inbox").DISPOSITION.search(text):
        msgs.append(f"{where}: holds a disposition-shaped line; a message reports a disposition as a fact and never asks or gives one (M1, M8)")
    return msgs

def channels(base: Path) -> dict[str, dict[str, str]]:
    d = base / REGISTRY / "channels"
    return {p.stem: parse(p.read_text(errors="replace"))[0] for p in sorted(d.glob("*.md"))} if d.is_dir() else {}

def members(base: Path) -> dict[str, dict[str, str]]:
    d = base / REGISTRY / "members"
    return {p.stem: parse(p.read_text(errors="replace"))[0] for p in sorted(d.glob("*.md"))} if d.is_dir() else {}

def messages(base: Path) -> list[Path]:
    d = base / STORE
    return sorted(d.glob("*/*/*.md")) if d.is_dir() else []

def limit_bytes(ch: dict[str, str]) -> int | None:
    m = re.match(r"(\d+) KiB", ch.get("limits", ""))
    return int(m[1]) * 1024 if m else None

def anchors(base: Path) -> set[str] | None:
    """The heading anchors of the root CONTENT-RULES.md (each heading lowercased, spaces as `-`), or None if absent."""
    p = base / RULES
    if not p.is_file():
        return None
    return {re.sub(r"[^a-z0-9-]", "", h.strip().lower().replace(" ", "-")) for h in _HEADING.findall(p.read_text(errors="replace"))}

def check_rules_slot(where: str, ch: dict[str, str], heads: set[str] | None) -> list[str]:
    """A channel's `content-rules` slot: `CONTENT-RULES.md#post-content #<channel>-post, channels <version>`, every
    anchor a heading of the root CONTENT-RULES.md (the self-imposed rules a subscriber reads before posting, L7)."""
    v = ch.get("content-rules")
    if not v:
        return []
    m = _CHANNEL_RULES.fullmatch(v)
    if not m:
        return [f"{where}: content-rules {v!r} is not `{RULES}#{LAYER1} #<rule>, channels <version>` (templates/channel.md)"]
    names = m[1].replace("#", " ").split()
    msgs = [] if LAYER1 in names else [f"{where}: content-rules names no #{LAYER1}; every channel's rules start with layer 1"]
    if heads is None:
        return msgs + [f"{where}: content-rules names {RULES}, which the channels repository's root does not hold"]
    return msgs + [f"{where}: content-rules #{n} is no heading of {RULES}" for n in names if n not in heads]

def check_message(base: Path, path: Path, text: str, chans: dict, mems: dict, ids: set[str]) -> list[str]:
    where = path.relative_to(base).as_posix()
    head, _ = parse(text)
    msgs = [f"{where}: lacks `{k}:` (templates/message.md)" for k in FIELDS if not head.get(k)]
    if head.get("format") and head["format"] != FORMAT:
        msgs.append(f"{where}: format {head['format']!r} is not {FORMAT}")
    if head.get("kind") and head["kind"] not in KINDS:
        msgs.append(f"{where}: kind {head['kind']!r} is none of {', '.join(KINDS)}")
    channel, system = path.parts[-3], path.parts[-2]
    if head.get("id") and (head["id"] != path.stem or not _ID.fullmatch(head["id"])):
        msgs.append(f"{where}: id {head['id']!r} is not the file's name, or not 1–80 of [A-Za-z0-9._-]")
    if head.get("channel") and head["channel"] != channel:
        msgs.append(f"{where}: channel {head['channel']!r} is not the directory {channel!r}")
    if channel not in chans:
        msgs.append(f"{where}: channel {channel!r} has no registry entry (G1)")
    sender = _SENDER.fullmatch(head.get("from", ""))
    if head.get("from") and not sender:
        msgs.append(f"{where}: from {head['from']!r} is not `<system>:<unit>` (G5)")
    elif sender and sender[1] != system:
        msgs.append(f"{where}: from {head['from']!r} writes under {system}/, not its own system's path (G8)")
    elif sender and sender[1] not in mems:
        msgs.append(f"{where}: sender system {sender[1]!r} has no member entry (G2)")
    if head.get("in-reply-to") and head["in-reply-to"] not in ids:
        msgs.append(f"{where}: in-reply-to {head['in-reply-to']!r} names no message (M6)")
    if (cap := limit_bytes(chans.get(channel, {}))) and len(text.encode()) > cap:
        msgs.append(f"{where}: {len(text.encode())} bytes, over its channel's limit of {cap} (L5)")
    return msgs

def attachment_lines(text: str) -> list[str] | None:
    """The `attachments:` field's entries: the value on its own line and each indented line after it, or None when the
    header has no such field (`parse` keeps only the first line, so the field is read here)."""
    head = text.partition("\n\n")[0].splitlines()
    for i, line in enumerate(head):
        if line.startswith("attachments:"):
            j = i + 1
            out = [line.partition(":")[2].strip()]
            while j < len(head) and head[j][:1] in (" ", "\t"):
                out.append(head[j].strip()); j += 1
            return [l for l in out if l]
    return None

def attachment_dir(path: Path) -> Path:
    """Where a message's attachments sit: `channels/<channel>/<system>/<id>/`, beside `<id>.md`."""
    return path.parent / path.stem

def is_text(data: bytes) -> bool:
    if b"\0" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True

def personal(text: str) -> list[str]:
    return [name for name, pat in PERSONAL_SHAPES if pat.search(text)]

def visibility(ch: dict[str, str], hosting: str | None = None) -> str:
    """A channel's effective visibility: its entry's `visibility` (absent, `public`), and `public` whenever the hosting
    says the repository is public, whatever the entry says (J1)."""
    v = ch.get("visibility") or "public"
    return "public" if hosting == "public" or v not in VISIBILITY else v

def attachment_limit(ch: dict[str, str], hosting: str | None = None) -> int:
    v = ch.get("attachment-limit", "")
    return int(v) if v.isdigit() else DEFAULT_LIMIT[visibility(ch, hosting)]

def check_attachments(base: Path, path: Path, text: str, ch: dict[str, str], root: Path,
                      private: set[str] | None = None, hosting: str | None = None) -> list[str]:
    """A message's attachments against its `attachments:` field (d-work #752): each listed file present with its
    sha256 and size, nothing unlisted, the channel's limit, the fence on text, and binaries and personal data only on
    a `private` channel. `path` is the message's place in the clone; the directory is read beside it."""
    where, d = path.relative_to(base).as_posix(), attachment_dir(path)
    lines, msgs = attachment_lines(text), []
    on_disk = sorted(p for p in d.rglob("*")) if d.is_dir() else []
    if lines is None:
        return [f"{where}: {d.relative_to(base).as_posix()}/ holds files but the message lists no `attachments:`"] if on_disk else []
    vis, listed, total = visibility(ch, hosting), set(), 0
    for line in lines:
        m = _ATTACHMENT.fullmatch(line)
        if not m:
            msgs.append(f"{where}: attachment {line!r} is not `<name> <sha256> <bytes>` (templates/message.md)"); continue
        name, sha, size = m[1], m[2], int(m[3])
        listed.add(name); total += size
        f = d / name
        aw = f"{where} attachment {name}"
        if not f.is_file():
            msgs.append(f"{aw}: listed but absent from {d.relative_to(base).as_posix()}/"); continue
        data = f.read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
            msgs.append(f"{aw}: is {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()[:12]}…, not the listed {size}, {sha[:12]}…")
        if is_text(data):
            body = data.decode("utf-8")
            msgs += check_text(body, root, aw, private)
            if vis != "private":
                msgs += [f"{aw}: holds a {n} shape; personal data goes only on a private channel (fence §4)" for n in personal(body)]
        elif vis != "private":
            msgs.append(f"{aw}: is binary; a {vis} channel takes text alone, which the fence can read (J2)")
    msgs += [f"{where}: {p.relative_to(base).as_posix()} is in its attachments' directory but not listed"
             for p in on_disk if p.relative_to(d).as_posix() not in listed]
    if total > (cap := attachment_limit(ch, hosting)):
        msgs.append(f"{where}: attachments total {total} bytes, over its channel's attachment-limit of {cap} (J3)")
    return msgs

def hosting_slug(base: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(base), "remote", "get-url", "origin"], capture_output=True, text=True)
    m = _GITHUB.match(r.stdout.strip()) if r.returncode == 0 else None
    return m[1] if m else None

def hosting_visibility(base: Path) -> tuple[str | None, str]:
    """The hosting's own flag for the clone's `origin` (J1): ("public" | "private", how it was read), or (None, why it
    could not be). Only GitHub is read, with `GITHUB_TOKEN` when set; an unauthenticated 404 is unknown, since a
    private repository and a missing one answer alike."""
    import urllib.error, urllib.request
    if (slug := hosting_slug(base)) is None:
        return None, "the clone's origin is no GitHub repository"
    token = os.environ.get("GITHUB_TOKEN")
    req = urllib.request.Request(f"https://api.github.com/repos/{slug}",
                                 headers={"Accept": "application/vnd.github+json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=HOSTING_TIMEOUT_S) as resp:
            return ("private" if json.load(resp).get("private") else "public"), "the hosting's flag"
    except urllib.error.HTTPError as e:
        return None, f"the hosting answered {e.code}"
    except Exception as e:                                       # The World: unreadable is a warning, never a crash
        return None, f"the hosting could not be read ({type(e).__name__})"

def landed_ref(base: Path) -> str | None:
    """The clone's view of the shared repository's main line (`origin/HEAD`, else `origin/main`), or None."""
    for ref in ("origin/HEAD", "origin/main"):
        r = subprocess.run(["git", "-C", str(base), "rev-parse", "--verify", "--quiet", ref], capture_output=True, text=True)
        if r.returncode == 0:
            return ref
    return None

def append_only(base: Path) -> list[str]:
    """A message the shared repository already holds is never edited or deleted (G8, the store's append-only rule)."""
    if not (base / ".git").exists() or (ref := landed_ref(base)) is None:
        return []
    r = subprocess.run(["git", "-C", str(base), "diff", "--name-status", "--no-renames", ref, "--", STORE],
                       capture_output=True, text=True)
    msgs = [f"{line.split(chr(9))[-1]}: {'edited' if line[0] == 'M' else 'deleted'} after it landed on {ref}; a message is append-only"
            for line in r.stdout.splitlines() if line[:1] in ("M", "D")]
    landed = set(subprocess.run(["git", "-C", str(base), "ls-tree", "-r", "--name-only", ref, "--", STORE],
                                capture_output=True, text=True).stdout.splitlines())
    added = subprocess.run(["git", "-C", str(base), "ls-files", "--others", "--exclude-standard", "--", STORE],
                           capture_output=True, text=True).stdout.splitlines()
    added += [l.split(chr(9))[-1] for l in r.stdout.splitlines() if l[:1] == "A"]
    for a in sorted(set(added)):
        parts = a.split("/")
        if len(parts) >= 5 and "/".join(parts[:4]) + ".md" in landed:
            msgs.append(f"{a}: added to the attachments of {'/'.join(parts[:4])}.md after it landed on {ref}; a message is append-only")
    return msgs

def check_package(root: Path | None = None, pkg: Path = dyadlib.PKG) -> list[str]:
    root = root or dyadlib.repo_root()
    base = store(root)
    if base is None or not base.is_dir():
        return [f"warning: skip posts: no channels checkout (name one as `clone:` in <instance>/{LOCAL})"]
    private, msgs = private_hashes(root), []
    chans, mems, heads = channels(base), members(base), anchors(base)
    hosting = None
    if any(ch.get("visibility") == "private" for ch in chans.values()):
        hosting, how = hosting_visibility(base)
        if hosting is None:
            msgs.append(f"warning: channels/posts: the repository's visibility is unread ({how}); each `private` entry is trusted (J1)")
    for name, ch in chans.items():
        where = f"{REGISTRY}/channels/{name}.md"
        if ch.get("visibility") == "private" and hosting == "public":
            msgs.append(f"{where}: visibility private, but the hosting says the repository is public (J1)")
        msgs += [f"{where}: lacks `{k}:` (templates/channel.md)" for k in CHANNEL_FIELDS if not ch.get(k)]
        msgs += [f"{where}: {k} {ch[k]!r} is no allowed value (templates/channel.md)" for k, pat in POLICY.items()
                 if ch.get(k) and not pat.fullmatch(ch[k])]
        if (m := _INTERVAL.fullmatch(ch.get("monitor", ""))) and int(m[1]) > int(m[2]):
            msgs.append(f"{where}: monitor floor {m[1]} is above its ceiling {m[2]} (W1)")
        msgs += check_rules_slot(where, ch, heads)
    for name, mem in mems.items():
        where = f"{REGISTRY}/members/{name}.md"
        msgs += [f"{where}: lacks `{k}:` (templates/member.md)" for k in MEMBER_FIELDS if not mem.get(k)]
        if mem.get("system") and mem["system"] != name:
            msgs.append(f"{where}: system {mem['system']!r} is not the file's name; each system writes only its own entry (G2)")
        if mem.get("content-rules") and not _MEMBER_RULES.fullmatch(mem["content-rules"]):
            msgs.append(f"{where}: content-rules {mem['content-rules']!r} is not `channels <version>`, the rules' version adopted (templates/member.md)")
    paths = messages(base)
    ids = {p.stem for p in paths}
    for p in paths:
        text = p.read_text(errors="replace")
        msgs += check_message(base, p, text, chans, mems, ids)
        msgs += check_attachments(base, p, text, chans.get(p.parts[-3], {}), root, private, hosting)
    msgs += append_only(base)
    for p in sorted(base.glob(f"{REGISTRY}/*/*.md")) + paths:
        msgs += check_text(p.read_text(errors="replace"), root, p.relative_to(base).as_posix(), private)
    return msgs

def summary(root: Path | None = None, pkg: Path = dyadlib.PKG) -> str:
    base = store(root or dyadlib.repo_root())
    if base is None or not base.is_dir():
        return "no channels checkout"
    return f"{len(channels(base))} channel(s), {len(members(base))} member(s), {len(messages(base))} message(s)"

def describe(root: Path, pkg: Path = dyadlib.PKG) -> dict:
    allowed = {"format": FORMAT, "id": "1-80 of [A-Za-z0-9._-], the file's name", "channel": "its directory",
               "kind": " | ".join(KINDS), "from": "<system>:<unit>", "sent": "an ISO-8601 UTC time"}
    return {"store": f"<clone: of <instance>/{LOCAL}>/channels/<channel>/<system>/<id>.md", "parser": "`posts.parse`",
            "observed": len(messages(store(root))) if store(root) and store(root).is_dir() else 0,
            "note": "unknown fields are kept and never refused; optional: " + ", ".join(OPTIONAL),
            "fields": [(f, "text", allowed[f], True, "", "posts.FIELDS") for f in FIELDS]}

def main(a: list[str]) -> int:
    root = Path(a[0]).resolve() if a else dyadlib.repo_root()
    msgs = check_package(root)
    for m in msgs:
        print(m)
    bad = [m for m in msgs if not m.startswith("warning:")]
    print(f"{'FAIL' if bad else 'ok  '} [channels/posts] {summary(root)}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

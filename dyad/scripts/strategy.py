#!/usr/bin/env python3
"""The operator's attention strategy (core craft; d-work #705; `dyad/dmc/attention-strategy.jsonld`, play-book
`dyad/playbooks/attention.md`). Kernel: Python 3.12+, git.

Where a candidate the home shows or proposes sits in the operator's attention order: what is owed (promotion's P1, P2)
first, then the operator's goals by horizon, then today's focus as a fading weight, then the urgency the existing
criteria already rank. The mechanism is one for every operator; the goals, the focus and the settings are each
operator's own, in the operator's store:

- **central**: `operator/` in the central repository this checkout names (`git config dyad.attention.clone`, #700):
  `goals.md`, `focus.md` (append-only), `settings.md`, and `dmc/` (the operator's overlay records);
- **fallback**, when no central repository is named: the goals and settings in `preferences-corpus/ATTENTION.md`
  (operator-owned, changed only by a preferences-zone PR, so a goal write prints that PR's text and writes nothing),
  and the focus as the `focus` key of the home's cross-row board entry (ledger-only).

A goal's words live only in that store and in the chat; every public record names a goal by `G<n>` alone. The order
authorizes nothing (`dmc:preference-kind`: a form): an item still becomes work only by its own question or a prompt.

Verbs (`dyad attention …`): `goals` (read-only), `goal add --horizon <h> --review <date> --said-file <f>`,
`goal retire G<n>`, `focus --said-file <f>` | `focus --inferred "<line>"`, and `order [--full]` (read-only).
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyadlib  # noqa: E402

RECORD = "attention-strategy"
CONFLICTS = ("goals-first", "blend")       # attention-conflict's values; the first is the default (the record's)
HORIZONS = ("long-term", "intermediate")   # a goal's horizon, highest tier first
TIER = {"long-term": 2, "intermediate": 1}  # the blend's tier weights; serves none is 0
OWED = ("P1", "P2")                         # promotion's owed classes: before any goal, moved by no setting
SOURCES = ("stated", "inferred")            # a focus's source; a stated one weighs 1
FLOOR = 0.05                                # a focus weight below this counts as none
NBD_WEIGHTS = ("nbd-criticality-weight", "nbd-age-weight")   # #709: the next-best order's weights, per operator
SETTINGS = ("attention-conflict", "focus-half-life-days", "inferred-focus-weight", *NBD_WEIGHTS)
FALLBACK_REL = "preferences-corpus/ATTENTION.md"
CENTRAL_DIR = "operator"
FOCUS_KEEP = 7                              # fallback focus lines kept on the cross-row entry, newest last
GOAL_ID = re.compile(r"G(\d+)")
GOAL_HEAD = re.compile(r"^## G(?P<n>\d+) (?P<horizon>long-term|intermediate) review (?P<review>\d{4}-\d{2}-\d{2})\s*$")
FOCUS_HEAD = re.compile(r"^## (?P<at>\d{4}-\d{2}-\d{2}T\S+) (?P<source>stated|inferred)\s*$")
FOCUS_LINE = re.compile(r"^(?P<at>\d{4}-\d{2}-\d{2}T\S+) (?P<source>stated|inferred): (?P<text>.+)$")
SERVES_LINE = re.compile(r"^#(?P<id>\d+) (?P<goal>G\d+|none) \((?P<reason>[^)]*)\) @(?P<at>\S+)$")
SETTING_LINE = re.compile(r"^(?P<key>[a-z-]+):\s*(?P<value>\S.*?)\s*$")
WORD = re.compile(r"[a-z][a-z0-9]{3,}")     # a focus matches a title sharing two such words
STOP = frozenset({"with", "from", "into", "that", "this", "when", "each", "what", "they", "them", "their", "have",
                  "make", "work", "only", "more", "than", "over", "under", "about", "every", "none", "rows", "today"})
USAGE = ("usage: dyad attention goals | dyad attention goal add --horizon <long-term|intermediate> --review <date> "
         "--said-file <f> | dyad attention goal retire G<n> | dyad attention focus --said-file <f> | "
         "dyad attention focus --inferred \"<line>\" | dyad attention order [--full]")
NO_GOALS = "attention: no goals are recorded; the order is today's, moved only by focus"


@dataclass
class Goal:
    id: str
    horizon: str
    review: str
    status: str
    words: str


@dataclass
class Focus:
    at: datetime.datetime
    source: str
    text: str


@dataclass
class Store:
    kind: str                 # "central" or "fallback"
    where: Path               # the operator/ directory, or ATTENTION.md
    goals: list
    focus: list
    settings: dict
    clone: Path | None = None


# ---- parsing (pure)

def fenced_blocks(text: str, head: re.Pattern) -> list[tuple[re.Match, str, dict]]:
    """[(heading match, fenced body, the key: value lines after the fence)] for every `## …` heading `head` matches.
    The body is the operator's words, kept as data inside a fence, so a heading or a pipe in it reshapes nothing."""
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        m = head.match(lines[i])
        i += 1
        if not m:
            continue
        while i < len(lines) and not lines[i].strip():
            i += 1
        body, keys = [], {}
        if i < len(lines) and lines[i].startswith("```"):
            fence = re.match(r"`{3,}", lines[i]).group(0)
            i += 1
            while i < len(lines) and lines[i].rstrip() != fence:
                body.append(lines[i])
                i += 1
            i += 1
        while i < len(lines) and not lines[i].startswith("## "):
            k = SETTING_LINE.match(lines[i])
            if k:
                keys[k["key"]] = k["value"]
            i += 1
        out.append((m, "\n".join(body), keys))
    return out


def parse_goals(text: str) -> list[Goal]:
    return [Goal(f"G{m['n']}", m["horizon"], m["review"], keys.get("status", "active"), body)
            for m, body, keys in fenced_blocks(text or "", GOAL_HEAD)]


def parse_when(at: str) -> datetime.datetime | None:
    try:
        d = datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.UTC)


def parse_focus_file(text: str) -> list[Focus]:
    out = []
    for m, body, _ in fenced_blocks(text or "", FOCUS_HEAD):
        if (at := parse_when(m["at"])):
            out.append(Focus(at, m["source"], body))
    return out


def parse_focus_key(value: str) -> list[Focus]:
    out = []
    for line in (l.strip() for l in (value or "").splitlines()):
        m = FOCUS_LINE.match(line)
        if m and (at := parse_when(m["at"])):
            out.append(Focus(at, m["source"], m["text"]))
    return out


def parse_settings(text: str) -> dict[str, str]:
    """The setting lines outside every fence, the keys of SETTINGS only."""
    out, fenced = {}, False
    for line in (text or "").splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        m = None if fenced else SETTING_LINE.match(line.strip())
        if m and m["key"] in SETTINGS:
            out[m["key"]] = m["value"]
    return out


def render_goal(g: Goal) -> str:
    fence = "````" if "```" in g.words else "```"
    return f"## {g.id} {g.horizon} review {g.review}\n\n{fence}\n{g.words.rstrip()}\n{fence}\nstatus: {g.status}\n"


def render_focus(f: Focus) -> str:
    fence = "````" if "```" in f.text else "```"
    return f"## {iso(f.at)} {f.source}\n\n{fence}\n{f.text.rstrip()}\n{fence}\n"


def iso(d: datetime.datetime) -> str:
    return d.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%MZ")


# ---- the order (pure)

def decay(source: str, age_days: float, half_life: float, inferred_weight: float) -> float:
    """A focus's weight: its source's (stated 1, inferred `inferred-focus-weight`) halved each `half_life` days; a
    weight below FLOOR counts as none."""
    w = (1.0 if source == "stated" else inferred_weight) * 0.5 ** (max(age_days, 0.0) / half_life)
    return w if w >= FLOOR else 0.0


def words(text: str) -> set[str]:
    return {w for w in WORD.findall((text or "").lower()) if w not in STOP}


def matches(focus: Focus, rid: int, title: str, goal: str | None) -> bool:
    """A focus matches a candidate when it names the row (`#<id>`), names the goal the row serves (`G<n>`), or shares
    two words of four letters or more with the row's title (stopwords aside)."""
    t = focus.text
    if re.search(rf"#{rid}\b", t) or (goal and re.search(rf"\b{goal}\b", t)):
        return True
    return len(words(t) & words(title)) >= 2


def focus_weight(focus: list[Focus], rid: int, title: str, goal: str | None, now: datetime.datetime,
                 half_life: float, inferred_weight: float) -> float:
    """The newest focus that matches the candidate counts, decayed by its age."""
    for f in sorted(focus, key=lambda f: f.at, reverse=True):
        if matches(f, rid, title, goal):
            return decay(f.source, (now - f.at).total_seconds() / 86400, half_life, inferred_weight)
    return 0.0


def tier_of(goal: str | None, goals: dict[str, Goal]) -> int:
    g = goals.get(goal or "")
    return TIER.get(g.horizon, 0) if g and g.status == "active" else 0


def sort_key(owed: bool, tier: int, weight: float, urgency: int, conflict: str) -> tuple:
    """goals-first: lexicographic (owed, tier, focus, urgency), so focus reorders only within a tier; blend: the tier
    and the focus weight summed. Owed always first, and urgency always last."""
    if conflict == "blend":
        return (0 if owed else 1, -(tier + weight), urgency)
    return (0 if owed else 1, -tier, -weight, urgency)


def order(cands: list[dict], goals: list[Goal], serves: dict[int, str | None], focus: list[Focus],
          settings: dict, now: datetime.datetime) -> list[dict]:
    """Each candidate `{id, title, cls, urgency}` (`cls` promotion's P1–P6 or a trigger kind; `urgency` its index in
    the existing order) gains `goal`, `tier`, `focus` and `key`, and the list is returned in the strategy's order."""
    by = {g.id: g for g in goals}
    conflict, half, inf = settings["attention-conflict"], settings["focus-half-life-days"], settings["inferred-focus-weight"]
    out = []
    for c in cands:
        goal = serves.get(c["id"])
        goal = goal if goal in by and by[goal].status == "active" else None
        tier = tier_of(goal, by)
        w = focus_weight(focus, c["id"], c.get("title", ""), goal, now, half, inf)
        out.append({**c, "goal": goal, "tier": tier, "focus": w,
                    "key": sort_key(c.get("cls") in OWED, tier, w, c.get("urgency", 0), conflict)})
    return sorted(out, key=lambda c: (c["key"], c["id"]))


def departs(focus: list[Focus], ordered: list[dict], goals: list[Goal], now: datetime.datetime) -> str | None:
    """A stated focus of today that matches only candidates serving none, while goals are recorded: one line naming the
    goals it departs from, for the operator to adopt as a goal or keep for today (A5)."""
    active = [g.id for g in goals if g.status == "active"]
    stated = [f for f in focus if f.source == "stated" and (now - f.at).total_seconds() < 86400]
    if not active or not stated:
        f = None
    else:
        f = max(stated, key=lambda f: f.at)
    if f is None:
        return None
    hit = [c for c in ordered if matches(f, c["id"], c.get("title", ""), c.get("goal"))]
    if hit and all(c.get("goal") is None for c in hit):
        return (f"attention: today's focus ({iso(f.at)}) matches only rows serving no goal "
                f"({', '.join('#' + str(c['id']) for c in hit)}); it departs from {', '.join(active)} — adopt it as a "
                "goal, or keep it for today")
    return None


def overlay_problem(record: dict) -> str | None:
    """An overlay record is admitted only if it declares `dyad:extends: dmc:attention-strategy` and none of its outcomes
    declares the effect `acts` or `skips`: an overlay may add an order or a tie-break, never authorize or skip a
    question."""
    if record.get("dyad:extends") != f"dmc:{RECORD}":
        return f"it does not declare dyad:extends dmc:{RECORD}"
    bad = [t.get("termCode", "?") for t in record.get("hasDefinedTerm", []) if t.get("dyad:effect") in ("acts", "skips")]
    return f"outcome(s) {', '.join(bad)} declare acts or skips" if bad else None


# ---- the store (reads the checkout and the clone)

def attention():
    return dyadlib.load_module(dyadlib.PKG / "scripts" / "attention.py", "dyad_attention")


def board():
    return dyadlib.load_guard("agent", "board")


def cos_entry(root: Path) -> tuple[str, dict[str, str]]:
    bd = board()
    name = bd.cos_name(bd.viewer_cabinet(root))
    return name, dict(bd.load(root)).get(name, {})


def read(root: Path) -> Store:
    """The operator's store: central when this checkout names a clone that is a git checkout, else the fallback."""
    clone = attention().config(root)["clone"]
    if clone is not None and (clone / ".git").exists():
        d = clone / CENTRAL_DIR
        rd = lambda n: (d / n).read_text(errors="replace") if (d / n).is_file() else ""
        return Store("central", d, parse_goals(rd("goals.md")), parse_focus_file(rd("focus.md")),
                     parse_settings(rd("settings.md")), clone)
    p = root / FALLBACK_REL
    text = p.read_text(errors="replace") if p.is_file() else ""
    return Store("fallback", p, parse_goals(text), parse_focus_key(cos_entry(root)[1].get("focus", "")),
                 parse_settings(text))


def settings(root: Path, st: Store) -> dict:
    """Each setting from the operator's store first, then `preferences-corpus/PREFERENCES.md`, then the record's
    default; a value outside what the record allows reads as the default. The next-best order's weights (#709,
    `dmc:next-best-disposition`) are read the same way: they are the operator's too."""
    out = {}
    conflict = (st.settings.get("attention-conflict") or dyadlib.preference("attention-conflict", root)
                or CONFLICTS[0]).strip()
    out["attention-conflict"] = conflict if conflict in CONFLICTS else CONFLICTS[0]
    for k in TUNABLES:
        e, default = dyadlib.tunable_entry(k), float(dyadlib.tunable_default(k))
        v = None
        for text in (st.settings.get(k), dyadlib.preference(k, root)):
            v = dyadlib.tunable_value(text, default, e.get("dyad:allowed", "")) if text else None
            if v is not None:
                break
        out[k] = float(v if v is not None else default)
    return out


def serves(root: Path, cos: dict[str, str], rows: dict) -> tuple[dict[int, str | None], list[str]]:
    """The home's grounding, `serves:` lines `#<id> G<n>|none (<reason>) @<ISO time>` on its cross-row entry: {row:
    goal id or None}, and a warning for each line unread, naming no row, or written before the row last changed
    (stale: dropped, to be re-recorded before it is used)."""
    out, warns = {}, []
    bd = board()
    for line in filter(None, (l.strip() for l in (cos.get("serves") or "").splitlines())):
        m = SERVES_LINE.match(line)
        if not m:
            warns.append(f"serves: unread line {line!r} (`#<id> G<n>|none (<reason>) @<ISO time>`)")
            continue
        rid, at = int(m["id"]), parse_when(m["at"])
        if rid not in rows:
            warns.append(f"serves: dropped #{rid}: no such row")
            continue
        changed = bd._row_changed_at(root, rid)
        if at is None or (changed is not None and changed > at):
            warns.append(f"serves: dropped #{rid}: the row changed after the line was written; re-record it")
            continue
        out[rid] = None if m["goal"] == "none" else m["goal"]
    return out, warns


def overlays(st: Store) -> list[tuple[str, str | None]]:
    """[(record file, refusal or None)] for the operator's overlay records (central store only)."""
    d = st.where / "dmc" if st.kind == "central" else None
    if d is None or not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.jsonld")):
        try:
            out.append((p.name, overlay_problem(json.loads(p.read_text()))))
        except (OSError, ValueError) as e:
            out.append((p.name, f"unreadable ({type(e).__name__})"))
    return out


def candidates(root: Path) -> tuple[list[dict], dict, list[str]]:
    """The candidates the home would show or propose: the Recommended items (`dmc:recommended-next`, in its kind order)
    and the rest of the backlog behind them, each with its class (`promote`'s recorded promotion class, else the kind)
    and its urgency index; then {row: Row} and the warnings."""
    bd = board()
    got = bd.load(root)
    cab = bd.viewer_cabinet(root)
    rows = {r.id: r for r in dyadlib.read_rows(root)}
    items, warns = bd.recommended(root, got, cab)
    cos = dict(got).get(bd.cos_name(cab), {})
    cls = {}
    for line in (l.strip() for l in (cos.get("recommended") or "").splitlines()):
        m = bd.RECOMMENDED_LINE.match(line)
        if m and m["kind"] == "promote":
            cls[int(m["id"])] = m["outcome"]
    out, seen, u = [], set(), 0
    for kind in bd.RECOMMENDED_KINDS:
        for i in items.get(kind) or []:
            if i is None or i in seen:
                continue
            seen.add(i)
            c = cls.get(i, kind)
            out.append({"id": i, "title": rows[i].title if i in rows else "", "kind": kind, "cls": c,
                        "urgency": u + (int(c[1]) if re.fullmatch(r"P[1-6]", c) else 0)})
            u += 10
    for r in sorted(rows.values(), key=lambda r: (r.opened, r.id)):
        if r.state == "backlog" and r.id not in seen:
            out.append({"id": r.id, "title": r.title, "kind": "backlog", "cls": "backlog", "urgency": u})
            u += 1
    return out, rows, warns


def ordered(root: Path, now: datetime.datetime | None = None) -> tuple[list[dict], Store, list[str]]:
    """The candidates in the strategy's order, the store read, and every warning (serves, overlays, defaults)."""
    now = now or datetime.datetime.now(datetime.UTC)
    st = read(root)
    s = settings(root, st)
    cands, rows, warns = candidates(root)
    grounds, w2 = serves(root, cos_entry(root)[1], rows)
    warns += w2
    warns += [f"overlay {n} refused: {why}" for n, why in overlays(st) if why]
    if not st.goals:
        warns.append(NO_GOALS)
    return order(cands, st.goals, grounds, st.focus, s, now), st, warns


def goal_label(c: dict) -> str:
    return f"serves {c['goal']}" if c.get("goal") else "serves none"


def order_lines(root: Path, full: bool = False, now: datetime.datetime | None = None) -> list[str]:
    """`dyad attention order [--full]`: one line per candidate, in the strategy's order, with its class, its tier, its
    grounding and today's focus weight; never a goal's words. Read-only."""
    now = now or datetime.datetime.now(datetime.UTC)
    items, st, warns = ordered(root, now)
    s = settings(root, st)
    on = dyadlib.slugs_on(root)
    rows = {r.id: r for r in dyadlib.read_rows(root)}
    shown = items if full else items[:10]
    out = [f"attention order: {len(items)} candidate(s), {s['attention-conflict']}, store {st.kind}"
           + ("" if full or len(items) <= 10 else f" (first 10; --full for all)")]
    for c in shown:
        owed = " owed" if c["cls"] in OWED else ""
        out.append(f"  {dyadlib.row_label(c['id'], rows, on)} {c['kind']} {c['cls']}{owed} — {goal_label(c)}, "
                   f"tier {c['tier']}, focus {c['focus']:.2f}")
    if (d := departs(st.focus, items, st.goals, now)):
        out.append(d)
    out += warns
    return out


def goals_lines(root: Path, today: datetime.date | None = None) -> list[str]:
    """`dyad attention goals`: the goal stack, each goal's id, horizon, review date (`overdue` when past) and status,
    and its words: printed in chat only, never written to a public record."""
    today = today or datetime.date.fromisoformat(dyadlib.utc_date())
    st = read(root)
    out = [f"attention goals: {len(st.goals)} goal(s), store {st.kind}"
           + (" (in this repository, and so public)" if st.kind == "fallback" else "")]
    for g in st.goals:
        due = " overdue" if g.status == "active" and g.review < today.isoformat() else ""
        out.append(f"{g.id} {g.horizon} review {g.review}{due} [{g.status}]")
        out += [f"  {l}" for l in g.words.splitlines()]
    if not st.goals:
        out.append(NO_GOALS)
    return out


# ---- writes

def commit_push(clone: Path, path: Path, message: str, out=print) -> int:
    """Commit one file in the clone and try one push, as sync does: a failed push keeps the commit for the next."""
    git = attention().git
    git(["add", str(path.relative_to(clone))], clone)
    if git(["commit", "-q", "-m", message], clone).returncode != 0:
        out("attention: nothing to commit")
        return 1
    if git(["push", "-q"], clone, timeout=120).returncode != 0:
        out(f"attention: committed in the clone; the push failed, the next sync pushes it")
        return 0
    out(f"attention: {message}")
    return 0


def next_goal_id(goals: list[Goal]) -> str:
    """Ids are never reused: one past the highest ever written."""
    return f"G{max((int(g.id[1:]) for g in goals), default=0) + 1}"


def goal_add(root: Path, horizon: str, review: str, said: str, out=print) -> int:
    if horizon not in HORIZONS:
        out(f"refused: --horizon is {' or '.join(HORIZONS)}, not {horizon!r}")
        return 1
    try:
        datetime.date.fromisoformat(review)
    except ValueError:
        out(f"refused: --review is a date YYYY-MM-DD, not {review!r}")
        return 1
    if not said.strip():
        out("refused: the --said-file holds no words; a goal is the operator's words, never composed")
        return 1
    st = read(root)
    g = Goal(next_goal_id(st.goals), horizon, review, "active", said)
    return _write_goals(root, st, st.goals + [g], f"goal {g.id} {horizon} added", out)


def goal_retire(root: Path, gid: str, out=print) -> int:
    st = read(root)
    hit = [g for g in st.goals if g.id == gid]
    if not hit:
        out(f"refused: no goal {gid} in the {st.kind} store")
        return 1
    if hit[0].status == "retired":
        out(f"refused: {gid} is already retired")
        return 1
    goals = [Goal(g.id, g.horizon, g.review, "retired" if g.id == gid else g.status, g.words) for g in st.goals]
    return _write_goals(root, st, goals, f"goal {gid} retired", out)


def _write_goals(root: Path, st: Store, goals: list[Goal], message: str, out) -> int:
    text = "# Goals\n\n" + "\n".join(render_goal(g) for g in goals)
    if st.kind == "central":
        st.where.mkdir(parents=True, exist_ok=True)
        p = st.where / "goals.md"
        p.write_text(text)
        return commit_push(st.clone, p, f"attention: {message}", out)
    # the fallback is operator-owned: a preferences-zone PR the home presents as its own question; nothing is written
    old = (root / FALLBACK_REL).read_text(errors="replace") if (root / FALLBACK_REL).is_file() else ""
    keep = "\n".join(f"{k}: {v}" for k, v in parse_settings(old).items())
    new = "# Attention (operator-owned; public, in this repository)\n\n" + (keep + "\n\n" if keep else "") + text
    out(f"attention: no central repository named; {message} is a preferences-zone PR to {FALLBACK_REL} "
        "(public, in this repository), presented as its own question. Its content:")
    out(new)
    return 0


def focus_add(root: Path, source: str, text: str, now: datetime.datetime | None = None, out=print) -> int:
    if source not in SOURCES or not text.strip():
        out("refused: a focus is --said-file <f> (the operator's words) or --inferred \"<one line>\"")
        return 1
    if source == "inferred" and "\n" in text.strip():
        out("refused: an inferred focus is one line, the home's reading")
        return 1
    f = Focus(now or datetime.datetime.now(datetime.UTC), source, text.strip())
    st = read(root)
    if st.kind == "central":
        st.where.mkdir(parents=True, exist_ok=True)
        p = st.where / "focus.md"
        prior = p.read_text(errors="replace") if p.is_file() else "# Focus (append-only)\n"
        p.write_text(prior.rstrip("\n") + "\n\n" + render_focus(f))
        rc = commit_push(st.clone, p, f"attention: focus {source} {iso(f.at)}", out)
    else:
        one = " ".join(f.text.split())
        name, cos = cos_entry(root)
        lines = [l for l in (cos.get("focus") or "").splitlines() if l.strip()]
        lines = (lines + [f"{iso(f.at)} {source}: {one}"])[-FOCUS_KEEP:]
        rc = board().cmd_set([name, "focus=" + "\n".join(lines)], root)
    if rc == 0 and source == "inferred":
        out(f"attention: reading today's focus as {f.text.strip()!r} (inferred, weight "
            f"{settings(root, st)['inferred-focus-weight']}); correct it with a stated focus")
    return rc


# ---- the weekly goal review (the grooming report reads these)

def review_lines(root: Path, since: datetime.datetime | None, today: datetime.date | None = None) -> list[str]:
    """The groom report's `goals:` lines and the uptake count: each goal with its review date (`overdue` when past) and
    the rows its current serves lines name, recorded since the last review; then `uptake:` — of the rows promoted or
    recommended on the home's cross-row entry since then, how many have left `backlog` for work, by goal. A proxy for
    the strategy's effect, stated as one; the replies per disposition stay the measure of attention."""
    today = today or datetime.date.fromisoformat(dyadlib.utc_date())
    st = read(root)
    rows = {r.id: r for r in dyadlib.read_rows(root)}
    name, cos = cos_entry(root)
    grounds = {}
    for line in (l.strip() for l in (cos.get("serves") or "").splitlines()):
        m = SERVES_LINE.match(line)
        if m and (at := parse_when(m["at"])) and (since is None or at >= since):
            grounds[int(m["id"])] = None if m["goal"] == "none" else m["goal"]
    out = []
    for g in st.goals:
        due = " overdue" if g.status == "active" and g.review < today.isoformat() else ""
        served = sorted(i for i, gid in grounds.items() if gid == g.id)
        out.append(f"goals: {g.id} {g.horizon} review {g.review}{due} [{g.status}] served: "
                   + (" ".join(f"#{i}" for i in served) or "none"))
    if not st.goals:
        out.append("goals: none recorded")
    offered = offered_since(root, name, since)
    by: dict[str, list[int]] = {}
    for i in offered:
        by.setdefault(grounds.get(i) or "none", []).append(i)
    taken = lambda ids: sum(1 for i in ids if i in rows and rows[i].state not in ("backlog", "archived"))
    parts = ", ".join(f"{k} {taken(v)}/{len(v)}" for k, v in sorted(by.items()))
    out.append(f"uptake: {taken(offered)} of {len(offered)} offered taken up" + (f" ({parts})" if parts else "")
               + " — a proxy for the strategy's effect, not the measure of attention")
    return out


def offered_since(root: Path, cos_name: str, since: datetime.datetime | None) -> list[int]:
    """The rows a `promote` or `hardening` line of the cross-row entry offered since `since`, from git's history of
    that file (the board is overwritten, its history git's)."""
    inst = dyadlib.instance_rel(root) or "agent-corpus"
    path = f"{inst}/d-work/board/{cos_name}.md"
    args = ["git", "log", "-p", "--format=", "--", path]
    if since is not None:
        args[3:3] = [f"--since={since.isoformat()}"]
    try:
        r = subprocess.run(args, cwd=root, capture_output=True, text=True, env=dyadlib.git_env(), timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    ids = re.findall(r"^\+(?:recommended: |\s+)(?:promote|hardening) #(\d+):", r.stdout, re.M)
    return list(dict.fromkeys(int(i) for i in ids))


# ---- the attention calendar (d-work #740; dyad/dmc/attention-calendar.jsonld): when, never what

CALENDAR_RECORD = "attention-calendar"
CALENDAR_OUTCOMES = ("owed", "no-calendar", "in-window", "next-window")   # the record's precedence order
CALENDAR_TUNABLES = ("calendar-question-minutes", "calendar-window-min")
WINDOWS_CENTRAL = "windows.md"                     # in the central repository's operator/
WINDOWS_LOCAL = "dyad-attention-windows.txt"       # else in the git common dir, never tracked
WINDOW_LINE = re.compile(r"^(?P<start>\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|[+-]\d{2}:?\d{2}))\s+"
                         r"(?P<end>\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|[+-]\d{2}:?\d{2}))$")
WINDOW_KEY = re.compile(r"^(?P<key>horizon|read):\s*(?P<at>\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|[+-]\d{2}:?\d{2}))$")


@dataclass
class Windows:
    spans: list            # [(start, end)], aware datetimes in the operator's time zone, sorted
    horizon: datetime.datetime
    read: datetime.datetime | None = None


def parse_windows(text: str) -> tuple[Windows | None, list[str]]:
    """(the window list, problems): times only — `<ISO start> <ISO end>` lines, one `horizon:` line and at most one
    `read:` line, each time carrying its offset. Any other text is a problem, so no title or calendar id can enter."""
    spans, keys, problems = [], {}, []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if (m := WINDOW_LINE.match(line)):
            a, b = parse_when(m["start"]), parse_when(m["end"])
            if a is None or b is None or b <= a:
                problems.append(f"line {n}: a window ends after it starts")
            else:
                spans.append((a, b))
        elif (m := WINDOW_KEY.match(line)) and m["key"] not in keys and parse_when(m["at"]):
            keys[m["key"]] = parse_when(m["at"])
        else:
            problems.append(f"line {n}: not a window (`<ISO start> <ISO end>`), `horizon:` or `read:` line; "
                            "the list holds times only")
    if "horizon" not in keys:
        problems.append("no `horizon: <ISO time>` line")
    if problems:
        return None, problems
    return Windows(sorted(spans), keys["horizon"], keys.get("read")), []


def render_windows(w: Windows) -> str:
    out = ([f"read: {w.read.isoformat(timespec='minutes')}"] if w.read else []) + [f"horizon: {w.horizon.isoformat(timespec='minutes')}"]
    return "\n".join(out + [f"{a.isoformat(timespec='minutes')} {b.isoformat(timespec='minutes')}" for a, b in w.spans]) + "\n"


def at_label(d: datetime.datetime) -> str:
    """`Tue 14:00`, in the window's own time zone."""
    return d.strftime("%a %H:%M")


def calendar_outcomes(items: list[dict], w: Windows | None, now: datetime.datetime, minutes: float,
                      window_min: float) -> list[tuple[str, datetime.datetime | None]]:
    """dmc:attention-calendar, mechanical and pure: for each question ready to ask, in the order already given, its
    outcome and, for `next-window`, the next window's start (None when no window lies before the horizon). An item with
    `owed` true is asked now; with no list, or one past its horizon, nothing is held; inside a window at least
    `window_min` long, a question is asked while it fits the window's remaining minutes after those placed before it;
    every other one is held for the next window, never refused."""
    usable = [(a, b) for a, b in (w.spans if w else []) if (b - a).total_seconds() / 60 >= window_min]
    expired = w is None or now > w.horizon
    current = next(((a, b) for a, b in usable if a <= now < b), None)
    upcoming = next((a for a, b in usable if a > now), None)
    left = (current[1] - now).total_seconds() / 60 if current else 0.0
    out = []
    for it in items:
        if it.get("owed"):
            out.append(("owed", None))
        elif expired:
            out.append(("no-calendar", None))
        elif current and left >= minutes:
            left -= minutes
            out.append(("in-window", None))
        else:
            out.append(("next-window", upcoming))
    return out


def windows_path(root: Path) -> tuple[Path, Path | None]:
    """Where the window list lives: the central repository's operator/windows.md when a clone is named, else the git
    common dir's untracked file; (path, clone or None)."""
    clone = attention().config(root)["clone"]
    if clone is not None and (clone / ".git").exists():
        return clone / CENTRAL_DIR / WINDOWS_CENTRAL, clone
    r = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root,
                       capture_output=True, text=True, env=dyadlib.git_env())
    return Path(r.stdout.strip() or root / ".git") / WINDOWS_LOCAL, None


def read_windows(root: Path) -> Windows | None:
    p, _ = windows_path(root)
    return parse_windows(p.read_text(errors="replace"))[0] if p.is_file() else None


def calendar_settings(root: Path) -> tuple[float, float]:
    return tuple(float(dyadlib.tunable(k, root)) for k in CALENDAR_TUNABLES)


def windows_set(root: Path, text: str, now: datetime.datetime | None = None, out=print) -> int:
    """`dyad attention windows --set-file <f>`: the home's composition of its connector read, times only; refused
    whole on any other line. Written to the central repository (committed there) or the untracked local file."""
    w, problems = parse_windows(text)
    if problems:
        for line in problems:
            out(f"refused: {line}")
        return 1
    w.read = now or datetime.datetime.now(datetime.UTC)
    p, clone = windows_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_windows(w))
    if clone is not None:
        return commit_push(clone, p, f"windows: {len(w.spans)} window(s), horizon {iso(w.horizon)}", out)
    out(f"attention: {len(w.spans)} window(s) written to this checkout's untracked store, horizon {iso(w.horizon)}")
    return 0


def calendar_lines(root: Path, now: datetime.datetime | None = None, shown: int = 5) -> list[str]:
    """`dyad attention calendar`, read-only: the next windows, times only, or `no window list` with how to make one."""
    now = now or datetime.datetime.now(datetime.UTC)
    w = read_windows(root)
    if w is None:
        return ["no window list: the home writes one from its calendar connector, `dyad attention windows --set-file <f>`"]
    if now > w.horizon:
        return [f"window list past its horizon ({iso(w.horizon)}): the calendar holds nothing until the home reads it again"]
    nxt = [(a, b) for a, b in w.spans if b > now][:shown]
    read = f"read {w.read.astimezone(w.horizon.tzinfo).strftime('%Y-%m-%d %H:%M')}, " if w.read else ""
    days = max(0, round((w.horizon - (w.read or now)).total_seconds() / 86400))
    body = ", ".join(f"{at_label(a)}–{b.strftime('%H:%M')}" for a, b in nxt) or "none before the horizon"
    return [f"next windows: {body} ({read}horizon {days} days)"]


# ---- CLI

def flag(a: list[str], name: str) -> str | None:
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else None


def main(argv: list[str], root: Path | None = None) -> int:
    root = root or dyadlib.repo_root()
    a = list(argv)
    if a == ["goals"]:
        print("\n".join(goals_lines(root)))
        return 0
    if a[:1] == ["order"] and a[1:] in ([], ["--full"]):
        print("\n".join(order_lines(root, full=a[1:] == ["--full"])))
        return 0
    if a[:2] == ["goal", "add"]:
        h, rv, f = flag(a, "--horizon"), flag(a, "--review"), flag(a, "--said-file")
        if None in (h, rv, f) or len(a) != 8:
            print(USAGE, file=sys.stderr)
            return 1
        return goal_add(root, h, rv, Path(f).read_text())
    if a[:2] == ["goal", "retire"] and len(a) == 3 and GOAL_ID.fullmatch(a[2]):
        return goal_retire(root, a[2])
    if a[:1] == ["focus"] and len(a) == 3 and a[1] in ("--said-file", "--inferred"):
        return focus_add(root, "stated" if a[1] == "--said-file" else "inferred",
                         Path(a[2]).read_text() if a[1] == "--said-file" else a[2])
    print(USAGE, file=sys.stderr)
    return 1


INVARIANTS = [   # crafts/syseng/rules/invariants.md: pure, enforced at import
    ("goals-first-is-the-default-conflict", lambda: CONFLICTS[0] == "goals-first" and set(CONFLICTS) == {"goals-first", "blend"}),
    ("the-focus-floor-is-five-hundredths", lambda: FLOOR == 0.05),
    ("owed-comes-before-any-goal", lambda: sort_key(True, 0, 0.0, 99, "goals-first") < sort_key(False, 2, 1.0, 0, "goals-first")
        and sort_key(True, 0, 0.0, 99, "blend") < sort_key(False, 2, 1.0, 0, "blend")),
    ("under-goals-first-focus-never-lifts-a-tier", lambda: sort_key(False, 1, 0.0, 9, "goals-first")
        < sort_key(False, 0, 1.0, 0, "goals-first")),
    ("a-stale-focus-counts-as-none", lambda: decay("stated", 30, 1, 0.5) == 0.0 and decay("stated", 0, 1, 0.5) == 1.0),
    ("an-overlay-that-skips-is-refused", lambda: overlay_problem({"dyad:extends": f"dmc:{RECORD}", "hasDefinedTerm":
        [{"termCode": "x", "dyad:effect": "skips"}]}) is not None
        and overlay_problem({"dyad:extends": f"dmc:{RECORD}", "hasDefinedTerm": [{"dyad:effect": "shapes"}]}) is None),
    ("goal-ids-are-never-reused", lambda: next_goal_id([Goal("G1", "long-term", "2026-01-01", "retired", "x"),
        Goal("G3", "intermediate", "2026-01-01", "active", "y")]) == "G4"),
    ("a-window-list-holds-times-only", lambda: parse_windows("2026-11-17T09:00+01:00 2026-11-17T10:00+01:00\n"
        "horizon: 2026-11-23T00:00+01:00")[0] is not None and parse_windows("2026-11-17T09:00Z 2026-11-17T10:00Z standup\n"
        "horizon: 2026-11-23T00:00Z")[0] is None),
    ("an-owed-question-is-never-held", lambda: calendar_outcomes([{"owed": True}], None,
        datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC), 3, 10) == [("owed", None)]),
    ("a-goal-round-trips", lambda: parse_goals(render_goal(Goal("G2", "intermediate", "2026-12-01", "active",
        "## not a heading\n| pipe")))[0].words == "## not a heading\n| pipe"),
]
dyadlib.enforce(INVARIANTS, __name__)   # Rule-12 p1: the fail-loud check, at import
TUNABLES = ("focus-half-life-days", "inferred-focus-weight", *NBD_WEIGHTS)   # the operator's settings (SETTINGS)
READ_TUNABLES = (*TUNABLES, *CALENDAR_TUNABLES)   # #740: every tunable this module reads, the calendar's through dyadlib.tunable
TREE_INVARIANTS = [   # read the records, so never at import
    ("the-tunables-are-the-records", lambda: dyadlib.tunables_read_by("scripts/strategy.py") == set(READ_TUNABLES)),
    ("the-calendar-outcomes-are-the-records", lambda: [t["termCode"] for t in json.loads((dyadlib.PKG / "dmc" / f"{CALENDAR_RECORD}.jsonld").read_text())["hasDefinedTerm"]]
        == list(CALENDAR_OUTCOMES)),
    ("the-settings-are-the-tunables-and-the-conflict", lambda: set(SETTINGS) == {"attention-conflict", *TUNABLES}),
]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

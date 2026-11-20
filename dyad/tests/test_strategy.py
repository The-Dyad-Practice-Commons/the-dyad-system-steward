"""scripts/strategy.py (the operator's attention strategy; d-work #705; dmc:attention-strategy): the definition of done's
tests — two operators' settings giving different orders from the same rows with no code change; a focus decaying to
nothing; this operator's default putting goal alignment first; a focus departing every goal shown once with those
goals; with no goals the order unchanged — and an overlay refused on `acts` or `skips`, the settings' precedence, the
fallback focus on the home's cross-row entry, a stale `serves:` line dropped, no goal's words in any board line, the
central store's goal and focus writes, and the grooming's `goals:` and `uptake:` lines."""
import datetime, os, subprocess, sys, tempfile, unittest, unittest.mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dyadlib
st = dyadlib.load_module(Path(__file__).resolve().parents[1] / "scripts" / "strategy.py", "dyad_strategy_test")
board = dyadlib.load_guard("agent", "board")

NOW = datetime.datetime(2026, 11, 14, 12, 0, tzinfo=datetime.UTC)
GOALS = [st.Goal("G1", "long-term", "2026-12-01", "active", "ship the practice to a second operator"),
         st.Goal("G2", "intermediate", "2026-11-01", "active", "cut the questions per week in half")]
DEFAULTS = {"attention-conflict": "goals-first", "focus-half-life-days": 1.0, "inferred-focus-weight": 0.5,
            "nbd-criticality-weight": 1.0, "nbd-age-weight": 0.5}   # #709: the next-best weights are the operator's too
ROW = "id: {id}\ntitle: {title}\nopened: 2026-11-0{d}\nstate: {state}\ndisposed: 2026-11-01 Y backlog\nrefs: \n"


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=dyadlib.git_env(), check=True)


def cands():
    """Four backlog rows: #10 a live defect (P1), #11 serves G2, #12 serves G1, #13 serves none and is today's focus."""
    return [{"id": 10, "title": "fix the fence", "cls": "P1", "urgency": 100},
            {"id": 11, "title": "fewer questions", "cls": "P4", "urgency": 400},
            {"id": 12, "title": "second operator", "cls": "P5", "urgency": 500},
            {"id": 13, "title": "publish chronicle episode", "cls": "P3", "urgency": 300}]


SERVES = {11: "G2", 12: "G1", 13: None}


class OrderTests(unittest.TestCase):
    def ids(self, settings, focus=()):
        return [c["id"] for c in st.order(cands(), GOALS, SERVES, list(focus), settings, NOW)]

    def test_two_operators_settings_give_different_orders_from_the_same_rows(self):
        f = [st.Focus(NOW, "stated", "today: publish the chronicle episode")]
        a = self.ids(DEFAULTS, f)                                         # goals-first: focus stays in its tier
        b = self.ids({**DEFAULTS, "attention-conflict": "blend"}, f)       # blend: the day counts for more
        self.assertEqual(a, [10, 12, 11, 13])
        self.assertEqual(b, [10, 12, 13, 11])                              # the focus ties #13 with G2's row, urgency wins
        self.assertEqual(b[0], 10)                                         # owed first under either

    def test_this_operators_default_puts_goal_alignment_first(self):
        self.assertEqual(st.settings(Path(tempfile.mkdtemp()), st.Store("fallback", Path("x"), [], [], {}))[
            "attention-conflict"], "goals-first")
        self.assertEqual(self.ids(DEFAULTS), [10, 12, 11, 13])            # owed, long-term, intermediate, none

    def test_a_focus_decays_to_nothing(self):
        self.assertEqual(st.decay("stated", 0, 1, 0.5), 1.0)
        self.assertAlmostEqual(st.decay("stated", 1, 1, 0.5), 0.5)
        self.assertAlmostEqual(st.decay("inferred", 0, 1, 0.5), 0.5)
        self.assertEqual(st.decay("stated", 5, 1, 0.5), 0.0)              # 1/32 < 0.05: none
        old = [st.Focus(NOW - datetime.timedelta(days=6), "stated", "#13")]
        blend = {**DEFAULTS, "attention-conflict": "blend"}
        self.assertEqual(self.ids(blend, old), self.ids(blend))            # a faded focus moves nothing

    def test_with_no_goals_the_order_is_unchanged(self):
        got = [c["id"] for c in st.order(cands(), [], {}, [], DEFAULTS, NOW)]
        self.assertEqual(got, [10, 13, 11, 12])                            # owed, then the existing urgency
        self.assertEqual(st.order(cands(), [], {}, [], DEFAULTS, NOW)[1]["goal"], None)

    def test_a_retired_goal_grounds_nothing(self):
        retired = [GOALS[0], st.Goal("G2", "intermediate", "2026-11-01", "retired", "x")]
        got = {c["id"]: c for c in st.order(cands(), retired, SERVES, [], DEFAULTS, NOW)}
        self.assertIsNone(got[11]["goal"])
        self.assertEqual(got[12]["goal"], "G1")

    def test_a_focus_departing_every_goal_is_shown_once_with_those_goals(self):
        f = [st.Focus(NOW - datetime.timedelta(hours=1), "stated", "publish the chronicle episode")]
        items = st.order(cands(), GOALS, SERVES, f, DEFAULTS, NOW)
        line = st.departs(f, items, GOALS, NOW)
        self.assertIn("#13", line)
        self.assertIn("G1, G2", line)
        self.assertNotIn(GOALS[0].words, line)                              # by id, never the words
        self.assertIsNone(st.departs(f, items, [], NOW))                   # no goals: nothing departs
        self.assertIsNone(st.departs([st.Focus(NOW, "stated", "#12")], items, GOALS, NOW))   # matches a goal's row

    def test_an_overlay_that_acts_or_skips_is_refused(self):
        ext = {"dyad:extends": "dmc:attention-strategy"}
        self.assertIsNone(st.overlay_problem({**ext, "hasDefinedTerm": [{"termCode": "tie", "dyad:effect": "shapes"}]}))
        for eff in ("acts", "skips"):
            self.assertIn(eff, st.overlay_problem({**ext, "hasDefinedTerm": [{"termCode": "x", "dyad:effect": eff}]}))
        self.assertIn("dyad:extends", st.overlay_problem({"hasDefinedTerm": []}))

    def test_goal_text_round_trips_inside_its_fence(self):
        g = st.Goal("G7", "long-term", "2027-01-01", "active", "## not a heading\n```\nstatus: retired")
        back = st.parse_goals(st.render_goal(g))
        self.assertEqual((back[0].words, back[0].status), (g.words, "active"))


class StoreTests(unittest.TestCase):
    def setUp(self):
        e = unittest.mock.patch.dict(os.environ, {"DYAD_INSTANCE": "agent-corpus", "DYAD_SESSION": "program-aaaaaaaa"})
        e.start(); self.addCleanup(e.stop)
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(self.tmp)]))
        self.root = self.tmp / "sys"
        git(["init", "-q", "-b", "main", str(self.root)], self.tmp)
        git(["config", "user.name", "t"], self.root); git(["config", "user.email", "t@t"], self.root)
        d = self.root / "agent-corpus" / "d-work"
        for sub in ("rows", "board"):
            (d / sub).mkdir(parents=True)
        for i, (title, state) in enumerate([("fewer questions", "backlog"), ("second operator", "backlog"),
                                            ("chronicle episode", "open")], start=11):
            (d / "rows" / f"{i}.md").write_text(ROW.format(id=i, title=title, d=i - 10, state=state))
        self.cos = d / "board" / "_cos.md"
        self.cos.write_text("holder: program-aaaaaaaa\n")
        git(["add", "-A"], self.root); git(["commit", "-q", "-m", "init"], self.root)

    def prefs(self, **kv):
        p = self.root / dyadlib.PREFERENCES_REL; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("| key | value | allowed | read by |\n|---|---|---|---|\n"
                     + "".join(f"| {k} | {v} | x | y |\n" for k, v in kv.items()))

    def central(self) -> Path:
        clone = self.tmp / "central"
        git(["init", "-q", "-b", "main", str(clone)], self.tmp)
        git(["config", "user.name", "t"], clone); git(["config", "user.email", "t@t"], clone)
        git(["commit", "-q", "--allow-empty", "-m", "s"], clone)
        git(["config", "dyad.attention.clone", str(clone)], self.root)
        return clone

    def test_the_settings_precedence_is_store_then_preferences_then_default(self):
        s0 = st.settings(self.root, st.read(self.root))
        self.assertEqual(s0, DEFAULTS)
        self.prefs(**{"attention-conflict": "blend", "focus-half-life-days": "3"})
        self.assertEqual(st.settings(self.root, st.read(self.root))["attention-conflict"], "blend")
        clone = self.central()
        (clone / "operator").mkdir()
        (clone / "operator" / "settings.md").write_text("attention-conflict: goals-first\ninferred-focus-weight: 0.25\n")
        s = st.settings(self.root, st.read(self.root))
        self.assertEqual((s["attention-conflict"], s["focus-half-life-days"], s["inferred-focus-weight"]),
                         ("goals-first", 3.0, 0.25))
        (clone / "operator" / "settings.md").write_text("attention-conflict: whatever\ninferred-focus-weight: 7\n")
        s = st.settings(self.root, st.read(self.root))
        self.assertEqual((s["attention-conflict"], s["inferred-focus-weight"]), ("goals-first", 0.5))

    def test_the_next_best_weights_are_read_store_first_and_a_negative_reads_the_default(self):
        """#709: `nbd-criticality-weight` and `nbd-age-weight` are the operator's settings: the store, then the
        preferences, then the record; 0 turns a term off, and a negative value reads as the default."""
        self.prefs(**{"nbd-age-weight": "2"})
        self.assertEqual(st.settings(self.root, st.read(self.root))["nbd-age-weight"], 2.0)
        clone = self.central()
        (clone / "operator").mkdir()
        (clone / "operator" / "settings.md").write_text("nbd-age-weight: 0\nnbd-criticality-weight: -1\n")
        s = st.settings(self.root, st.read(self.root))
        self.assertEqual((s["nbd-age-weight"], s["nbd-criticality-weight"]), (0.0, 1.0))

    def test_the_central_store_takes_goals_and_focus_and_retires_without_reuse(self):
        clone = self.central()
        said = "ship the practice to a second operator"
        out = []
        self.assertEqual(st.goal_add(self.root, "long-term", "2026-12-01", said, out=out.append), 0)
        self.assertEqual(st.goal_add(self.root, "intermediate", "2026-11-20", "fewer questions", out=out.append), 0)
        self.assertEqual(st.goal_retire(self.root, "G1", out=out.append), 0)
        self.assertEqual(st.goal_add(self.root, "intermediate", "2026-12-20", "third", out=out.append), 0)
        gs = st.read(self.root).goals
        self.assertEqual([(g.id, g.status) for g in gs], [("G1", "retired"), ("G2", "active"), ("G3", "active")])
        self.assertEqual(gs[0].words, said)
        self.assertNotEqual(st.goal_add(self.root, "someday", "2026-12-01", "x", out=out.append), 0)
        self.assertNotEqual(st.goal_add(self.root, "long-term", "2026-12-01", "  ", out=out.append), 0)
        self.assertEqual(st.focus_add(self.root, "inferred", "the release", NOW, out=out.append), 0)
        self.assertTrue(any("reading today's focus as" in l for l in out))
        fs = st.read(self.root).focus
        self.assertEqual([(f.source, f.text) for f in fs], [("inferred", "the release")])
        self.assertIn("goals.md", git(["log", "--name-only", "--format="], clone).stdout)
        self.assertNotIn(said, self.cos.read_text())                       # no goal text on the public board
        self.assertFalse((self.root / st.FALLBACK_REL).exists())

    def test_the_fallback_prints_a_preferences_pr_and_keeps_the_focus_on_the_cross_row_entry(self):
        out = []
        self.assertEqual(st.goal_add(self.root, "long-term", "2026-12-01", "a goal", out=out.append), 0)
        self.assertIn("preferences-zone PR", out[0])
        self.assertIn("## G1 long-term review 2026-12-01", out[1])
        self.assertFalse((self.root / st.FALLBACK_REL).exists())            # operator-owned: nothing written
        calls = []
        with unittest.mock.patch.object(board, "cmd_set", lambda a, repo: calls.append(a) or 0), \
                unittest.mock.patch.object(st, "board", lambda: board):
            self.assertEqual(st.focus_add(self.root, "stated", "the\nrelease", NOW, out=out.append), 0)
        self.assertEqual(calls, [["_cos", "focus=2026-11-14T12:00Z stated: the release"]])
        self.assertEqual(st.parse_focus_key("2026-11-14T12:00Z stated: the release")[0].text, "the release")

    def test_a_stale_serves_line_is_dropped_with_a_warning(self):
        rows = {r.id: r for r in dyadlib.read_rows(self.root)}
        cos = {"serves": "#11 G2 (fewer asks) @2026-11-14T00:00Z\n#12 none (no goal) @2026-11-14T00:00Z\nbad line"}
        changed = {11: datetime.datetime(2026, 11, 14, 6, tzinfo=datetime.UTC),
                   12: datetime.datetime(2026, 11, 13, tzinfo=datetime.UTC)}
        with unittest.mock.patch.object(board, "_row_changed_at", lambda root, rid: changed.get(rid)):
            got, warns = st.serves(self.root, cos, rows)
        self.assertEqual(got, {12: None})
        self.assertTrue(any("dropped #11" in w for w in warns))
        self.assertTrue(any("unread line" in w for w in warns))

    def test_no_goal_text_reaches_a_board_line(self):
        clone = self.central()
        st.goal_add(self.root, "intermediate", "2026-12-01", "secret words of the operator", out=lambda m: None)
        self.cos.write_text("holder: program-aaaaaaaa\nrecommended: promote #11: P4 (fewer) @2099-01-01T00:00Z\n"
                            "serves: #11 G1 (fewer asks) @2099-01-01T00:00Z\n")
        line = board.closing_line(self.root)
        self.assertIn("promote (#11 G1)", line)
        self.assertNotIn("secret words", "\n".join(board.board_lines(self.root)) + line)
        self.assertNotIn("secret words", "\n".join(st.order_lines(self.root, full=True)))
        self.assertIn("secret words", "\n".join(st.goals_lines(self.root)))      # chat only

    WINDOWS = "2026-11-17T09:00-08:00 2026-11-17T10:00-08:00\n2026-11-17T14:00-08:00 2026-11-17T15:00-08:00\nhorizon: 2026-11-23T00:00-08:00\n"

    def test_the_window_list_is_written_untracked_or_central_and_read_back(self):
        """#740: with no clone the list lands in the git common dir, untracked; with one, in operator/windows.md,
        committed there; `attention calendar` prints the times only; no tracked path of this checkout is written."""
        before = git(["status", "--porcelain", "--untracked-files=all"], self.root).stdout
        self.assertEqual(st.calendar_lines(self.root, NOW)[0].split(":")[0], "no window list")
        out = []
        self.assertEqual(st.windows_set(self.root, self.WINDOWS, NOW, out=out.append), 0)
        self.assertTrue((self.root / ".git" / st.WINDOWS_LOCAL).is_file())
        self.assertEqual(git(["status", "--porcelain", "--untracked-files=all"], self.root).stdout, before)
        now = datetime.datetime(2026, 11, 17, 8, 0, tzinfo=TZ)
        self.assertEqual(st.calendar_lines(self.root, now),
                         ["next windows: Tue 09:00–10:00, Tue 14:00–15:00 (read 2026-11-14 04:00, horizon 9 days)"])
        self.assertIn("past its horizon", st.calendar_lines(self.root, datetime.datetime(2026, 11, 24, tzinfo=TZ))[0])
        clone = self.central()
        self.assertEqual(st.windows_set(self.root, self.WINDOWS, NOW, out=out.append), 0)
        self.assertTrue((clone / "operator" / st.WINDOWS_CENTRAL).is_file())
        self.assertIn("windows: 2 window(s)", git(["log", "-1", "--format=%s"], clone).stdout)
        self.assertEqual(git(["status", "--porcelain", "--untracked-files=all"], self.root).stdout, before)

    def test_a_list_with_a_title_or_an_id_is_refused_whole(self):
        out = []
        self.assertEqual(st.windows_set(self.root, self.WINDOWS + f"busy {CAL_ID}\n", NOW, out=out.append), 1)
        self.assertTrue(out and all(l.startswith("refused:") for l in out))
        self.assertFalse((self.root / ".git" / st.WINDOWS_LOCAL).exists())

    def test_the_board_holds_a_ready_question_for_the_next_window_and_names_it(self):
        """#740: the closing line's `deferred <n> (next window <weekday> <HH:MM>)`, computed at render; an owed (floor)
        question is never held; with no list nothing is."""
        items = [{"kind": "plan", "outcome": "batch"}, {"kind": "destructive", "outcome": "solo"}]
        now = datetime.datetime(2026, 11, 17, 11, 0, tzinfo=TZ)
        board.hold_for_windows(self.root, items, now)
        self.assertEqual([t["outcome"] for t in items], ["batch", "solo"])          # no list: as today
        st.windows_set(self.root, self.WINDOWS, NOW, out=lambda m: None)
        board.hold_for_windows(self.root, items, now)
        self.assertEqual([t["outcome"] for t in items], ["defer", "solo"])
        self.assertEqual(board.next_window_part(items), " (next window Tue 14:00)")
        self.assertEqual(board.next_window_part([{"outcome": "defer"}]), "")         # held by the bound, not the calendar

    def test_the_grooming_reads_the_goals_and_the_uptake(self):
        self.central()
        st.goal_add(self.root, "long-term", "2026-01-01", "g one", out=lambda m: None)
        self.cos.write_text("holder: program-aaaaaaaa\nrecommended: promote #11: P4 (x) @2026-11-14T00:00Z\n"
                            "  promote #13: P3 (y) @2026-11-14T00:00Z\nserves: #13 G1 (z) @2026-11-14T00:00Z\n")
        git(["add", "-A"], self.root); git(["commit", "-q", "-m", "offer"], self.root)
        lines = st.review_lines(self.root, None, today=datetime.date(2026, 11, 14))
        self.assertIn("goals: G1 long-term review 2026-01-01 overdue [active] served: #13", lines)
        self.assertTrue(lines[-1].startswith("uptake: 1 of 2 offered taken up (G1 1/1, none 0/1) — a proxy"), lines[-1])


TZ = datetime.timezone(datetime.timedelta(hours=-8))
CAL_ID = "abc123" + "@group.calendar." + "google.com"   # assembled, so no tracked file holds the shape whole


def win(day, a, b):
    return (datetime.datetime(2026, 11, day, a, tzinfo=TZ), datetime.datetime(2026, 11, day, b, tzinfo=TZ))


class CalendarTests(unittest.TestCase):
    """#740, dmc:attention-calendar: the record's four outcomes, read mechanically from a times-only window list."""
    W = st.Windows([win(17, 9, 10), win(17, 14, 15), win(18, 9, 9)], datetime.datetime(2026, 11, 23, tzinfo=TZ))

    def outcomes(self, items, now, w=None):
        return st.calendar_outcomes(items, self.W if w is None else w, now, 3, 10)

    def test_inside_a_window_questions_fit_in_order_and_the_rest_wait_for_the_next(self):
        now = datetime.datetime(2026, 11, 17, 9, 54, tzinfo=TZ)            # six minutes left: two questions fit
        got = self.outcomes([{}, {}, {}], now)
        self.assertEqual([o for o, _ in got], ["in-window", "in-window", "next-window"])
        self.assertEqual(got[2][1], win(17, 14, 15)[0])

    def test_outside_every_window_a_question_is_held_for_the_next_and_an_owed_one_is_asked(self):
        now = datetime.datetime(2026, 11, 17, 11, 0, tzinfo=TZ)
        got = self.outcomes([{"owed": True}, {}], now)
        self.assertEqual(got, [("owed", None), ("next-window", win(17, 14, 15)[0])])

    def test_no_list_or_a_list_past_its_horizon_holds_nothing(self):
        now = datetime.datetime(2026, 11, 17, 11, 0, tzinfo=TZ)
        self.assertEqual(st.calendar_outcomes([{}], None, now, 3, 10), [("no-calendar", None)])
        self.assertEqual(self.outcomes([{}], datetime.datetime(2026, 11, 24, tzinfo=TZ)), [("no-calendar", None)])

    def test_a_stretch_shorter_than_the_minimum_is_no_window(self):
        now = datetime.datetime(2026, 11, 17, 16, 0, tzinfo=TZ)            # only the zero-length 18th 09:00 is left
        self.assertEqual(self.outcomes([{}], now), [("next-window", None)])

    def test_the_list_holds_times_only_and_refuses_any_other_line(self):
        good = "2026-11-17T09:00-08:00 2026-11-17T10:00-08:00\nhorizon: 2026-11-23T00:00-08:00\n"
        w, problems = st.parse_windows(good)
        self.assertEqual((problems, len(w.spans)), ([], 1))
        for bad in ("2026-11-17T09:00-08:00 2026-11-17T10:00-08:00 standup\nhorizon: 2026-11-23T00:00-08:00",
                    f"calendar: {CAL_ID}\nhorizon: 2026-11-23T00:00-08:00",
                    "2026-11-17T09:00-08:00 2026-11-17T10:00-08:00",
                    "2026-11-17T10:00-08:00 2026-11-17T09:00-08:00\nhorizon: 2026-11-23T00:00-08:00"):
            with self.subTest(bad=bad):
                self.assertIsNone(st.parse_windows(bad)[0])
        self.assertEqual(st.parse_windows(st.render_windows(w))[0].spans, w.spans)


if __name__ == "__main__":
    unittest.main()
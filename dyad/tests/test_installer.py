"""install.sh (d-work #721, plan revisions 1 and 2): run as `sh install.sh` into scratch directories with a stub
`claude` that records its argv, over a release archive built from this tree. E1: a fresh install through
`dyad install`, the launcher written, the first launch without `--resume` and naming `--remote-control maintain`,
a later launch with it, the last line naming what to attend; E2: `--yes --no-launch` in a checkout that already
holds `dyad/` reinstalls nothing and starts nothing; a second run changes nothing; `DYAD_CLAUDE_FLAGS` replaces
the fixed flags; a clone of a dyad checkout; refusals before any write: a tampered archive, a missing
prerequisite, and no terminal to ask the two prompts; a missing or non-checkout directory, given no clone URL,
is initialized, installed and launched with no further input (d-work #734)."""
import hashlib, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG / "scripts")); import dyadlib, livetest

INSTALLER = PKG / "scripts" / "install.sh"
STUB = '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CLAUDE_LOG"\n[ "$1" = --version ] && echo "stub 0.0.0"\nexit 0\n'
TOP = Path(tempfile.mkdtemp(prefix="dyad-installer-"))
SEED = "This session is the maintenance unit of the dyad system installed here: follow dyad/playbooks/first-boot.md."   # #728
ARCHIVE = TOP / "dyad-test.tar.gz"


def setUpModule():
    r = subprocess.run([sys.executable, str(PKG / "scripts" / "package.py"), "build", str(ARCHIVE)],
                       capture_output=True, text=True, env=dyadlib.git_env())
    if r.returncode:
        raise RuntimeError(f"package.py build: {r.stdout}{r.stderr}")


def tearDownModule():
    shutil.rmtree(TOP, ignore_errors=True)


def git(d, *a):
    r = subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=dyadlib.git_env())
    if r.returncode:
        raise RuntimeError(f"git {' '.join(a)}: {r.stdout}{r.stderr}")
    return r.stdout.strip()


def tree_digest(d: Path) -> dict[str, str]:
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(d.rglob("*")) if p.is_file() and ".git" not in p.relative_to(d).parts}


class Installer(unittest.TestCase):
    def setUp(self):
        self.top = Path(tempfile.mkdtemp(dir=TOP))
        self.bin = self.top / "bin"; self.bin.mkdir()
        (self.bin / "claude").write_text(STUB); (self.bin / "claude").chmod(0o755)
        self.log = self.top / "claude.log"
        self.sha = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
        self.env = {k: v for k, v in dyadlib.git_env().items() if k not in ("DYAD_INSTANCE", "DYAD_SESSION", "DYAD_CLAUDE_FLAGS")}
        self.env.update({"PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}", "CLAUDE_LOG": str(self.log),
                         "DYAD_SESSION": "someone-else"})

    def repo(self, name="target") -> Path:
        d = self.top / name; d.mkdir()
        git(d, "init", "-q")
        for k, v in livetest.NO_AUTO_MAINTENANCE:
            git(d, "config", k, v)
        return d

    def run_installer(self, *a, env=None, **kw):
        return subprocess.run(["/bin/sh", str(INSTALLER), *a], capture_output=True, text=True, env=env or self.env,
                              stdin=subprocess.DEVNULL, start_new_session=True, **kw)

    def install(self, d, *extra):
        return self.run_installer("--yes", "--dir", str(d), "--archive", str(ARCHIVE), "--sha256", self.sha, *extra)

    def launcher(self, d) -> Path:
        gcd = Path(git(d, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        return gcd / "dyad-launch"

    def argv(self):
        return [l for l in self.log.read_text().splitlines() if l != "--version"] if self.log.exists() else []

    def test_e1_fresh_install_then_first_and_later_launch(self):
        d = self.repo()
        r = self.install(d, "--no-launch")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue((d / "dyad" / "VERSION").is_file())
        self.assertIn("| dyad-operator |", (d / "crafts" / "REGISTRY.md").read_text())
        self.assertEqual(git(d, "config", "core.hooksPath"), "dyad/hooks")
        self.assertEqual(self.argv(), [], "no-launch starts nothing")
        launch = self.launcher(d)
        self.assertTrue(os.access(launch, os.X_OK))
        for _ in range(2):
            r = subprocess.run([str(launch)], capture_output=True, text=True, env=self.env)
            self.assertEqual(r.returncode, 0, r.stderr)
        first, later = self.argv()
        self.assertEqual(first, f"--dangerously-skip-permissions --chrome --remote-control maintain {SEED}")   # #728: the seed, last
        self.assertEqual(later.split(), ["--dangerously-skip-permissions", "--resume", "--chrome", "--remote-control", "maintain"])
        self.assertTrue((launch.parent / "dyad-launched").is_file())
        # #747 (fix C2): the launcher names the unit provisionally, so first-boot's `name` step has its function
        self.assertNotIn("unset DYAD_SESSION", launch.read_text())
        self.assertIn("DYAD_SESSION='maintain'\nexport DYAD_SESSION\n", launch.read_text())
        envbin = self.top / "envbin"; envbin.mkdir()
        (envbin / "claude").write_text('#!/bin/sh\nprintf "%s" "$DYAD_SESSION" > "$CLAUDE_LOG.env"\n'); (envbin / "claude").chmod(0o755)
        r = subprocess.run([str(launch)], capture_output=True, text=True,
                           env={**self.env, "PATH": f"{envbin}{os.pathsep}{self.env['PATH']}", "DYAD_SESSION": "someone-else"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(f"{self.log}.env").read_text(), "maintain")   # an inherited name is replaced, never kept

    def test_e1_launch_names_what_to_attend_and_execs_claude(self):
        d = self.repo()
        r = self.install(d, "--rc-name", "maintain-test")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        lines = r.stdout.splitlines()
        self.assertIn("open the app and attend maintain-test", lines)
        self.assertLess(lines.index("open the app and attend maintain-test"),
                        next(i for i, l in enumerate(lines) if l.startswith("launch: claude")))
        self.assertEqual(self.argv(), [f"--dangerously-skip-permissions --chrome --remote-control maintain-test {SEED}"])

    def test_second_run_changes_nothing(self):
        d = self.repo()
        self.assertEqual(self.install(d, "--no-launch").returncode, 0)
        before, launch = tree_digest(d), self.launcher(d).read_bytes()
        r = self.install(d, "--no-launch")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not reinstalled", r.stdout); self.assertIn("unchanged", r.stdout)
        self.assertEqual((tree_digest(d), self.launcher(d).read_bytes()), (before, launch))

    def test_later_launch_carries_no_seed_and_resumes(self):
        """#728: the seed prompt rides the first launch only; a later one resumes and names no play-book."""
        d = self.repo()
        self.assertEqual(self.install(d, "--no-launch").returncode, 0)
        for _ in range(3):
            subprocess.run([str(self.launcher(d))], capture_output=True, env=self.env, check=True)
        first, *later = self.argv()
        self.assertTrue(first.endswith(SEED))
        self.assertEqual(len(later), 2)
        for line in later:
            self.assertIn("--resume", line); self.assertNotIn("first-boot", line)

    def test_attention_clone_is_git_config_and_no_tracked_file(self):
        """#728: `--attention-clone` (or DYAD_ATTENTION_CLONE) writes `dyad.attention.clone` and nothing tracked."""
        for how in ("flag", "env"):
            with self.subTest(how=how):
                d = self.repo(f"target-{how}")
                path = str(self.top / f"central-{how}")
                if how == "flag":
                    r = self.install(d, "--no-launch", "--attention-clone", path)
                else:
                    r = self.run_installer("--yes", "--dir", str(d), "--archive", str(ARCHIVE), "--sha256", self.sha,
                                           "--no-launch", env=dict(self.env, DYAD_ATTENTION_CLONE=path))
                self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
                self.assertEqual(git(d, "config", "dyad.attention.clone"), path)
                self.assertNotIn(path, r.stdout)                                   # the name is never printed
                tracked = git(d, "ls-files", "-z").split("\0") + git(d, "ls-files", "-z", "--others", "--exclude-standard").split("\0")
                self.assertFalse(any(path in (d / f).read_text(errors="replace") for f in tracked if f and (d / f).is_file()))

    def test_e2_existing_checkout_no_launch(self):
        d = self.repo()
        self.assertEqual(self.install(d, "--no-launch").returncode, 0)
        self.launcher(d).unlink()
        r = self.run_installer("--yes", "--no-launch", cwd=d)       # in its working directory, no archive needed
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not reinstalled", r.stdout)
        self.assertTrue(self.launcher(d).is_file())
        self.assertEqual(r.stdout.splitlines()[-1],
                         "install.sh: this session is the maintenance unit, next follow dyad/playbooks/first-boot.md from its step 2 (#728)")
        self.assertEqual(self.argv(), [])

    def test_flags_variable_replaces_the_fixed_flags(self):
        d = self.repo()
        env = dict(self.env, DYAD_CLAUDE_FLAGS="--a --resume --b")
        r = self.run_installer("--yes", "--dir", str(d), "--archive", str(ARCHIVE), "--sha256", self.sha, "--no-launch", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        for _ in range(2):
            subprocess.run([str(self.launcher(d))], capture_output=True, env=self.env, check=True)
        self.assertEqual(self.argv(), [f"--a --b --remote-control maintain {SEED}", "--a --resume --b --remote-control maintain"])

    def test_clone_of_a_dyad_checkout(self):
        src = self.repo("src")
        self.assertEqual(self.install(src, "--no-launch").returncode, 0)
        git(src, "add", "-A"); git(src, "-c", "core.hooksPath=/dev/null", *livetest.IDENTITY, "commit", "-qm", "installed")
        d = self.top / "clone"
        r = self.run_installer("--yes", "--dir", str(d), "--repo", str(src), "--no-launch")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("not reinstalled", r.stdout)
        self.assertTrue(self.launcher(d).is_file())

    def assert_initialized_and_launched(self, d, r):
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn(f"install.sh: initialized {d} as a new git checkout", r.stdout)
        self.assertTrue((d / "dyad" / "VERSION").is_file())
        self.assertEqual(git(d, "config", "core.hooksPath"), "dyad/hooks")
        self.assertNotIn("run: ", r.stdout + r.stderr, "nothing printed reads as a command for the operator to run")
        self.assertEqual(len(self.argv()), 1, "launched with no further input")

    def test_missing_directory_is_created_initialized_and_launched(self):
        d = self.top / "new" / "host"                                 # #734: no mkdir, no git init, Enter at both prompts
        self.assert_initialized_and_launched(d, self.install(d))

    def test_non_checkout_directory_is_initialized_as_it_stands(self):
        d = self.top / "plain"; d.mkdir(); (d / "notes.txt").write_text("kept\n")
        self.assert_initialized_and_launched(d, self.install(d))
        self.assertEqual((d / "notes.txt").read_text(), "kept\n", "nothing in it moved or overwritten")

    def test_tampered_archive_refused_before_any_write(self):
        d = self.repo()
        r = self.run_installer("--yes", "--dir", str(d), "--archive", str(ARCHIVE), "--sha256", "0" * 64, "--no-launch")
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing written", r.stderr)
        self.assertFalse((d / "dyad").exists()); self.assertFalse(self.launcher(d).exists())

    def test_missing_prerequisite_is_named(self):
        only = self.top / "only"; only.mkdir()
        for tool in ("git",):
            os.symlink(shutil.which(tool), only / tool)
        os.symlink(sys.executable, only / "python3")
        r = self.run_installer("--yes", env=dict(self.env, PATH=str(only)))
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing prerequisite(s): claude curl", r.stderr)

    def test_no_terminal_and_no_answers_refused(self):
        d = self.repo()
        r = self.run_installer("--archive", str(ARCHIVE), "--sha256", self.sha, cwd=d)
        self.assertEqual(r.returncode, 2)
        self.assertIn("the directory and clone-or-reuse", r.stderr)
        self.assertFalse((d / "dyad").exists()); self.assertFalse(self.launcher(d).exists())


if __name__ == "__main__":
    unittest.main()

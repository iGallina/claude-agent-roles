"""Generic leak gate: emails, IPs, UUIDs, home paths, phone numbers and token prefixes stay plain regexes.
Owner-specific terms are NOT checked here: the repo ships no term list. The owner runs a private scan before a push."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

from helpers import ROOT, path

sys.path.insert(0, path("scripts"))
import leak_scan  # noqa: E402


class ScannerMechanics(unittest.TestCase):
    """Prove each pattern on a planted sample before trusting its zero on the repo."""

    def test_generic_patterns_are_flagged(self):
        samples = {
            "email": "write to a" + "@" + "b.example",
            "ipv4": "host " + ".".join(["10", "0", "0", "12"]),
            "uuid": "id " + "-".join(["123e4567", "e89b", "12d3", "a456", "426614174000"]),
            "home path": "see /Us" + "ers/someone/file",
            "tilde path": "see ~" + "/work/x",
            "phone": "call +1 555 " + "0100",
            "slack token": "x" + "oxb-123456789012-abcdefghij",
            "api key": "s" + "k-" + "a1b2c3d4e5f6g7h8i9j0",
        }
        for name, text in samples.items():
            with self.subTest(kind=name):
                kinds = {h.kind for h in leak_scan.scan_text(text)}
                self.assertIn(name, kinds, f"{name} not flagged")

    def test_reports_line_numbers(self):
        found = leak_scan.scan_text("ok\nok\ncall me at a" + "@" + "b.example\n")
        self.assertEqual([f.line for f in found], [3])

    def test_clean_text_passes(self):
        self.assertEqual(leak_scan.scan_text("A short, clean sentence about control and zz."), [])

    def test_safe_numbers_are_not_phones(self):
        self.assertEqual(leak_scan.scan_text("Limit: 60 lines, 5 lines, version 1, 2026"), [])


class NoOwnerSpecificGate(unittest.TestCase):
    """H1: the public tree holds no hashed term list and no identity hash."""

    def test_no_hash_file(self):
        self.assertFalse(os.path.exists(path("tests", "forbidden.sha256")))

    def test_scanner_has_no_hash_machinery(self):
        for name in ("ALLOWED_EMAIL_SHA", "ALLOWED_NAME_SHA", "load_hashes", "sha", "HASH_FILE", "commit_problems"):
            self.assertFalse(hasattr(leak_scan, name), name)


class RepoFiles(unittest.TestCase):
    """L5: a fork, or a ZIP download with no .git, runs the same tests."""

    def test_walks_the_folder_when_it_is_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "sub"))
            for rel in ("a.md", os.path.join("sub", "b.md")):
                with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
                    f.write("x\n")
            os.makedirs(os.path.join(tmp, "__pycache__"))
            with open(os.path.join(tmp, "__pycache__", "c.pyc"), "w", encoding="utf-8") as f:
                f.write("x\n")
            self.assertEqual(leak_scan.repo_files(tmp), ["a.md", os.path.join("sub", "b.md")])

    def test_skips_dot_git_when_walking(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".git"))
            with open(os.path.join(tmp, ".git", "x"), "w", encoding="utf-8") as f:
                f.write("x\n")
            self.assertEqual(leak_scan.repo_files(tmp), [])


class NoGitBinary(unittest.TestCase):
    """F6: a machine without git (a slim Python image) runs the scan on a ZIP download."""

    def test_in_git_repo_is_false_when_git_is_missing(self):
        with unittest.mock.patch.dict(os.environ, {"PATH": ""}):
            self.assertFalse(leak_scan._in_git_repo(ROOT))

    def test_repo_files_walks_the_folder_when_git_is_missing(self):
        with unittest.mock.patch.dict(os.environ, {"PATH": ""}):
            files = leak_scan.repo_files(ROOT)
        self.assertIn("README.md", files)
        self.assertFalse([f for f in files if f.startswith(".git" + os.sep)])

    def test_cli_runs_without_git_on_the_path(self):
        # a copy, so ignored local folders of this checkout (a ZIP has none) stay out of the walk
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "scripts"))
            shutil.copy(path("scripts", "leak_scan.py"), os.path.join(tmp, "scripts"))
            shutil.copy(path("README.md"), tmp)
            r = subprocess.run([sys.executable, os.path.join(tmp, "scripts", "leak_scan.py")], capture_output=True,
                               text=True, env=dict(os.environ, PATH=""))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("leak-scan: 0 hits", r.stdout)


class Repo(unittest.TestCase):
    def test_no_hits_in_any_file(self):
        problems = []
        for rel in leak_scan.repo_files(ROOT):
            with open(path(rel), encoding="utf-8", errors="replace") as f:
                text = f.read()
            problems += [f"{rel}:{h.line} {h.kind}" for h in leak_scan.scan_text(text)]
        self.assertEqual(problems, [])

    @unittest.skipUnless(shutil.which("gitleaks"), "gitleaks is not installed")
    def test_gitleaks_files(self):
        r = subprocess.run(["gitleaks", "detect", "--no-git", "--no-banner", "--redact", "-s", ROOT],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(shutil.which("gitleaks") and os.path.isdir(path(".git")), "gitleaks or a git history is missing")
    def test_gitleaks_history(self):
        if subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True).returncode != 0:
            self.skipTest("no commit yet")
        r = subprocess.run(["gitleaks", "detect", "--no-banner", "--redact", "-s", ROOT],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class ScriptExit(unittest.TestCase):
    def test_cli_prints_the_count_and_exits_zero_when_clean(self):
        r = subprocess.run([sys.executable, path("scripts", "leak_scan.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("leak-scan: 0 hits", r.stdout)


if __name__ == "__main__":
    unittest.main()

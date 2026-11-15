import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import ROLES, path, read

sys.path.insert(0, path("scripts"))


class Generator(unittest.TestCase):
    def test_committed_outputs_equal_generator_output(self):
        import build
        expected = build.render_all(path("roles"))
        self.assertEqual(sorted(expected), sorted(
            [os.path.join(".claude", "agents", f"{r}.md") for r in ROLES]
            + [os.path.join("paseo", f"{r}.md") for r in ROLES]
        ))
        for rel, text in expected.items():
            with self.subTest(file=rel):
                self.assertEqual(read(rel), text, f"{rel} is stale: run python3 scripts/build.py")

    def test_generated_files_say_where_they_come_from(self):
        for r in ROLES:
            for rel in (os.path.join(".claude", "agents", f"{r}.md"), os.path.join("paseo", f"{r}.md")):
                self.assertIn(f"roles/{r}.md", read(rel))

    def test_check_mode_exits_zero_when_clean(self):
        import build
        self.assertEqual(build.main(["--check"]), 0)

    def _copy(self, tmp):
        for part in ("roles", "scripts", ".claude", "paseo"):
            shutil.copytree(path(part), os.path.join(tmp, part), ignore=shutil.ignore_patterns("__pycache__"))

    def _check(self, tmp):
        return subprocess.run([sys.executable, os.path.join(tmp, "scripts", "build.py"), "--check"],
                              capture_output=True, text=True)

    def test_check_mode_exits_nonzero_on_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._copy(tmp)
            self.assertEqual(self._check(tmp).returncode, 0)
            target = os.path.join(tmp, "paseo", "researcher.md")
            with open(target, "a", encoding="utf-8") as f:
                f.write("drift\n")
            r = self._check(tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("stale: " + os.path.join("paseo", "researcher.md"), r.stderr)

    def test_check_mode_flags_a_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._copy(tmp)
            target = os.path.join(tmp, "roles", "task-worker.md")
            with open(target, encoding="utf-8") as f:
                text = f.read()
            with open(target, "w", encoding="utf-8") as f:
                f.write(text.replace("thinking: medium", "thinking: high"))
            self.assertEqual(self._check(tmp).returncode, 1)


if __name__ == "__main__":
    unittest.main()

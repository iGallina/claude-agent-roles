import re
import unittest

from helpers import ROLES, read, split

TITLES = ["Chief of Staff", "Account Manager", "Project Manager", "Personal Assistant", "Task Worker", "Researcher"]


class Readme(unittest.TestCase):
    def setUp(self):
        self.text = read("README.md")

    def test_names_all_six_roles(self):
        for title in TITLES:
            with self.subTest(role=title):
                self.assertIn(title, self.text)
        for role in ROLES:
            self.assertIn(role, self.text)

    def test_documents_both_install_paths(self):
        for needle in (".claude/agents", "paseo/", "claude --agent", "decisions/open.md", "decisions/blocked.md", "PROTOCOL.md"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_has_the_chain_a_worked_example_and_a_license_line(self):
        for heading in ("## The chain", "## Install", "## Worked example", "## Test", "## License"):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.text)
        self.assertIn("MIT", self.text)

    def test_cites_the_claude_code_docs_and_credits_the_principles(self):
        self.assertIn("https://code.claude.com/docs/en/sub-agents", self.text)
        self.assertIn("multica-ai/andrej-karpathy-skills", self.text)

    def test_says_anthropic_only_and_lists_the_models(self):
        self.assertIn("Anthropic", self.text)
        for model in ("claude-sonnet-5-5",):
            self.assertIn(model, self.text)

    def test_every_relative_link_exists(self):
        import os
        from helpers import ROOT
        for target in re.findall(r"\]\((?!https?:)([^)#]+)\)", self.text):
            with self.subTest(link=target):
                self.assertTrue(os.path.exists(os.path.join(ROOT, target)), target)


class HelpersDocs(unittest.TestCase):
    """F7: the test parser mirrors no loader that the repo does not ship."""

    def test_no_private_loader_wording_and_no_dead_helper(self):
        text = read("tests", "helpers.py") + read("tests", "test_roles.py")
        self.assertNotIn("Paseo profile loader", text)
        self.assertNotIn("list_value", text)
        self.assertIn("flat `key: value` front matter", read("tests", "helpers.py"))


class License(unittest.TestCase):
    def test_mit(self):
        text = read("LICENSE")
        self.assertIn("MIT License", text)
        self.assertIn("Permission is hereby granted, free of charge", text)


class ProtocolFile(unittest.TestCase):
    def test_every_role_is_in_the_protocol(self):
        text = read("PROTOCOL.md")
        for title in TITLES:
            self.assertIn(title, text)

    def test_templates_exist(self):
        for rel in (("templates", "handoff.md"), ("templates", "decisions", "open.md"), ("templates", "decisions", "blocked.md")):
            self.assertTrue(read(*rel).strip())

    def test_handoff_template_has_the_six_sections(self):
        text = read("templates", "handoff.md")
        for n in range(1, 7):
            self.assertRegex(text, rf"(?m)^## {n}\. ")


class ProtocolFixes(unittest.TestCase):
    def setUp(self):
        self.text = read("PROTOCOL.md")

    def authority_row(self):
        row = [l for l in self.text.splitlines() if l.startswith("| Run tests")][0]
        return [c.strip() for c in row.strip("|").split("|")]

    def test_m2_role_limits_tighten_the_authority_line(self):
        self.assertIn("A role's own Never list and hard limits tighten this line and never loosen it.", self.text)

    def test_m3_open_a_pr_is_a_gate_and_branch_push_stays_green(self):
        green, gate = self.authority_row()
        self.assertNotIn("open a pr", green.lower())
        self.assertIn("open a pr", gate.lower())
        self.assertIn("Push a non-protected branch", green)

    def test_m6_no_invented_paseo_profile_option(self):
        self.assertNotIn("`paseo run` with the profile", self.text)
        self.assertIn("paseo run --provider claude", self.text)

    def test_l2_only_the_chief_of_staff_closes_items(self):
        self.assertNotIn("close it with evidence", self.text)
        self.assertIn("the Chief of Staff closes the item", self.text)

    def test_l3_each_role_archives_what_it_started(self):
        self.assertIn("archives on the starter's word", self.text)
        self.assertNotIn("Archives finished workers", self.text)


class ReadmeFixes(unittest.TestCase):
    def setUp(self):
        self.text = read("README.md")

    def section(self, title):
        m = re.search(rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)", self.text)
        self.assertTrue(m, f"missing section {title}")
        return m.group(1)

    def test_m4_running_the_chain_states_the_operator_relays(self):
        sec = self.section("Running the chain")
        self.assertIn("operator", sec)
        self.assertRegex(sec, r"(?i)one terminal per role")
        rows = [l for l in sec.splitlines() if l.startswith("|") and not set(l) <= set("|- ")]
        self.assertEqual(len(rows), 4)  # header + start, send, archive
        for verb in ("Start", "Send", "Archive"):
            self.assertTrue(any(r.split("|")[1].strip() == verb for r in rows), verb)
        self.assertIn("paseo send", sec)
        self.assertIn("paseo archive", sec)

    def test_m5_commit_or_install_globally(self):
        self.assertRegex(self.text, r"(?is)commit.{0,80}PROTOCOL\.md.{0,80}\.claude/agents/.{0,80}handoffs/")
        self.assertIn("$HOME/.claude/agents/", self.text)
        self.assertRegex(self.text, r"(?i)absolute")

    def test_m6_paseo_install_uses_settings_and_a_real_run_line(self):
        sec = self.section("Install")
        self.assertIn("Settings", sec)
        line = [l for l in sec.splitlines() if "paseo run" in l][0]
        flags = set(re.findall(r"--[a-z-]+", line))
        self.assertTrue(flags and flags <= {"--provider", "--model", "--mode", "--thinking", "--title"}, flags)
        for gone in ("profile loader", "hosts", "split_from", "parent"):
            self.assertNotIn(gone, sec)

    def test_m7_personal_assistant_tools_are_explained(self):
        self.assertIn("mcp__", self.text)
        self.assertRegex(self.text, r"(?i)personal assistant.{0,200}(no `tools`|inherits)")

    def test_l4_diagram_and_do_line(self):
        chain = self.section("The chain")
        lines = chain.split("```")[1].splitlines()
        pa = [l for l in lines if "Personal Assistant" in l][0]
        first = [l for l in lines if "Account Manager" in l][0]
        self.assertLess(pa.index("└─"), first.index("Account Manager"))
        self.assertIn('DO: reply "approve"', self.text)
        self.assertNotIn("in the Project Manager's session", self.text)

    def test_l7_read_only_limit_is_a_prompt_rule(self):
        self.assertRegex(self.text, r"(?i)read-only limit is a prompt rule")

    def test_f3_paseo_example_starts_the_project_manager(self):
        sec = self.section("Install")
        self.assertIn("paseo/project-manager.md", sec)
        self.assertIn("PM · checkout", sec)
        self.assertNotIn("AM · storefront", sec)

    def test_f4_global_install_names_protocol_in_the_handoff_file(self):
        self.assertIn("name the absolute path of `PROTOCOL.md` in the handoff file, under Rules", self.text)

    def test_f5_personal_assistant_no_send_is_a_prompt_rule(self):
        self.assertIn("no-send rule is a prompt rule too", self.text)
        self.assertRegex(self.text, r"(?i)asks before a send tool")

    def test_h1_no_hash_file_claim(self):
        self.assertNotIn("forbidden.sha256", self.text)
        self.assertNotIn("SHA-256", self.text)


RULE = "A role writes the handoff file and names the session to start. The operator starts it, carries each stop line to the parent, and archives on the starter's word."


def flat(text):
    return " ".join(text.split())


class OneRuleInBothFiles(unittest.TestCase):
    """F1: the install copies PROTOCOL.md and never README.md, so both must state the same rule."""

    def test_both_files_carry_the_rule_sentence(self):
        for name in ("README.md", "PROTOCOL.md"):
            with self.subTest(file=name):
                self.assertIn(RULE, flat(read(name)))

    def test_no_file_says_a_role_starts_or_archives_a_session(self):
        for name in ("PROTOCOL.md", "README.md"):
            text = flat(read(name))
            with self.subTest(file=name):
                for stale in ("starts the child", "Each role archives", "starts Project Managers, archives them",
                              "Archives the Project Managers it started", "starts and supervises its Project Managers"):
                    self.assertNotIn(stale, text)

    def test_role_prompts_ask_the_operator(self):
        for role in ("account-manager", "project-manager"):
            with self.subTest(role=role):
                body = flat(read("roles", f"{role}.md"))
                self.assertIn("ask the operator to archive", body.lower())
                self.assertNotRegex(body, r"(?i)\b(start|archive) (one|each|every)\b")


class PaseoStartLine(unittest.TestCase):
    """F2: a role body holds backticks; inside double quotes a shell would run them. The line must read the body
    through $(sed ...), which a shell does not evaluate again."""

    def test_readme_and_protocol_give_the_sed_line(self):
        for name in ("README.md", "PROTOCOL.md"):
            with self.subTest(file=name):
                found = re.search(r"\"\$\(sed '1,/\^<\.-- Generated/d' paseo/[^)\n]+\.md\)\nREAD FIRST: [^\"\n]+\"", read(name))
                self.assertTrue(found, f"{name} lacks the $(sed ...) start line")

    def test_the_start_line_holds_no_bang(self):
        """Interactive bash 3.2 runs history expansion on `!` inside $( ), even between single quotes."""
        for name in ("README.md", "PROTOCOL.md"):
            with self.subTest(file=name):
                m = re.search(r"\"\$\(sed [^\n]*\nREAD FIRST: [^\"\n]+\"", read(name))
                self.assertTrue(m, f"{name} lacks the start line")
                self.assertNotIn("!", m.group(0))

    def test_the_line_passes_a_body_with_backticks_unchanged(self):
        import os
        import shutil
        import subprocess
        import tempfile
        from helpers import ROOT
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, "paseo"))
            for role in ROLES:
                shutil.copy(os.path.join(ROOT, "paseo", f"{role}.md"), os.path.join(tmp, "paseo", f"{role}.md"))
            for role in ROLES:
                with self.subTest(role=role):
                    snippet = ('printf "%s" "$(sed \'1,/^<.-- Generated/d\' paseo/' + role + '.md)\n'
                               'READ FIRST: handoffs/x.md"')
                    out = subprocess.run(["sh", "-c", snippet], cwd=tmp, capture_output=True, text=True)
                    body = read("paseo", f"{role}.md").split("\n\n", 1)[1].strip("\n")
                    self.assertEqual(out.returncode, 0, out.stderr)
                    self.assertEqual(out.stderr, "")
                    self.assertEqual(out.stdout.strip("\n"), body + "\nREAD FIRST: handoffs/x.md")
                    self.assertIn("`", out.stdout)


class ChiefOfStaffStart(unittest.TestCase):
    """A Chief of Staff starts with no handoff file, so a global install must name the protocol path in the start line."""

    def test_readme_gives_the_chief_of_staff_start_line(self):
        self.assertIn('claude --agent chief-of-staff "READ FIRST: <absolute path of PROTOCOL.md>"', read("README.md"))


if __name__ == "__main__":
    unittest.main()

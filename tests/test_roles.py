import os
import unittest

from helpers import ALLOWED_MODELS, CLAUDE_TOOLS, KEBAB, ROLES, THINKING, path, read, split


class SourceRoles(unittest.TestCase):
    def test_six_sources_and_nothing_else(self):
        found = sorted(f[:-3] for f in os.listdir(path("roles")) if f.endswith(".md"))
        self.assertEqual(found, sorted(ROLES))

    def test_source_front_matter(self):
        for role in ROLES:
            fm, body = split(read("roles", f"{role}.md"))
            with self.subTest(role=role):
                for key in ("name", "title", "description", "model", "thinking", "order"):
                    self.assertTrue(fm.get(key), f"{role}: missing {key}")
                self.assertEqual(fm["name"], role)
                self.assertIn(fm["model"], ALLOWED_MODELS)
                self.assertIn(fm["thinking"], THINKING)
                self.assertTrue(fm["order"].isdigit())
                self.assertLessEqual(len(fm["description"]), 400)
                self.assertTrue(body.strip())

    def test_orders_are_unique(self):
        orders = [split(read("roles", f"{r}.md"))[0]["order"] for r in ROLES]
        self.assertEqual(len(set(orders)), len(ROLES))


class ClaudeCodeFormat(unittest.TestCase):
    def test_six_agents_and_nothing_else(self):
        found = sorted(f[:-3] for f in os.listdir(path(".claude", "agents")) if f.endswith(".md"))
        self.assertEqual(found, sorted(ROLES))

    def test_required_fields_and_values(self):
        for role in ROLES:
            fm, body = split(read(".claude", "agents", f"{role}.md"))
            with self.subTest(role=role):
                # docs: only name and description are required; name has no ":" and does not start with "-"
                self.assertEqual(fm["name"], role)
                self.assertRegex(fm["name"], KEBAB)
                self.assertTrue(fm["description"])
                self.assertIn(fm["model"], ALLOWED_MODELS)
                self.assertIn(fm["effort"], THINKING)
                if "tools" in fm:
                    tools = {t.strip() for t in fm["tools"].split(",")}
                    self.assertLessEqual(tools, CLAUDE_TOOLS)
                self.assertTrue(body.strip())

    def test_only_documented_fields(self):
        documented = {"name", "description", "tools", "model", "effort"}
        for role in ROLES:
            fm, _ = split(read(".claude", "agents", f"{role}.md"))
            with self.subTest(role=role):
                self.assertLessEqual(set(fm), documented)

    def test_researcher_tool_list_has_no_edit(self):
        # Write and Bash stay (the report, read commands): the read-only limit is a prompt rule, not a tool limit.
        fm, _ = split(read(".claude", "agents", "researcher.md"))
        self.assertNotIn("Edit", {t.strip() for t in fm["tools"].split(",")})

    def test_personal_assistant_has_no_tools_line_so_mcp_connectors_work(self):
        fm, _ = split(read(".claude", "agents", "personal-assistant.md"))
        self.assertNotIn("tools", fm)


class PaseoFormat(unittest.TestCase):
    KEYS = ("name", "provider", "model", "modeId", "thinkingOptionId", "notes")
    PRIVATE = ("hosts", "order", "version", "parent", "split_from", "split_into", "status")

    def test_six_profiles_and_nothing_else(self):
        found = sorted(f[:-3] for f in os.listdir(path("paseo")) if f.endswith(".md"))
        self.assertEqual(found, sorted(ROLES))

    def test_required_fields_and_values(self):
        for role in ROLES:
            fm, body = split(read("paseo", f"{role}.md"))
            with self.subTest(role=role):
                for key in self.KEYS:
                    self.assertIn(key, fm, f"{role}: missing {key}")
                self.assertEqual(fm["provider"], "claude")
                self.assertIn(fm["model"], ALLOWED_MODELS)
                self.assertEqual(fm["modeId"], "auto")
                self.assertIn(fm["thinkingOptionId"], THINKING)
                for key in self.PRIVATE:
                    self.assertNotIn(key, fm, f"{role}: {key} belongs to a private loader")
                self.assertTrue(fm["name"] and fm["notes"])
                self.assertTrue(body.strip())


class YamlSafety(unittest.TestCase):
    """Claude Code reads real YAML. A plain scalar breaks on ': ' or ' #' and on a leading indicator character."""

    def test_scalars_are_plain_yaml_safe(self):
        for rel in [("roles", f"{r}.md") for r in ROLES] + [(".claude", "agents", f"{r}.md") for r in ROLES] + [("paseo", f"{r}.md") for r in ROLES]:
            fm, _ = split(read(*rel))
            for key, value in fm.items():
                with self.subTest(file="/".join(rel), key=key):
                    self.assertNotIn(": ", value)
                    self.assertNotIn(" #", value)
                    self.assertFalse(value[:1] in "&*!|>'\"%@`{" and value[:1] != "", value)
                    self.assertEqual(value, value.strip())


class BothFormats(unittest.TestCase):
    def test_same_body_in_every_copy(self):
        for role in ROLES:
            src = split(read("roles", f"{role}.md"))[1].strip()
            with self.subTest(role=role):
                self.assertIn(src, split(read(".claude", "agents", f"{role}.md"))[1])
                self.assertIn(src, split(read("paseo", f"{role}.md"))[1])

    def test_same_model_in_every_copy(self):
        for role in ROLES:
            models = {
                split(read("roles", f"{role}.md"))[0]["model"],
                split(read(".claude", "agents", f"{role}.md"))[0]["model"],
                split(read("paseo", f"{role}.md"))[0]["model"],
            }
            with self.subTest(role=role):
                self.assertEqual(len(models), 1)


class FormatsAgree(unittest.TestCase):
    def test_effort_equals_thinking_and_description_equals_notes(self):
        for role in ROLES:
            src = split(read("roles", f"{role}.md"))[0]
            cc = split(read(".claude", "agents", f"{role}.md"))[0]
            pa = split(read("paseo", f"{role}.md"))[0]
            with self.subTest(role=role):
                self.assertEqual(cc["effort"], pa["thinkingOptionId"])
                self.assertEqual(cc["effort"], src["thinking"])
                self.assertEqual(cc["description"], pa["notes"])
                self.assertEqual(cc["description"], src["description"])


class RoleWording(unittest.TestCase):
    def body(self, role):
        return split(read("roles", f"{role}.md"))[1]

    def test_l2_only_the_chief_of_staff_writes_or_closes_decisions(self):
        for role in ("account-manager", "personal-assistant"):
            b = self.body(role)
            with self.subTest(role=role):
                self.assertNotIn("decisions list", b)
                self.assertNotIn("close it with evidence", b)
                self.assertNotIn("Close the item", b)
                self.assertIn("the Chief of Staff closes the item", b)
        self.assertIn("`[decision]`", self.body("personal-assistant"))

    def test_l3_account_manager_archives_project_managers_only(self):
        b = self.body("account-manager")
        self.assertNotIn("finished worker", b)
        self.assertIn("ask the operator to archive its Project Manager", b)
        self.assertIn("Project Manager", split(read("roles", "account-manager.md"))[0]["description"])
        self.assertNotIn("finished workers", split(read("roles", "account-manager.md"))[0]["description"])


class PromptShape(unittest.TestCase):
    def test_each_role_has_done_when_and_points_to_protocol(self):
        for role in ROLES:
            body = split(read("roles", f"{role}.md"))[1]
            with self.subTest(role=role):
                self.assertRegex(body, r"(?m)^## Done when\b")
                self.assertIn("PROTOCOL.md", body)

    def test_no_rule_is_copied_between_roles(self):
        """Single source: a long line may live in one role prompt only."""
        seen = {}
        for role in ROLES:
            for line in split(read("roles", f"{role}.md"))[1].splitlines():
                line = line.strip()
                if len(line) >= 50 and not line.startswith("Follow `PROTOCOL.md` at the project root"):
                    self.assertNotIn(line, seen, f"{role} repeats a line of {seen.get(line)}")
                    seen[line] = role

    def test_sentences_are_short(self):
        import re
        for role in ROLES:
            body = split(read("roles", f"{role}.md"))[1]
            for line in body.splitlines():
                if line.startswith(("#", "|", "```")):
                    continue
                for sentence in re.split(r"(?<=[.!?:;])\s+", line.strip("-* ")):
                    with self.subTest(role=role, sentence=sentence[:40]):
                        self.assertLessEqual(len(sentence.split()), 30)


if __name__ == "__main__":
    unittest.main()

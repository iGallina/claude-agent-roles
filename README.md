# claude-agent-roles

Six agent roles for teams that run on Anthropic models only: **Chief of Staff, Account Manager, Project Manager, Personal Assistant, Task Worker and Researcher**.
Each role is one prompt. Together they form a chain that keeps work moving and brings the owner only the decisions that are theirs.

- Claude only. Model ids: `claude-fable-5-2`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`. No other provider, router or local model.
- Two formats from one source: Claude Code agents in `.claude/agents/`, and optional Paseo agent profiles in `paseo/`.
- The shared rules live once, in [PROTOCOL.md](PROTOCOL.md). A role prompt points there and never repeats a rule.

## The roles

| Role | File name | What it does |
|---|---|---|
| Chief of Staff | `chief-of-staff` | The owner's top session. Keeps the decisions list and the blocked list. Routes work to Account Managers. Never implements. |
| Account Manager | `account-manager` | One per area. Holds the area's context, names the Project Managers to start, asks for their archive when they finish, promotes only what the owner alone can decide. |
| Project Manager | `project-manager` | One per project. Owns the plan, the branches and the reviews. Splits work into Task Workers. Runs the full tests before anything merges. |
| Personal Assistant | `personal-assistant` | An Account Manager for the owner's own inbox. Drafts replies in the owner's voice. Never sends without approval of the exact text. |
| Task Worker | `task-worker` | One bounded task with a done-when. Proves it, stops with one status line, waits to be archived. |
| Researcher | `researcher` | One question, read-only. Answers with sources, proved facts apart from inference, and ranked fixes. Writes only its report. |

## The chain

```
owner → Chief of Staff → Account Manager → Project Manager → Task Worker
              │                                  └────────→ Researcher
              └─ Personal Assistant (an Account Manager for the owner's inbox)
```

- Each role reports only to the role that started it. Only the Chief of Staff speaks to the owner.
- What the owner settles with one word goes to `decisions/open.md`. What the owner must do with their own hands goes to `decisions/blocked.md`. Both files belong to the client; the Chief of Staff is their only writer.
- A brief to a new session is a handoff file of at most 60 lines. The message that starts the session is one line: `READ FIRST: <path>`.
- Merges, deploys, spend, credentials and anything another person reads are gates. They wait for the owner.

Read [PROTOCOL.md](PROTOCOL.md) for the full rules: roles table, handoff file, stop line, decision items, authority line, isolation.

## Running the chain

No role can open, message or archive another session by itself: the formats give a role no such tool. **The operator runs the chain.** The operator opens one terminal per role and carries each stop line to the parent session.

| Step | Claude Code | Paseo |
|---|---|---|
| Start | `claude --agent <role> "READ FIRST: <handoff path>"` in a new terminal | `paseo run …` with the start line under [Paseo agent profiles](#paseo-agent-profiles-optional) |
| Send | Paste the one-line message into the parent's terminal | `paseo send <agent id> "<message>"` |
| Archive | Close the terminal when the parent has reviewed the work | `paseo archive <agent id>` |

A role writes the handoff file and names the session to start. The operator starts it, carries each stop line to the parent, and archives on the starter's word. The stop line is the status line plus the numbered questions.

## Install

Both formats are generated from `roles/<role>.md`. Run the commands from the folder of the project that will use the roles.

### Claude Code agents

```sh
mkdir -p .claude/agents decisions handoffs
cp /path/to/claude-agent-roles/.claude/agents/*.md .claude/agents/
cp /path/to/claude-agent-roles/PROTOCOL.md .
cp /path/to/claude-agent-roles/templates/decisions/*.md decisions/
cp /path/to/claude-agent-roles/templates/handoff.md handoffs/TEMPLATE.md
```

Task Workers run in a worktree, and a worktree holds tracked files only. Commit `PROTOCOL.md`, `.claude/agents/` and `handoffs/` to the project, or the worker will not find them.
Or install the agents in `$HOME/.claude/agents/` for every project on the machine, keep `PROTOCOL.md` somewhere fixed, and name the absolute path of `PROTOCOL.md` in the handoff file, under Rules.

Start a role as its own session:

```sh
claude --agent chief-of-staff
claude --agent project-manager "READ FIRST: handoffs/checkout-tests.md"
```

`--agent <name>` makes the session itself take that agent's system prompt, tools and model. `CLAUDE.md` still loads.
Add `--permission-mode auto` for the roles that run unattended. Task Workers start in the mode you trust for routine edits.
Front matter fields used: `name`, `description`, `tools`, `model`, `effort`. Source: [Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents).

Limits to know:
- The Personal Assistant has no `tools` line, so it inherits every tool, including MCP connectors (mail, chat). A `tools` list removes all MCP tools. If you add one, list each connector as `mcp__<server>__*`.
- The Personal Assistant's no-send rule is a prompt rule too. Run it in a mode that asks before a send tool.
- The Researcher's read-only limit is a prompt rule. Its tool list keeps `Write` (for the report) and `Bash` (for read commands), and only the prompt stops a write. Keep it away from live data.

### Paseo agent profiles (optional)

Public Paseo has no profile folder to copy into. A profile is created in the app and holds no prompt. Per role:

1. In Paseo, open Settings, then your host, then Agents, then Agent profiles, and choose New profile.
2. Take the values from `paseo/<role>.md`: `name` as the profile name, `provider`, `model`, `modeId` (the mode), `thinkingOptionId` (the thinking level), and `notes` as "When to use".
3. Start the role with the prompt body of that file:

```sh
paseo run --provider claude --model claude-sonnet-5-5 --mode auto --thinking high --title "PM · checkout" "$(sed '1,/^<!-- Generated/d' paseo/project-manager.md)
READ FIRST: handoffs/checkout-flaky.md"
```

`paseo run` has no profile flag, so the prompt carries the role. The `$(sed …)` reads the body of `paseo/<role>.md` after the generated-file note. Do not paste the body between the quotes: every body holds backticks, and a shell runs backticked text inside double quotes as a command. Paseo's public docs do not list mode ids; `modeId: auto` is the value these profiles use. List the modes your provider offers with `paseo agent mode <agent id> --list`. Field meanings: [Paseo MCP reference](https://paseo.sh/docs/mcp).

### Change a role

Edit the source in `roles/`, then regenerate both formats:

```sh
python3 scripts/build.py
```

A test fails when a committed file differs from the generator output.

## Worked example

Goal: a flaky checkout test fails one run in ten.

1. **Owner → Chief of Staff.** The owner tells the Chief of Staff: "Fix the flaky checkout test." The Chief of Staff routes it to `AM · storefront`.
2. **Account Manager → Project Manager.** The Account Manager writes `handoffs/checkout-flaky.md` (goal, state, remaining work, commands, rules, report path). The operator starts the Project Manager: `claude --agent project-manager "READ FIRST: handoffs/checkout-flaky.md"`.
3. **Project Manager → Researcher.** The cause is unknown, so the Project Manager writes a handoff file and names `Research: why does checkout_test fail one run in ten?` for the operator to start. The Researcher writes `reports/checkout-flaky.md`: root cause with file and line, three ranked fixes, one recommendation.
4. **Project Manager → Task Worker.** The Project Manager writes the recommended fix into a handoff file for a Task Worker named `Fix the checkout test race`, on its own worktree branch, and the operator starts it. The worker writes the failing test first, fixes the race, runs the checks, and stops:

   ```
   Fixed the race in cart_lock.rb; checkout_test passed 50 runs in a row (output attached), full suite green.
   1. Merge branch fix-checkout-race? Recommend yes, because the full suite is green and the diff is 12 lines.
   ```

5. **Review.** The Project Manager reads the diff, runs the full suite, and tells the operator to archive the worker. Merging to `main` is a gate, so the Project Manager reports it up.
6. **Account Manager → Chief of Staff.** The Account Manager promotes one item:

   ```
   [decision] AM · storefront · Fix the checkout test race · Approve the merge of fix-checkout-race into main
   REC: approve, because the full suite is green and the diff is small
   DO: reply "approve"
   CHECK: git log main --oneline -1 -> contains "Fix the checkout test race"
   DUE: none
   ```

7. **Chief of Staff → owner.** The Chief of Staff writes the item to `decisions/open.md`. The owner answers in one word. The answer travels back down the chain. The Account Manager reports the `CHECK` output, and the Chief of Staff closes the item.

## Test

```sh
python3 -m unittest discover -s tests -v
python3 scripts/leak_scan.py
```

Standard library only. The tests cover: front matter parses; required fields per format; model ids stay in the allowed set; all six roles exist in both formats; `effort` equals `thinkingOptionId` and `description` equals `notes` per role; committed outputs equal the generator output, and `build.py --check` fails on a changed copy; no rule is copied between roles; README and PROTOCOL state the same start-and-archive rule; the Paseo start line passes a body with backticks unchanged; the README names every role and both install paths; the generic leak scan finds nothing.

`scripts/leak_scan.py` is the generic leak gate: emails, IPs, UUIDs, home paths, phone numbers and token prefixes are plain regexes. It walks the folder when there is no `.git`. `gitleaks` runs too when it is installed. The repo ships no list of owner-specific terms. If you fork it for a private team, keep your own term list outside the repo and scan the working tree and `git log -p --all` with it before every push.

## License

[MIT](LICENSE).

The Task Worker's working principles (think before acting, simplest change, surgical edits, verify before done) follow the guidelines in [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills), which distill Andrej Karpathy's observations on common model mistakes when coding.

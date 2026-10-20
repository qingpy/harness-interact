# harness-interact

Lets coding-agent harnesses delegate work to each other in the background. Claude Code can hand a task to Grok, Grok can hand one to Claude Code, and the delegating agent keeps working or stays idle until the harness notifies it that the answer is ready, exactly like a background shell command or subagent.

It is a single skill folder:

- **`SKILL.md`** tells agents to run the script with their harness's background shell. The harness itself then runs it in the background and wakes the agent when it finishes.
- **`harness_interact.py`** runs another harness headless on a task from a prompt file and prints its final answer and session id. Python standard library only.

Supported harnesses: **Claude Code** (`claude`) and **Grok Build** (`grok`). Requires Python 3.10+.

## Install

```sh
git clone https://github.com/qingpy/harness-interact
python harness-interact/skills/harness-interact/harness_interact.py install
```

`install` copies the skill into `~/.claude/skills/` and, when Grok is present, `~/.grok/skills/`. Each copy's `SKILL.md` gets the absolute path of its script, because harness permission checkers refuse commands that expand variables such as `$HOME`. Run it again after updating the clone.

## Usage

Agents use it on their own through the skill: they write the task to a file with their file tool, then run the script in their background shell. By hand:

```sh
python harness-interact/skills/harness-interact/harness_interact.py grok task.md
```

The prompt comes from a file because a plain command line works the same in every shell, passes every permission checker, and keeps the prompt's text exact. Agents write it to the system temp directory, and the script deletes it there after reading, so nothing lands in your workspace. A prompt file anywhere else is left untouched. The output is the agent's final answer followed by `session_id: <id>`. Pass `--session <id>` to continue that conversation. The delegated agent works in the current directory, and its own tool calls and reasoning stay in its harness, out of the caller's context.

## Permissions

A delegated agent follows your own settings for its harness: its default permission mode and its allow and deny rules, exactly as when you run it yourself.

To change that for one task, pass `--mode` (for Claude Code and Grok: `default`, `auto`, `acceptEdits`, `dontAsk`, `plan`, or `bypassPermissions`) and repeatable `--allow` / `--deny` rules in the harness's syntax, such as `Bash(git log *)`. Rules add to your settings, and deny always wins. `--allow` combined with `--mode dontAsk` lets the agent run only the allowed tools. The skill tells agents to set these only when you ask.

## Limits

- **Delegation depth.** A delegated agent can delegate once more. A third level gets an error, which keeps chains from looping.
- **Silent on Windows.** Delegated agents run without opening a console window.

## Adding a harness

Any harness with a headless mode that prints JSON needs one entry in `HARNESSES` in `skills/harness-interact/harness_interact.py`, plus its name in the skill's description. Lists are argument fragments in which `{}` becomes the value:

```python
"grok": {
    "cmd": ["grok", "--output-format", "json"],
    "prompt": ["-p", "{}"],
    "resume": ["--resume", "{}"],
    "mode": ["--permission-mode", "{}"],
    "allow": ["--allowedTools", "{}"],
    "deny": ["--disallowedTools", "{}"],
    "text": "text",
    "session": "sessionId",
},
```

| Field | Meaning |
|---|---|
| `cmd` | Headless command that prints one JSON object or JSON lines |
| `prompt` | Fragment that carries the prompt, or `"stdin"` to send it on standard input |
| `resume`, `mode`, `allow`, `deny` | Optional. Leave out what the harness lacks; the script then rejects that option |
| `text`, `session` | Dotted paths to the answer and the session id in the output, e.g. `"item.text"`. With JSON lines, the last match wins |

## License

MIT

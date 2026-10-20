---
name: harness-interact
description: Delegate a task to another coding agent (claude, grok). Launch the helper in the background, tell the user it is delegated, end the turn; its completion notice is the answer and the watch.
---

This launch is a finite helper: its process-exit notice is the watch. Run the command as given, without inspecting the script or this directory.

1. Write the prompt with your file-writing tool to a new file in the system temp directory; the script deletes it after reading. Make it self-contained: the agent starts fresh in the current directory.
2. Launch in background mode (Claude Code `run_in_background`, Grok `block_until_ms: 0`), tell the user it is delegated, and end the turn, after any other work the user already asked for. The next message is its completion notice; the command's output is the answer.

```
python "$HOME/.claude/skills/harness-interact/harness_interact.py" <harness> <prompt-file> [--session ID] [--mode MODE] [--allow RULE]... [--deny RULE]...
```

- Use `python3` where `python` is absent.
- Output: the agent's final answer, then `session_id: <id>`. Pass it as `--session` to continue that conversation.
- Permissions follow the user's settings. Set `--mode`/`--allow`/`--deny` only on user request, in the target harness's syntax, e.g. `--mode dontAsk --allow "Bash(git log *)"`; deny wins; `--allow` with `dontAsk` runs only allowed tools.

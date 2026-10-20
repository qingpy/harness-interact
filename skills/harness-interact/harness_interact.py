"""Delegate a task to another coding-agent harness and print its answer."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# One entry per harness. Lists are argv fragments in which "{}" becomes the value.
#   cmd        headless command printing JSON (one object or JSON lines)
#   prompt     fragment carrying the prompt, or "stdin" (needed for .cmd shims, which
#              mangle multi-line arguments)
#   resume / mode / allow / deny   optional; leave out what the harness lacks
#   text / session   dotted paths to the answer and the session id in the output
HARNESSES = {
    "claude": {
        "cmd": ["claude", "-p", "--output-format", "json"],
        "prompt": "stdin",
        "resume": ["--resume", "{}"],
        "mode": ["--permission-mode", "{}"],
        "allow": ["--allowedTools", "{}"],
        "deny": ["--disallowedTools", "{}"],
        "text": "result",
        "session": "session_id",
    },
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
}

MAX_DEPTH = 2  # a delegated agent may delegate once more
# Replaced by the installed script's absolute path: permission checkers refuse variable expansion.
SCRIPT_PLACEHOLDER = "$HOME/.claude/skills/harness-interact/harness_interact.py"


def main() -> None:
    if sys.argv[1:] == ["install"]:
        return install()
    parser = argparse.ArgumentParser(prog="harness-interact", description=__doc__)
    parser.add_argument("harness", choices=HARNESSES)
    parser.add_argument("prompt_file", help="file containing the prompt")
    parser.add_argument("--session", help="session id to continue")
    parser.add_argument("--mode", help="permission mode")
    parser.add_argument("--allow", action="append", default=[], help="permission rule to allow (repeatable)")
    parser.add_argument("--deny", action="append", default=[], help="permission rule to deny (repeatable)")
    args = parser.parse_args()

    prompt_file = Path(args.prompt_file).resolve()
    try:
        prompt = prompt_file.read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError as e:
        sys.exit(f"harness-interact: {e}")
    if prompt_file.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        prompt_file.unlink()  # a scratch prompt; files elsewhere belong to the caller
    if not prompt:
        sys.exit("harness-interact: the prompt file is empty.")

    depth = int(os.environ.get("HARNESS_INTERACT_DEPTH", "0"))
    if depth >= MAX_DEPTH:
        sys.exit("harness-interact: delegation depth limit reached; do the task yourself.")
    h = HARNESSES[args.harness]
    exe = shutil.which(h["cmd"][0])
    if not exe:
        sys.exit(f"harness-interact: `{h['cmd'][0]}` is not on PATH.")

    argv = [exe, *h["cmd"][1:]]
    options = {"resume": ("--session", [args.session]), "mode": ("--mode", [args.mode]),
               "allow": ("--allow", args.allow), "deny": ("--deny", args.deny)}
    for key, (flag, values) in options.items():
        for value in filter(None, values):
            if key not in h:
                sys.exit(f"harness-interact: {args.harness} does not support {flag}.")
            argv += _fill(h[key], value)
    stdin = h["prompt"] == "stdin"
    if not stdin:
        argv += _fill(h["prompt"], prompt)

    env = {**os.environ, "HARNESS_INTERACT_DEPTH": str(depth + 1)}
    env.pop("CLAUDECODE", None)  # Claude Code refuses to start inside another Claude Code session
    proc = subprocess.run(
        argv,
        input=(prompt if stdin else "").encode(),
        capture_output=True,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    out = proc.stdout.decode(errors="replace")
    objs = _parse(out)
    text = _find(objs, h["text"])
    if proc.returncode or text is None or any(o.get("is_error") for o in objs):
        detail = (text or proc.stderr.decode(errors="replace") or out).strip()[-2000:]
        sys.exit(f"harness-interact: {args.harness} failed (exit {proc.returncode}): {detail}")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"{text}\n\nsession_id: {_find(objs, h['session'])}")


def install() -> None:
    """Copy this skill into Claude Code's (and Grok's, if present) user skills folder."""
    src = Path(__file__).resolve()
    skill = (src.parent / "SKILL.md").read_text(encoding="utf-8")
    for home in (".claude", ".grok"):
        if home != ".claude" and not (Path.home() / home).is_dir():
            continue
        dst = Path.home() / home / "skills" / "harness-interact"
        dst.mkdir(parents=True, exist_ok=True)
        script = dst / src.name
        if script.resolve() != src:
            shutil.copyfile(src, script)
        (dst / "SKILL.md").write_text(skill.replace(SCRIPT_PLACEHOLDER, script.as_posix()), encoding="utf-8")
        print(f"installed {dst}")


def _fill(fragment: list[str], value: str) -> list[str]:
    return [arg.replace("{}", value) for arg in fragment]


def _parse(out: str) -> list[dict]:
    """Parse one JSON object or JSON lines."""
    try:
        objs = [json.loads(out)]
    except json.JSONDecodeError:
        objs = []
        for line in out.splitlines():
            try:
                objs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return [o for o in objs if isinstance(o, dict)]


def _find(objs: list[dict], path: str):
    """Last non-null value at a dotted path across the objects."""
    found = None
    for value in objs:
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        if value is not None:
            found = value
    return found


if __name__ == "__main__":
    main()

"""Cross-platform hook configuration regressions."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
HOOK_LAUNCHER = REPO_ROOT / "hooks" / "run-python-hook.js"
INSTALL_PS1 = REPO_ROOT / "install.ps1"


def _post_tool_config() -> dict:
    config = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    return config["hooks"]["PostToolUse"][0]


def test_schema_hook_uses_cross_platform_command_and_matcher() -> None:
    post_tool = _post_tool_config()
    handler = post_tool["hooks"][0]
    serialized = json.dumps(handler)

    assert handler["type"] == "command"
    assert handler["command"].startswith("node ")
    assert "${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.js" in handler["command"]
    assert "${CLAUDE_PLUGIN_ROOT}/hooks/validate-schema.py" in handler["command"]
    assert "args" not in handler
    assert "apply_patch" in post_tool["matcher"]
    assert "$FILE_PATH" not in serialized
    assert handler["command"] != "sh"


def test_hook_launcher_documents_python_probe_order() -> None:
    text = HOOK_LAUNCHER.read_text(encoding="utf-8")
    for marker in ("CLAUDE_SEO_PYTHON", "py", "-3", "python3", "python"):
        assert marker in text


def test_hook_launcher_preserves_blocking_exit_code_two(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available in this test environment")

    script = tmp_path / "block.py"
    script.write_text(
        "import sys\n"
        "assert sys.argv[1] == 'payload'\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["CLAUDE_SEO_PYTHON"] = sys.executable

    proc = subprocess.run(
        [node, str(HOOK_LAUNCHER), str(script), "payload"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert proc.returncode == 2


def test_hook_launcher_reads_codex_tool_input_from_stdin(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available in this test environment")

    target = tmp_path / "page.html"
    target.write_text("<html></html>", encoding="utf-8")
    script = tmp_path / "check.py"
    script.write_text(
        "import pathlib, sys\n"
        f"assert pathlib.Path(sys.argv[1]) == pathlib.Path({str(target)!r})\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["CLAUDE_SEO_PYTHON"] = sys.executable

    proc = subprocess.run(
        [node, str(HOOK_LAUNCHER), str(script)],
        input=json.dumps({"tool_input": {"file_path": str(target)}}),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert proc.returncode == 2


def test_windows_installer_prefers_py_launcher_and_rejects_store_stubs() -> None:
    text = INSTALL_PS1.read_text(encoding="utf-8")
    py_pos = text.index("Exe = 'py'; Args = @('-3')")
    python3_pos = text.index("Exe = 'python3'; Args = @()")
    python_pos = text.index("Exe = 'python'; Args = @()")

    assert py_pos < python3_pos < python_pos
    assert "Microsoft Store|WindowsApps|App execution alias|was not found" in text

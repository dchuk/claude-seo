"""Tests for the Claude agent to Codex agent compatibility layer."""

from __future__ import annotations

import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import install_codex_agents as converter  # noqa: E402


class CodexAgentConversionTest(unittest.TestCase):
    def test_all_agents_generate_valid_toml(self) -> None:
        generated = converter.build_all()
        self.assertEqual(18, len(generated))
        for content in generated.values():
            parsed = tomllib.loads(content)
            self.assertIn("name", parsed)
            self.assertIn("description", parsed)
            self.assertIn("developer_instructions", parsed)

    def test_comma_form_tools_and_comments_are_parsed(self) -> None:
        source = ROOT / "agents" / "seo-technical.md"
        header, _ = converter.split_document(source.read_text(encoding="utf-8"))
        metadata = converter.parse_frontmatter(header)
        tools = converter.tool_names(metadata["tools"])
        self.assertIn("Write", tools)
        self.assertNotIn("# Write needed for report/data file output", tools)

    def test_write_agents_receive_workspace_write(self) -> None:
        _, content = converter.build_agent(ROOT / "agents" / "seo-technical.md")
        self.assertEqual("workspace-write", tomllib.loads(content)["sandbox_mode"])

    def test_installer_writes_project_scoped_agents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            written = converter.install(Path(directory))
            self.assertEqual(18, len(written))
            self.assertTrue(all(path.parent.name == "agents" for path in written))


if __name__ == "__main__":
    unittest.main()

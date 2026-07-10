#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");

function stripWrappingQuotes(value) {
  return value.replace(/^["']|["']$/g, "");
}

function pythonCandidates() {
  const candidates = [];
  if (process.env.CLAUDE_SEO_PYTHON) {
    candidates.push({
      label: "CLAUDE_SEO_PYTHON",
      exe: stripWrappingQuotes(process.env.CLAUDE_SEO_PYTHON),
      args: [],
    });
  }
  candidates.push(
    { label: "py -3", exe: "py", args: ["-3"] },
    { label: "python3", exe: "python3", args: [] },
    { label: "python", exe: "python", args: [] },
  );
  return candidates;
}

function isStoreStubOutput(text) {
  return /Microsoft Store|WindowsApps|App execution alias|was not found/i.test(text);
}

function probe(candidate) {
  const script = "import sys; print(sys.executable); print(sys.version.split()[0])";
  const result = spawnSync(candidate.exe, [...candidate.args, "-c", script], {
    encoding: "utf8",
  });
  const output = `${result.stdout || ""}\n${result.stderr || ""}`;
  return result.status === 0 && Boolean((result.stdout || "").trim()) && !isStoreStubOutput(output);
}

function pathsFromHookInput() {
  let payload;
  try {
    const input = fs.readFileSync(0, "utf8").trim();
    payload = input ? JSON.parse(input) : {};
  } catch (_) {
    return [];
  }

  const toolInput = payload.tool_input || payload.toolInput || {};
  const directPath = toolInput.file_path || toolInput.path;
  if (directPath) {
    return [directPath];
  }

  const patch = toolInput.patch || toolInput.input || "";
  const paths = [];
  for (const match of String(patch).matchAll(/^\*\*\* (?:Add|Update) File: (.+)$/gm)) {
    paths.push(match[1].trim());
  }
  return [...new Set(paths)];
}

function main() {
  const [, , hookScript, ...explicitArgs] = process.argv;
  if (!hookScript) {
    process.exit(0);
  }

  const hookArgs = explicitArgs.length ? explicitArgs : pathsFromHookInput();
  if (!hookArgs.length) {
    process.exit(0);
  }

  for (const candidate of pythonCandidates()) {
    if (!probe(candidate)) {
      continue;
    }
    let exitStatus = 0;
    let ran = false;
    for (const hookArg of hookArgs) {
      const result = spawnSync(candidate.exe, [...candidate.args, hookScript, hookArg], {
        stdio: "inherit",
      });
      if (result.error) {
        continue;
      }
      ran = true;
      if (result.status === 2) {
        exitStatus = 2;
      } else if (result.status && exitStatus === 0) {
        exitStatus = result.status;
      }
    }
    if (ran) {
      process.exit(exitStatus);
    }
  }

  console.error(
    "Claude SEO hook could not find Python. Tried CLAUDE_SEO_PYTHON, py -3, python3, python.",
  );
  process.exit(1);
}

main();

# Forgejury

**A lie detector for AI coding agents.**

Your coding agent says *"Done! Created `CHANGELOG.md`, all 5 tests pass."*
Forgejury checks for itself: the file isn't there and only 1 test passed, so
the build **fails**. When several agents build the same thing in parallel, it
also shows you which one behaves differently from the rest.

[![CI](https://github.com/zerochance1907/forgejury/actions/workflows/ci.yml/badge.svg)](https://github.com/zerochance1907/forgejury/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

```
$ forgejury grade examples/SPEC.md examples/build-a examples/build-b examples/build-c
=== Forgejury verdict ===
Summary: 2/3 builds PASS
  FAIL  build-b: claims:files, claims:tests_passed
  DIVERGES  build-c disagrees with the others on 'add-negative'

[build-b] verdict=FAIL
    spec axis:
      file:app.py                  PASS
      file:README.md               PASS
      symbol:app.py::add           PASS
      test_cmd                     PASS
    claims axis:
      files                        FAIL  (claimed but missing: CHANGELOG.md)
      symbols                      PASS
      test_cmd_exit                PASS
      tests_passed                 FAIL  (claimed 5, observed 1)
...
$ echo $?
1
```

> "Exit code 0 is not proof." Agents' self-reports drift from reality all the
> time. Forgejury never reads the agent's prose. It re-observes the build and
> compares that to what was **specified** and what was **claimed**.

## Why

Coding agents (Claude Code, Codex, Cursor, Aider…) end every task with a
confident summary, and usually you have to check it by hand. Forgejury makes
that check mechanical, so it can sit in CI or between agents in a pipeline:

- **Zero dependencies.** Pure Python standard library, a ~700-line package.
- **Deterministic.** No LLM in the loop. Symbols are found with `ast`, not
  grep, and every FAIL names the exact claim it contradicts.
- **CI-friendly.** Exit `0` if every build passes, `1` if any fails, `2` on bad
  input. `--json` gives a stable, machine-readable schema.
- **Built for parallel agents.** Run N agents on one spec and Forgejury
  triangulates them: `3-0` agreement, `2-1` (names the odd one out), or
  `3-way` (no majority).

## How it works

You give it three things:

1. **A spec** (any Markdown file) containing a `## Forgejury Acceptance Block`
   heading followed by a JSON block: the files and symbols that must exist,
   the test command, and behavioral fixtures.
2. **One or more build directories** to judge.
3. Optionally, a **`claims.json`** in each build: what the agent *says* it did.

````markdown
## Forgejury Acceptance Block

```json
{
  "spec_checks": {
    "requires_file": ["app.py", "README.md"],
    "requires_symbol": ["app.py::add"],
    "test_cmd": "python app.py 2 3",
    "runner": "exit-code"
  },
  "consensus": {
    "invoke": "python app.py {input}",
    "fixtures": [
      { "name": "add-small",    "input": "2 3",  "expected": "5" },
      { "name": "add-negative", "input": "-1 4", "expected": "3" }
    ]
  }
}
```
````

```jsonc
// build-b/claims.json: what the agent reported
{ "files": ["app.py", "README.md", "CHANGELOG.md"], "symbols": ["app.py::add"],
  "test_cmd_exit": 0, "tests_passed": 5 }
```

Each build is then graded on three axes:

| Axis | Question | Fails the build? |
|---|---|---|
| **Spec** | Do the required files and symbols exist, and does `test_cmd` exit 0? | Yes |
| **Claims** | Does a fresh observation match the agent's `claims.json`? (files, symbols, exit code, number of tests passed) | Yes (use `--claims-advisory` to only report) |
| **Consensus** | Running each fixture through every build, who disagrees with whom? Does each match the pinned `expected`? | No: it points your attention at a build, it doesn't decide correctness |

Forgejury only ever runs the `test_cmd` and `invoke` commands declared in the
spec, never a command named in an agent's report.

## Install and use

```bash
pip install git+https://github.com/zerochance1907/forgejury
```

```bash
forgejury lint SPEC.md                         # validate the acceptance block before building
forgejury grade SPEC.md build-1 build-2 build-3
forgejury grade SPEC.md build-1 --json         # machine-readable, for pipelines
forgejury grade SPEC.md build-1 --claims-advisory   # report lies without failing
```

`lint` also warns when a pinned `expected` output looks volatile (a date, a
temp path, a memory address, a UUID), so your fixtures don't go flaky.

Try the bundled example from a clone:

```bash
git clone https://github.com/zerochance1907/forgejury && cd forgejury
python -m forgejury grade examples/SPEC.md examples/build-a examples/build-b examples/build-c
```

`build-a` is honest, `build-b` lies in its `claims.json`, and `build-c` is honest
but has a real bug on negative numbers, which the `2-1` consensus split exposes.

### JSON output

```jsonc
{
  "summary": {
    "passed": 2, "total": 3,
    "failed": { "examples/build-b": ["claims:files", "claims:tests_passed"] },
    "diverging": { "add-negative": "examples/build-c" },
    "no_majority": []
  },
  "builds": [
    { "build": "examples/build-a", "verdict": "PASS", "reasons": [],
      "spec_axis": { "file:app.py": "PASS", "...": "..." },
      "claims_axis": { "files": "PASS", "...": "..." } }
  ],
  "consensus": {
    "add-negative": { "label": "2-1", "diverging_build": "examples/build-c",
                      "expected_match": { "...": "PASS|FAIL" },
                      "outputs": { "...": "<canonical stdout>" }, "errors": null }
  }
}
```

The `build` field is always exactly the path string you passed in, so it
round-trips on Windows and POSIX alike.

## What it does not do

Honest limits, by design:

- **The claims axis is a self-delusion detector, not a security boundary.** It
  catches a report that drifted from reality ("12 tests passed" when a fresh
  run sees 9). It won't stop an adversarial agent that runs Forgejury itself
  and tunes `claims.json` to match.
- **Consensus routes attention; it is not a correctness oracle.** In a `2-1`
  split, the two agreeing builds can share the same wrong assumption. Pin
  `expected` on fixtures where you know the right answer.

## Origin

Forgejury was designed and built by
[**Agent Forge**](https://github.com/zerochance1907/agent-forge), an autonomous
team of Claude Code agents that scouts trending AI repos, debates what to
build, builds it three ways in parallel, and reviews the results.

In cycle 1 the agents found `Balanov/verdict` ("exit code 0 is not proof") and
`Balanov/skein` trending, argued for three rounds, and chose this tool. Three
executioner personas built it, and this production-engineer build won 9.25/10.
The reviewer then used Forgejury to grade all three competing builds, and it
caught a real difference between them that the reviewer had missed. The full
debate, spec and review are public in the Agent Forge repo under
`memos/2026-11-04/`.

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q        # 43 tests
```

CI runs the suite on Linux, Windows and macOS with Python 3.10 and 3.13.

## License

[MIT](LICENSE)

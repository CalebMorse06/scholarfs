# Contributing to ScholarFS

ScholarFS is small on purpose. The best contributions make the file standard easier to adopt, inspect, and trust.

## Before opening a change

For a bug, include the command, expected result, actual result, operating system, Python version, and the smallest safe fixture that reproduces it. Remove names, course materials, tokens, grades, and personal schedule data.

For a new field or command, explain:

- which student task it unlocks;
- why existing Markdown or JSON cannot represent it;
- which file owns the canonical value;
- how older workspaces behave;
- what the privacy and rollback story is.

Large features should start as an issue. In particular, discuss schema changes and live connectors before writing them.

## Development setup

Python 3.11 or newer is required.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS or Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the package and optional development checks:

```bash
python -m pip install -e ".[dev]"
```

## Test the complete story

```bash
python -m unittest discover -s tests -v
scholarfs validate examples/fall-2026 --strict
python -m build
```

Then install the built wheel into a clean environment and check the public entry point:

```bash
python -m venv .smoke-venv
.smoke-venv/bin/python -m pip install dist/scholarfs-0.1.0-py3-none-any.whl
.smoke-venv/bin/scholarfs --help
```

On Windows, use `.smoke-venv\Scripts\python.exe` and `.smoke-venv\Scripts\scholarfs.exe`.

## Pull-request checklist

- [ ] The change keeps core offline and avoids adding runtime dependencies without a documented portability need.
- [ ] Mutations are non-destructive by default and use atomic writes where structured data changes.
- [ ] Tests cover happy paths, invalid input, and a failure boundary.
- [ ] Schemas, examples, and reference docs match the implementation.
- [ ] No fixture contains real student information, copyrighted course material, or credentials.
- [ ] `README.md` still gets a newcomer to a visible result quickly.
- [ ] `CHANGELOG.md` records user-visible behavior.

## Style

Prefer standard-library code, explicit types, actionable error messages, and small modules. Avoid abstraction that exists only for a possible future connector or frontend. Format Markdown for readable diffs.

## Commits and releases

Use focused commits with imperative messages. Maintainers release from a clean tag after CI, wheel smoke installation, and example/schema validation pass. PyPI trusted publishing should be configured by the repository owner before enabling the release workflow.

## Conduct

By participating, you agree to follow the [Code of Conduct](./CODE_OF_CONDUCT.md).

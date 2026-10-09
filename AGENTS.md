# Contributing to shopkit

These are the conventions this repository follows. They apply to every contributor.

## Code

- Python 3.12+, fully typed: `mypy src` runs in strict mode and must pass.
- Formatting and lint are `ruff format` and `ruff check` with the settings in `pyproject.toml`.
- Money is always `Decimal`, never `float`. Round explicitly with the helpers in
  `shopkit.money`; do not call `round()` or `quantize()` ad hoc elsewhere.
- Keep the library free of runtime dependencies. Development tools are pinned in
  `requirements-dev.txt`.
- Public functions and classes have docstrings that describe the behaviour, including edge cases
  (rounding, inclusive or exclusive bounds). If you change the behaviour, update the docstring.

## Tests

- Every bug fix comes with a test that fails before the fix and passes after it.
- Every new behaviour is covered by tests in `tests/`, next to the existing tests for that
  module.
- Tests are fast and deterministic: no network, no real clock (pass `today=` explicitly), no
  sleeping.
- Before opening a pull request, run all four checks from the README: `pytest -q`,
  `ruff check . && ruff format --check .`, and `mypy src`.

## Commits and pull requests

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `fix(cart): reject quantities above 999`, `feat(cli): add --json output`,
  `docs: …`, `test: …`, `chore: …`. Use the imperative mood; keep the subject under 72
  characters.
- One logical change per pull request. Reference the issue in the description.
- Add an entry to `CHANGELOG.md` under **Unreleased** for every user-visible change (Added,
  Changed, Fixed or Removed).

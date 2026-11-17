# Contributing

Thanks for your interest in improving `ufs`! Bug reports, docs fixes and pull requests are
all welcome.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) for environments and dependencies.

```bash
git clone https://github.com/spsoni/ufs.git
cd ufs
uv sync --all-groups          # creates .venv with dev and docs dependencies
uv run pre-commit install     # run ruff on every commit
```

## Checks

CI runs all of these, and a pull request needs them to pass:

```bash
uv run pytest                          # tests + coverage (S3 is mocked with moto)
uv run ruff check .                    # lint
uv run ruff format --check .           # formatting
uv run mypy ufs tests                  # strict type checking
uv run mkdocs build --strict           # docs build without warnings
```

Preview the docs locally with `uv run mkdocs serve`.

## Guidelines

- **Keep the backends in step.** A feature on `File`/`Directory` should work on both local
  and S3, and be tested in `tests/test_portable.py`, which runs every test against both.
- **Add tests** for bug fixes and features, and keep coverage where it is.
- **Document user-facing changes** in `docs/` and add an entry under *Unreleased* in
  `CHANGELOG.md`.
- **Public API:** anything exported from `ufs/__init__.py`. Avoid breaking it without a
  good reason, and call breaks out in the changelog.

## Releasing

1. Bump the version (`uv version --bump minor`, or edit `pyproject.toml`), and move the
   *Unreleased* changelog entries under it with today's date.
2. Merge to `main`.
3. Publish a GitHub release tagged `vX.Y.Z`, for example
   `gh release create vX.Y.Z --generate-notes`. The *Release* workflow checks that the tag
   matches the package version, runs the tests, and publishes to PyPI through trusted
   publishing. No token is needed.

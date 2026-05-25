# Contributing to paper-trail

Thanks for your interest. The plugin is in active development; this
guide explains what kind of contributions are most useful right now.

## Scope of v0.1

paper-trail is currently in **v0.1** — feature-complete for the core
workflows (create SOTA, audit SOTA, audit paper, daily registry
maintenance) but with limited real-world validation outside the
author's own use.

The most useful contributions at this stage are:

- **Bug reports** with reproducible steps
- **Documentation improvements** (typos, unclear instructions,
  missing examples)
- **Test fixtures** that exercise edge cases of the state machine,
  cascade, or invariants
- **Adapter implementations** (e.g., Zotero, currently a V2 stub)
- **Sub-agent prompts** that improve the inverted research workflow

Structural changes (new state machine states, new invariants,
new core skills) are less likely to be accepted before v1.0 unless
they address a documented limitation in `CHANGELOG.md` or
`docs/USAGE.md` § Troubleshooting.

## Workflow

1. **Open an issue first** for non-trivial changes — discuss the
   approach before writing code
2. Fork the repository, create a feature branch from `main`
3. Make your changes; preserve the existing code style (read a few
   files to get the feel)
4. Run the local test suite:

   ```bash
   source venv/bin/activate
   python pipeline/tests/test_invariants_synthetic.py   # 19/19 expected
   python pipeline/tests/test_skills_structure.py       # 21/21 expected
   python pipeline/tests/test_idempotence.py
   python pipeline/tests/test_concurrent.py
   python pipeline/tests/test_events.py
   python pipeline/tests/test_f1_negative.py
   python pipeline/tests/assert_coverage.py             # mechanical guard
   ```
5. Open a pull request. CI is not yet automated; tests must pass
   locally and you must summarize the test output in the PR description
6. Update `CHANGELOG.md` under the **Unreleased** section
7. If your change affects user-visible behavior, also update
   `docs/USAGE.md`
8. If your change adds a new component (skill / agent / hook /
   adapter), update the mechanical coverage guard
   (`assert_coverage.py`) and add a proof line in the relevant
   `coverage_run_*.md`

## Code style

- Python: PEP 8, 4 spaces, type hints where useful, docstrings on
  public functions
- Markdown skills/agents/commands: keep frontmatter under 20 lines,
  body sections under 200 lines per file
- Commit messages: imperative mood, Conventional Commits style
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, etc.)
- Co-author trailers: if Claude Code participated in the change,
  add `Co-Authored-By: Claude <noreply@anthropic.com>`

## Shadow libraries (Sci-Hub, Anna's Archive)

Contributions that **enable shadow libraries by default**, **bypass
the disclaimer**, or **add new shadow sources without explicit
opt-in** will not be accepted. See `DISCLAIMER.md` for the
philosophy.

Contributions that improve **traceability** of shadow-library
usage (better logging, audit trail) are welcome.

## License

By contributing, you agree that your contributions are licensed
under the same MIT License as the project (see `LICENSE`).

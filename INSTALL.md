# INSTALL

## Prerequisites

- Python 3.11+
- A vault directory (Obsidian, flat markdown, or Zotero — anywhere you
  want your reference registry and PDFs to live)
- `uv` (recommended) or `pipx` for installing the `paper-search` MCP
  server in an isolated environment
- Optional : `rtfm` CLI (for failure correlation), Calibre (for
  format conversion in the shadow-libs cascade)

## Install the plugin in Claude Code

```
/plugin marketplace add roomi-fields
/plugin install paper-trail
```

(Or for local hacking : `/plugin install file:///path/to/paper-trail`.)

## Install the `paper-search` MCP (required for SOTA writing)

The `sota-writer` skill needs the `paper-search` MCP to query 22
academic platforms in a unified way (OpenAlex, Crossref, Semantic
Scholar, arXiv, PubMed, HAL, CORE, Europe PMC, DBLP, …).

> ⚠️ **Do NOT install `paper-search-mcp` from PyPI.**
> The PyPI release `0.1.3` is severely outdated : it ships only 13 of
> the 63 tools the plugin expects. Critical platforms (OpenAlex,
> Crossref, Semantic Scholar, HAL, CORE, Europe PMC, Unpaywall) are
> missing, and the unified `search_papers` entry point is absent.
> Install from the git HEAD instead.

Recommended install (isolated venv, kept up-to-date with the dépôt) :

```bash
uv venv ~/.local/paper-search-mcp/venv
uv pip install --python ~/.local/paper-search-mcp/venv/bin/python \
    "paper-search-mcp @ git+https://github.com/openags/paper-search-mcp.git"
claude mcp add paper-search --scope user \
    ~/.local/paper-search-mcp/venv/bin/python -m paper_search_mcp.server
```

Then **fully restart Claude Code** : MCP servers are only loaded on
session start. Verify with `claude mcp list` — you should see a
`paper-search` entry.

To upgrade later :

```bash
uv pip install --python ~/.local/paper-search-mcp/venv/bin/python \
    --upgrade "paper-search-mcp @ git+https://github.com/openags/paper-search-mcp.git"
```

## Required configuration

The plugin **refuses to start without `RESEARCH_VAULT_PATH`**. When it
is missing, the first command you run prints a clear error explaining
the three ways to set it (shell, global config file, project `.env`).

## Global config — set secrets once, use everywhere

Putting the same `S2_API_KEY` and `RESEARCH_CONTACT_EMAIL` in every
project's `.env` is painful. The plugin auto-loads
`~/.config/paper-trail/env` (XDG-aware via `XDG_CONFIG_HOME`) at
startup. Variables already defined in the shell environment take
priority — the global file is a default, not an override.

```bash
mkdir -p ~/.config/paper-trail
cat > ~/.config/paper-trail/env <<'EOF'
# Required (can be overridden per-project)
RESEARCH_VAULT_PATH=~/Documents/MyResearch

# Recommended
RESEARCH_CONTACT_EMAIL=you@example.org

# Optional secrets
S2_API_KEY=s2k-...
EOF
chmod 600 ~/.config/paper-trail/env
```

Format : `KEY=VALUE` per line, `#` for comments, quotes optional.

## Per-project overrides

If you need a different vault for one project, set `RESEARCH_VAULT_PATH`
in that project's `.env` and source it before launching Claude Code.

```bash
# Required
export RESEARCH_VAULT_PATH="$HOME/Documents/MyResearch"
```

## Optional configuration

```bash
# Layout adapter (default: obsidian)
export RESEARCH_VAULT_LAYOUT=obsidian   # or 'flat' or 'zotero'

# Override the default sub-paths if your layout differs
export RESEARCH_SOURCES_PATH="$RESEARCH_VAULT_PATH/sources"
export RESEARCH_REGISTRY_PATH="$RESEARCH_SOURCES_PATH/_registry"

# Failure correlation (optional — disabled cleanly if absent)
export RESEARCH_RTFM_DB="$HOME/.rtfm/library.db"

# Contact email injected in Crossref / Semantic Scholar / Unpaywall queries
export RESEARCH_CONTACT_EMAIL="you@example.org"

# Semantic Scholar API key (without it: 100 req / 5 min instead of 1 req/s)
# Get one at https://www.semanticscholar.org/product/api#api-key-form
export S2_API_KEY="s2k-..."

# Shadow libraries (Anna's Archive, Sci-Hub) — strict opt-in
# See DISCLAIMER.md before enabling
export RESEARCH_ENABLE_SHADOW_LIBS=1

# NotebookLM in sota-writer phase A
export RESEARCH_ENABLE_NOTEBOOKLM=1

# Skip the SessionEnd consistency check
export RESEARCH_SKIP_END_DOCTOR=1
```

Put these in `~/.bashrc`, `~/.zshrc`, the global
`~/.config/paper-trail/env`, or a project `.env`.

## Project-specific author whitelist

The Semantic Scholar resolver skips queries containing
group/organization names (treated as anonymous authors). Populate the
list in :

```
~/.config/paper-trail/project_authors.txt
```

One entry per line, `#` for comments. Example :

```
# Project-specific group authors that should not be sent to S2
Anonymous
Group
MyProject
```

The file is **optional**. If absent, the whitelist is empty and every
author name is sent verbatim to S2.

## Optional MCPs (NotebookLM, RTFM)

Beyond `paper-search` (required), two other MCPs are supported :

| MCP | What it adds | Without it |
|---|---|---|
| `NotebookLM` | Books corpus with citations | Skipped — only used when `RESEARCH_ENABLE_NOTEBOOKLM=1` |
| `RTFM` | Local indexed corpus, OCR failure correlation | `RTFM_DB` left unset, ingest skips OCR correlation cleanly |

The built-in REST cascade (Crossref, arXiv, OpenAlex, Unpaywall, HAL,
CORE, archive.org, Semantic Scholar) is **always active**, including
the unauthenticated path when `S2_API_KEY` is absent.

## Verify the install

```bash
python3 -m pipeline preflight
```

Runs without requiring `RESEARCH_VAULT_PATH`. Checks vault, Python
deps, `git`, `paper-search` MCP registration, and warns about missing
optional secrets. Output is actionable : every error / warning prints
the exact command to fix it.

Then the deeper registry check :

```bash
RESEARCH_VAULT_PATH="$HOME/Documents/MyResearch" \
    python3 -m pipeline doctor
```

If it prints a registry health report (even with zero refs), config
is correct. If it raises `ConfigError`, follow the message.

## Test suite

```bash
python3 -m pytest pipeline/tests/ --ignore=pipeline/tests/test_events.py
```

The `conftest.py` at the repo root provides a temporary vault path so
the tests can import `pipeline.config` even without `RESEARCH_VAULT_PATH`
exported.

## Troubleshooting

### `No executables are provided by package …`

Triggered by `uv tool install paper-search-mcp`. The PyPI package does
not declare a console script entrypoint. Use the `venv` recipe above
instead — `python -m paper_search_mcp.server` is the supported
invocation.

### `ModuleNotFoundError: pypdf` when launching the MCP server

Triggered when `paper-search-mcp` was installed with `--no-deps`.
Reinstall **without** `--no-deps` :

```bash
uv pip install --python ~/.local/paper-search-mcp/venv/bin/python \
    --force-reinstall \
    "paper-search-mcp @ git+https://github.com/openags/paper-search-mcp.git"
```

### `TypeError: search_papers() got an unexpected keyword argument 'max_results'`

The unified entry point uses `max_results_per_source`, not
`max_results`. Adjust the call :

```python
mcp__paper-search__search_papers(
    query="…",
    max_results_per_source=10,
    sources=["openalex", "crossref", "semantic", "arxiv"],
)
```

### Only 13 tools listed in `mcp list` instead of 63

You have the PyPI release. Reinstall from git (recipe above).

### `paper-search` doesn't appear in `claude mcp list` after install

You need to restart Claude Code. MCP servers are loaded once, at
session start.

### `ConfigError: RESEARCH_VAULT_PATH n'est pas défini`

Either `RESEARCH_VAULT_PATH` is missing from your shell, or
`~/.config/paper-trail/env` doesn't exist / doesn't contain
`RESEARCH_VAULT_PATH=…`. The error message lists all three options.

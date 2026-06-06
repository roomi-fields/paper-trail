# INSTALL

## Prerequisites

- Python 3.11+
- A vault directory (Obsidian, flat markdown, or Zotero — anywhere you
  want your reference registry and PDFs to live)
- Optional : `rtfm` CLI (for failure correlation), Calibre (for
  format conversion in the shadow-libs cascade)

## Install the plugin in Claude Code

```
/plugin install file:///path/to/paper-trail
```

Or, once published on the marketplace :

```
/plugin marketplace add roomi-fields
/plugin install paper-trail
```

## Required configuration

The plugin **refuses to start without `RESEARCH_VAULT_PATH`**. When it
is missing, the first command you run prints a clear error explaining
what to do — no silent fallback to anyone else's vault.

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

Put these in `~/.bashrc`, `~/.zshrc`, or a project `.env` you source
before launching Claude Code.

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

## Optional MCPs (paper-search, NotebookLM, RTFM)

The plugin uses three MCP servers when available. **All three are optional —
the plugin works without them** by falling back to the built-in REST cascade
(Crossref, arXiv, OpenAlex, Unpaywall, HAL, CORE, archive.org, Semantic
Scholar). The fallback is always active ; the MCPs only add convenience
and additional sources.

| MCP | What it adds | Without it |
|---|---|---|
| `paper-search` | Single unified API across 22 platforms (used in step 1 of `sota-writer`) | The cascade and resolver still hit Crossref / S2 / arXiv / OpenAlex / Unpaywall / HAL / CORE directly via REST |
| `NotebookLM` | Books corpus with citations | Skipped — only used when `RESEARCH_ENABLE_NOTEBOOKLM=1` |
| `RTFM` | Local indexed corpus, OCR failure correlation | `RTFM_DB` left unset, ingest skips OCR correlation cleanly |

If you want the MCPs, configure them in `~/.claude/mcp.json`. The plugin
detects their availability at runtime — no need to advertise their presence
in env vars.

## Verify the install

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

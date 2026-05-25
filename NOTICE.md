# NOTICE — Attributions

The `paper-trail` plugin is distributed under the MIT License (see
`LICENSE`). Some components or patterns are inspired by, or imported
from, third-party projects. This file lists the attributions and
origins.

---

## Components imported from author's other projects

### Worker engine (state machine + cascade + invariants)

Written by Romain Peyrichou. Modules under `pipeline/` and `tools/`.
Provided under the MIT License of this project.

### PDF acquisition helpers (`lib/`)

Originally written for a personal Claude Code plugin
(`source-collector`). Imported here under MIT for self-containment.

Files concerned:

- `lib/oa_finder.py` — Crossref OA URL resolver
- `lib/s2_resolver.py` — Semantic Scholar resolver
- `lib/archive_org_helper.py` — archive.org search and download
- `lib/validate_pdf_content.py` — page 1 anti-homonymy validation
- `lib/download_books.py` — generic PDF download utility
- `lib/shadow/annas_archive.py` — Anna's Archive helper (opt-in,
  see DISCLAIMER.md)
- `lib/shadow/scihub.py` — Sci-Hub helper (opt-in, extracted from
  `pipeline/cascade.py`)

### Writing and audit skills

Originally written for a private academic research project. Generalized
for multi-domain use in paper-trail under the MIT License.

Skills concerned:

- `skills/sota-writer/`
- `skills/sota-auditor/`
- `skills/citation-receipts/`
- `skills/paper-writer/`

Derived agents and tools:

- `agents/researcher.md` (converted skill → sub-agent)
- `tools/notebooklm-integration.md`
- `tools/citation_audit.py` (parameterized by source file path,
  generalization of two domain-specific scripts)

---

## Inspiration patterns (concept only, no code copied)

### `Imbad0202/academic-research-skills` (ARS) v3.9.4

License: CC BY-NC 4.0. Author: Cheng-I Wu
(https://github.com/Imbad0202/academic-research-skills).

**Concepts referenced** (no code copied):

- Research → write → review → revise → finalize pipeline
  architecture
- Audit anchors for claim traceability
- Vault adapter pattern (Obsidian, flat, etc.)

No ARS source file is included in paper-trail. The MIT licensing of
this project is preserved because CC BY-NC 4.0 does not allow
relicensing of derivative code, but inspiration on non-copyrightable
architectural concepts is permitted.

### `Agents365-ai/paper-fetch` v0.5.0

License: MIT. Author: Agents365-ai
(https://github.com/Agents365-ai/paper-fetch).

**Patterns referenced**:

- Stable JSON output format for PDF acquisition
- File naming convention `{first_author}_{year}_{journal}_{title}.pdf`
- Typed exit codes for orchestrator routing

### `JamesWeatherhead/receipts`

License: MIT. Author: James Weatherhead
(https://github.com/JamesWeatherhead/receipts).

**Patterns referenced**:

- Local PDF↔claim audit (read paper + sources, generate per-citation
  verdict)
- `RECEIPTS.md` format with structured verdicts (VALID / ADJUST /
  INVALID + reason + suggested correction)

The `receipts` code is in JavaScript. Our implementation is in Python
(`tools/citation_audit.py` + skill `citation-receipts`), an
independent reimplementation of the pattern.

### `fcakyon/phd-skills` v1.3.0

License: MIT. Author: fcakyon
(https://github.com/fcakyon/phd-skills).

**Patterns referenced**:

- Integrity hooks design (`PostToolUse`, `PreToolUse`, `SessionEnd`)
  for real-time validation of academic artifacts
- Fact-check pattern against bibliographic databases

### `Psypeal/claude-knowledge-vault` v2.4.0

License: MIT. Author: Psypeal
(https://github.com/Psypeal/claude-knowledge-vault).

**Concepts referenced**:

- YAML frontmatter for references (`.vault/raw/<slug>.md`)
- Per-project Sci-Hub opt-in pattern (which we extended to global
  opt-in via environment variable)

---

## External MCPs used (configured by the user, out of scope)

paper-trail interacts with MCP servers that the user configures
independently in `~/.claude/mcp.json` or `<project>/.mcp.json`:

- `paper-search` (multi-platform academic search)
- `notebooklm` (book corpus, optional)
- `rtfm` (local indexing, optional)

These MCPs are not distributed with paper-trail. The plugin documents
their usage but does not formally depend on their presence.

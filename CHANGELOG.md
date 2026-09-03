# Changelog

All notable changes to the `paper-trail` plugin are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-09-03

The plugin queried open-access directories but never made the gesture a human
makes: open the article, spot the file, take it. References available in three
clicks went unacquired. This release adds the routes that a four-month field
deployment had to write alongside the plugin, for want of them inside it.

### Added

- **Five acquisition routes**, cheapest first:
  - `publisher_doi` — follows the DOI to the publisher and reads the
    standard full-text declaration, over two levels. No browser, no opt-in:
    directories do not list everything publishers put online.
  - `publisher_headful` — the same through a real browser, for publishers
    that refuse every programmatic client. Measured: Frontiers yields only
    to this route, PMC already yields to the previous one.
  - `researchgate` — author-deposited full texts, using your own session
    cookies (`RESEARCH_BROWSER_COOKIES`). A record too far from the title is
    refused rather than downloaded and then rejected.
  - `libgen_optin` — a holding distinct from Anna's Archive, with no anti-bot
    challenge and no rationed queue. It succeeds where Anna's queue has
    stopped delivering.
  - `annas_scidb_optin` — Anna's article reader: a door with no rationing,
    tried *before* the slot-based route. It accounts for most of the
    failures observed on that holding.
- **A shared browser session.** One window for the whole pass instead of one
  per reference: the opening cost is no longer paid per ref, and the profile
  persists, so session cookies and a cleared anti-bot challenge survive.
- `--ref` now accepts several slugs. A full pass replays every known failure
  of every waiting reference; acquiring a few new ones took a quarter of an
  hour.

### Changed

- Anna's Archive slot route now tries **up to five candidate fingerprints**.
  A single result was kept, so one bad printing — another edition, a
  namesake, an unreadable scan — condemned the whole reference.
- Run output is line-buffered. Under a scheduled job nothing appeared before
  the pass ended, so there was no way to tell work from a hang.

### Fixed

- **Honorifics taken for surnames** (issue #8). The author check looked for
  the *first word* of the author field: `Maître Eckhart` made it look for
  "Maître", `Anonyme (X)` for "Anonyme". A genuine edition was refused
  twice. All plausible name fragments are now tried, and the file's own
  metadata serve as a last resort.
- **Previews and reviews accepted as the work** (issue #9). A review
  reproduces the author and title on its first page, so it passed every
  identity check. The existing detection was capped at 3,000 characters — a
  thirteen-page review slipped through. Three checks replace that cap, all
  on the head of the text so a bibliography entry does not count, plus a
  page floor for references explicitly declared as books. The page count is
  now recorded in the validation log.
- **An undated citation never matched its own registry entry** (issue #10).
  The registry writes `0000` for an unknown year while the citation yields
  an empty string, so the comparison always failed and every re-ingest
  created another ref (`_2`, `_3`, `_4`). The same file was downloaded
  twice, the manual queue filled with duplicates, and attempt history was
  split across them. Undated citations are now matched on name and title
  alone, at a stricter similarity.

## [0.3.17] — 2026-09-03

Three defects confirmed from a four-month field report on an outside corpus
(316 refs, 273 verified documents, 16 reviews) — the first use of the plugin
outside its author's own vault.

### Fixed

- **An unreadable ref was skipped without a word.** `load_ref` returned
  `None` and `iter_refs` silently dropped the file, so a reference vanished
  from every acquisition pass with nothing to show for it — two full passes
  were lost to this. Parse failures are now named: the pass prints the slug
  and the reason (`invalid YAML: …`, `no frontmatter delimiter`,
  `unterminated frontmatter block`). `load_ref` keeps its contract;
  `load_ref_verbose` and `parse_frontmatter_md_verbose` carry the reason.
- **A Crossref title could produce a filename containing a literal
  newline**, which breaks every command-line tool operating on the vault.
  Crossref returns titles wrapped over several lines and carrying JATS
  markup; the filename sanitizer filtered on "neither word nor whitespace",
  and whitespace includes the newline, so a folded title survived it.
  Titles and venues taken from metadata providers are now stripped of
  markup and collapsed to single spaces before being written, and the
  derived filename is sanitized after that, not before.
- **Ingest wrote the initial ref file without checking it parses.** It is
  the one registry write that does not go through `save_ref`, which always
  re-reads what it just wrote. It now performs the same check and refuses
  rather than leaving an unreadable ref behind. The two remaining bare
  scalars in the template — the source review's path and the PDF path — are
  now quoted, so a colon in a folder or file name no longer corrupts the
  ref.

## [0.3.16] — 2026-08-23

### Fixed

- **The browser route could not start a browser under `pipeline run`**
  (issue #6). `pipeline run` caps the process address space at 1.5 GB, and
  the guard that lifts the cap for the browser was nested *inside*
  `sync_playwright()` instead of around it. The Playwright node driver is
  spawned when that context manager is entered, so it inherited the cap —
  and since Chromium is spawned by the driver, not by Python, lifting the
  cap afterwards changed nothing. The browser died at launch
  (`Connection closed while reading from the driver`) and the reference
  ended up blocked. `pipeline acquire`, which sets no cap, was unaffected.
  The two guards are now in the right order, and a test asserts the cap is
  already lifted at the moment the driver is spawned.
- **`RESEARCH_ANNAS_HEADFUL_BUDGET_S` is now enforced** (issue #7). The
  budget was only consulted between download slots, so the anti-bot
  challenge loop, page loads and mirror searches ran past it — one
  reference was observed wedging a pass for over 11 minutes. Every browser
  wait is now clipped to the remaining budget, and a wall-clock guard cuts
  the attempt ~30 s past it, covering the one Playwright call that accepts
  no timeout (waiting for a download to finish). Callers no longer need an
  external process timeout as a backstop.
- Running out of budget now always leaves the reference **retriable**.
  Two paths previously reported a definitive verdict instead: exhausting
  the budget while looking up the file identifier reported "no source",
  and exhausting it on the last mirror reported the mirrors as tried.

## [0.3.15] — 2026-08-23

### Changed

- **Everything a user reads is now in English.** Pipeline messages, CLI
  help, hook warnings, the exhaustion hints file written next to the
  registry, the WebSearch queue header, and this changelog. The repository
  used to mix an English user-facing documentation with French runtime
  output. Code comments and docstrings stay in French — they are internal.

### Fixed

- The SessionEnd hook looked for a summary line by its French prefix; the
  prefix and the hook now move together, with the coupling covered by the
  rename.

## [0.3.14] — 2026-08-23

Documentation: everything 0.3.13 brought is now described where a user
looks for it, without having to read the source or this changelog.

### Added

- `docs/ACQUISITION_HEADFUL.md`: where to run browser-based acquisition —
  headless container, virtual display, scheduled job — with a container
  recipe, things to watch for, and an environment check.
- `docs/USAGE.md`: the browser route in the extended-sources section (what
  the unavailability message means, how to enable it, the per-reference
  budget); a section on automatic resumption after a transient failure
  (`retry_after`, `transient_retries`, `--retry-exhausted`); a
  troubleshooting entry for "the pipeline reports nothing but skipped
  refs".
- `README.md`: the browser route in the extended-sources table, a pointer
  to the deployment document, and `RESEARCH_ANNAS_HEADFUL_BUDGET_S` in the
  environment-variable table (also in `INSTALL.md`).

### Changed

- **Pipeline messages and CLI help are now in English**, matching the rest
  of the user-facing documentation. Code comments and docstrings stay in
  French — they are internal.

### Fixed

- The browser-route module no longer needs the vault configuration to be
  imported: the documented environment check runs in a bare container,
  before any configuration.
- **The source count was wrong everywhere.** Documentation, skills and
  commands announced "10 sources" — a figure matching neither the default
  cascade (8) nor the full one (11 since the browser route was added).
  Corrected in `README.md`, `docs/MARKETPLACE_ENTRY.md`, both skills and
  both commands concerned.
- The message shown when the browser route is unavailable now says the
  other sources carry on normally, gives the install command and points to
  further reading — it could read as an error.

## [0.3.13] — 2026-08-23

Field reports (7 SOTAs, 95 refs, see issues #1 and #3): the Anna's Archive
cascade stopped returning anything, and 29 perfectly acquirable refs sat
immobilised because transient slot rationing had been treated as definitive
exhaustion.

### Added

- **`annas_headful_optin` cascade source** (`lib/shadow/annas_headful.py`):
  Anna's Archive driven by a windowed Chromium, to be launched under
  `xvfb-run -a`. `cloudscraper` gets a 403 from DDoS-Guard, and a headless
  browser does clear the challenge but the partner file server answers it
  with a 502 — a visible browser gets the PDF. Resolves the MD5 (the
  `annas_md5` field, then `/scidb/<doi>`, then a title+author search with an
  anti-homonymy filter), opens the `slow_download` slots in series, waits
  for the partner link (~20 s) and downloads through a real click. Goes
  through `_save_and_validate` like every other source. Disables itself
  (with a message) when Playwright or the display is missing: no existing
  behaviour changes. Two protocol details integrated: the `/md5/` page only
  exposes its download links with `?&check=1`, and slots are rationed.
- **`pipeline run --retry-exhausted`**: lifts `cascade_exhausted_needs_manual`
  locks before the pass, for automatic resumptions (a slot freed up, a new
  edition, a source added since). `blocked_by` values placed by a human are
  left untouched. The lift happens on the first pass only: in `--loop`,
  repeating it every iteration would replay the full cascade over
  definitively exhausted refs.
- **A per-reference time budget** for the browser route
  (`RESEARCH_ANNAS_HEADFUL_BUDGET_S`, 600 s by default): rationed slots are
  slow to probe, and without a bound a single ref could occupy a pass for
  half an hour.

### Fixed

- **A transient failure no longer places a curator lock.** When every
  attempt in a pass is a temporary unavailability (a mirror rationing its
  slots, an open circuit-breaker, a 502/503, a timeout), the ref simply
  gets a timestamped `retry_after` (back-off from 15 min to 8 h, with a
  `transient_retries` counter cleared on acquisition and on unlocking)
  instead of `blocked_by: cascade_exhausted_needs_manual`. The dispatcher
  picks it up again on its own once that date has passed. As soon as a
  definitive failure appears (404, page 1 rejected, no source, a file
  already refused), the historical behaviour — lock and human arbitration —
  applies. Classification keys on the verdict (a closed vocabulary) before
  the reason (free text), with explicit boundaries so that
  `pdf_too_small [1502B]` is not read as a 502 and a title containing
  "rate" is not read as a rate limit; an unknown verdict counts as
  definitive.
- **`pipeline run`'s memory bound prevented any browser from starting.**
  `run` capped its address space at 1.5 GB while also setting the hard
  limit — hence irreversible, and inherited by child processes: Chromium,
  which reserves tens of GB of virtual address space, died on startup. The
  original hard limit is now preserved, and the bound is lifted only while
  launching the browser.
- **A missing dependency meant every ref "blocked" with no reason.** On an
  interpreter without `bs4`, each ref crashed one after another and the
  summary showed `blocked=N` without the doctor reporting the cause.
  `pipeline run` now checks its dependencies before the first ref, fails
  with an explicit message, and returns a non-zero exit code.
- **Command descriptions were not being read.** The descriptions at the top
  of command files were not quoted: as soon as one contained a colon, the
  file became unparseable and the command disappeared.

### Changed

- `requirements.txt`: the `playwright` line (still optional) documents the
  browser install and launching under `xvfb-run`.
- Neutral framing of the optional extended sources in the public-facing
  pitch.

### Added (documentation)

- `PRIVACY.md`: no telemetry, an honest description of the data flows
  (which requests leave, to which services, carrying what).

## [0.3.12] — 2026-06-13

Field report: final SOTA validation was blocking wrongly, reporting 20
"free-text" citations and 3 wikilinks "missing from the registry" when
everything was in fact correct. Three compounding bugs in the PreToolUse
hooks.

### Fixed

- **False I22 positive when the hook does not inherit `RESEARCH_VAULT_PATH`.**
  The hook loaded the registry through `iter_refs`, silently swallowed any
  exception and concluded "empty registry" → every wikilink in a legitimate
  SOTA was flagged as missing. Hooks now load
  `~/.config/paper-trail/env` themselves at startup, BEFORE importing
  `pipeline.config`. And if the registry stays unreachable, they print a
  clear message and cleanly **disable** the I22/I23 checks instead of
  blocking.
- **The I21 regex accepted `[[slug]]` but not `[[slug|displayed text]]`.**
  The aliased Obsidian wikilink — the idiomatic form for showing
  "Author Year" to the reader while pointing at the slug — was treated as
  missing, so lines that did carry a linked citation were flagged I21.
  Fixed in the `pre_save_sota_check.py` hook and in `pipeline/invariants.py`
  (I20, I21).
- **Explicit diagnosis instead of silent blocking.** Both PreToolUse hooks
  now print a clear message on stderr when the registry is unreachable,
  pointing at the fix (`~/.config/paper-trail/env`).

## [0.3.11] — 2026-06-13

Field report on v0.3.10: 10 refs still missed, including open-access ones
that should have gone through. Four further fixes to the HTTP fetcher and
page 1 validation.

### Added

- **DOI override in page 1 validation.** If the expected DOI appears on
  page 1 (or in the first 6 pages) of the downloaded PDF, the validator
  accepts directly — short-circuiting the title / author / off-domain
  checks that produce false negatives on multilingual theses (French
  title, English body — Rodriguez 2025, Cheveigné…) and on publications
  whose lead author differs from the registry's.

### Changed

- **HTTP fetcher based on `requests` with a browser-like UA.** `_http_get`
  used `urllib` with a generic UA, blocked by many repositories (UMass
  SchoolWorks, KIT, TU Darmstadt). Now: `requests` with a Chrome 124
  User-Agent, Accept-Language, redirects followed, cookies. Falls back to
  `urllib` when `requests` is unavailable (isolated tests).
- **`curl` UA retry on unexpected HTML.** Some servers (JCMS, HAL,
  scientific journals) serve a JS viewer to browsers and the raw PDF to
  command-line downloaders. The pipeline now retries with a minimal
  `curl/7.88.0` UA when the first response (browser UA) is HTML and the
  landing→PDF resolver found nothing. Seen on JCMS, HAL theses, and
  Springer link at times.

### Fixed

- **Compatible with JCMS / HAL theses / OJS galleys.** The curl-UA retry
  combined with the landing→PDF resolver now covers Rodriguez 2025 (HAL
  EN-FR thesis), Vigliensoni 2022 (JCMS galley), and any OJS / DSpace
  server that gates browsers.

## [0.3.10] — 2026-06-13

Field report: an agent reported 13/57 PDFs missed when most were openly
accessible. Diagnosis: the cascade did not follow the HTML landing pages
served by university repositories (HAL, KIT, Darmstadt, NIME,
eScholarship…), and offered no clean way in when the agent already knew
the URL.

### Added

- **Universal landing→PDF resolver.** When a cascade source receives HTML
  instead of a PDF, the pipeline now parses the
  `<meta name="citation_pdf_url">` tag (the Highwire Press convention,
  supported by most academic repositories), falls back to `og:pdf`, then
  to plausible `<a href="...pdf">` links. It follows the link it finds
  with a correct `Referer` header. Massive impact on
  HAL/KIT/Darmstadt/NIME/eScholarship — landing pages previously counted
  as `no_source` now become validated PDFs.
- **`oa_url:` frontmatter field.** Lets you inject a known OA URL (author
  page, university repository, NIME) when the automatic cascade cannot
  find the right PDF. A new `manual_oa_url` source sits at the HEAD of the
  cascade — tried first, and benefits from the landing→PDF resolver.
- **`/paper-trail:inject-url <slug> <url>` command.** Sets `oa_url` in the
  frontmatter, unblocks the ref if it was blocked, and re-runs the
  targeted cascade. Saves an agent from improvising by hand (downloading
  outside the pipeline, dropping the file in directly, losing the metric).
- **Actionable hints on cascade exhaustion.** When the cascade runs out,
  it writes `_hints/<slug>.md` next to the registry listing the two clean
  ways in: inject `oa_url`, or put the PDF locally with `pdf_path`. The
  "what was tried" table shows exactly what failed and why.

### Changed

- **HAL: `/document` fallback.** If the `fileMain_s` returned by the HAL
  API serves HTML, the pipeline retries the canonical URL
  `https://hal.science/<halId>/document`, which forces PDF output. Covers
  the cases where the first URL points at a viewer.

## [0.3.9] — 2026-06-13

Field report from a fresh session: installation friction and the
`paper-search` MCP. Seven UX improvements for a clean start in a new
project.

### Added

- **`pipeline preflight`.** A new subcommand that checks the environment
  before starting a session: vault path, permissions, Python dependencies,
  presence of the `git` binary, registration of the `paper-search` MCP in
  Claude Code, optional variables. Runs **without** `RESEARCH_VAULT_PATH`
  (that is precisely what it diagnoses). Human text or `--json` output.
  Every error/warning prints the exact command to fix it.
- **Global config at `~/.config/paper-trail/env`.** Loaded automatically
  when `pipeline.config` is imported (XDG-aware). Shell/project variables
  keep priority. Lets you set `S2_API_KEY`, `RESEARCH_CONTACT_EMAIL` and
  `RESEARCH_VAULT_PATH` once and have them apply to every project without
  copying them into each `.env`.

### Changed

- **`INSTALL.md` rewritten.** An explicit "Install the `paper-search` MCP"
  section with the exact command (`uv venv` + git URL + `claude mcp add`)
  and a warning against the outdated PyPI build (13 tools instead of 63 on
  git HEAD). A troubleshooting section (No executables,
  ModuleNotFoundError pypdf, TypeError max_results, MCP not listed). A
  section on the global `~/.config/paper-trail/env` config for reusable
  secrets.
- **`README.md`.** MCP table reworked: paper-search marked **Required**,
  with a direct link to the install recipe. Quick start updated with the
  global config and the `pipeline preflight` check command.
- **`sota-writer` skill.** A mandatory preflight step before phase A.
  Correct signatures documented (`max_results_per_source`, not
  `max_results`) to avoid a TypeError on the first call.
- **`/paper-trail:new-sota` command.** Step 0 added: invokes
  `pipeline preflight` before starting sota-writer; halts with a recipe if
  the MCP is not registered.
- **A more useful `ConfigError`.** The message lists all three options
  (shell, `~/.config/paper-trail/env`, project `.env`) instead of the
  shell variable alone.

## [0.3.8] — 2026-06-06

Field reports from a third-party project running the plugin on a flat,
non-Obsidian layout: six bugs fixed (portability, cascade robustness,
page 1 validation, UX).

### Fixed

- **I21 + the pre-save hook: flat-layout compatible.** Free-text citation
  detection recognised only Obsidian `[[slug]]` wikilinks and raised
  wrongly on flat SOTAs (legitimate citations in `[text](refs/slug.md)`
  form). The regex now accepts both.
- **`sota_sync` outside a git repo.** `arbitrate` failed on every call with
  "git backup pre-flight failed" when the vault was not versioned.
  Default: a clean skip with a WARN; strict behaviour is opt-in through
  `RESEARCH_REQUIRE_GIT=1`.
- **`arbitrate reject-pdf` made consistent with I5/I6.** The transition
  moves the record to `needs_reacquisition` after clearing
  `pdf_path`/`pdf_sha256`, but that state was in `STATES_WITH_PDF` → I5/I6
  then raised. Removed from the set: the state means "PDF unusable,
  awaiting re-acquisition", so no active PDF is expected.
- **Sharper page 1 anti-homonymy.** Five reported cases of homonyms
  accepted within the same domain (Dudley 1939 Vocoder vs Morise 2016
  WORLD, Schwarz 2007 vs Einbond 2016…). Adaptive distinctive threshold
  (1 hit for 1-2 words, 2 for 3-4, 3 for 5+); secondary gate at 60 %
  instead of 50 % for titles with ≥5 distinctive words.
- **Book covers.** Roads' *Microsound* was rejected because page 1 is a
  cover with neither author nor keywords. Fallback: read up to 6 pages
  before concluding "author_not_in_page1 and no_domain_keywords".
- **CORE `AttributeError`.** `r.get("fullText", {}).get("url")` broke when
  the API returned `fullText: null`. Replaced with
  `r.get("fullText") or {}`.
- **Anna's Archive `md5_found_but_no_dl`.** Download cascade fleshed out:
  extraction pattern extended (`get/?…` in addition to `get.php?…`),
  granular diagnosis (`dl_unreachable` vs `dl_validation_failed`),
  `annas-archive.org/md5/<md5>` fallback before `library.lol`.

### Changed

- **`pipeline run` (single-pass mode)** now explicitly suggests
  `pipeline run --loop` when at least one transition was made, saving a
  manual re-run to chain the following steps (uid_resolved → pdf_acquired
  → page1_validated).

### Added

- **`INSTALL.md`**: a section listing the optional MCPs (paper-search,
  NotebookLM, RTFM) and clarifying that the plugin works without them,
  through the REST fallback that is already active.

## [0.3.7] — 2026-06-06

Security + portability: every hardcoded path and the API key leaked in the
source removed. The plugin is now usable on any machine once the
environment variables are configured.

### Security

- **Semantic Scholar key removed from the source.** `lib/s2_resolver.py`
  exposed a key in clear text (public commit). It is now read from
  `S2_API_KEY` (env var). **The previous key must be revoked on the
  Semantic Scholar side.**

### Changed (breaking for existing installations)

- **`pipeline/config.py`**: `_DEFAULT_VAULT` removed (the
  `/mnt/d/Obsidian/Articles/Projets/Ontologie musicale` path). If
  `RESEARCH_VAULT_PATH` is not set, the plugin raises `ConfigError` with an
  explicit help message instead of silently falling back to somebody
  else's path.
- **`lib/s2_resolver.py`**: `STATUS_JSON`, `MD_PATH` and `OBSIDIAN_ROOT`
  derived from the configured vault instead of being hardcoded. `EMAIL`
  configurable through `RESEARCH_CONTACT_EMAIL`.
- **`PROJECT_AUTHORS`**: the musicology-specific whitelist moved out to
  `~/.config/paper-trail/project_authors.txt` (empty by default).
- **`RTFM_DB`**: becomes optional (`RESEARCH_RTFM_DB` env var). The
  consuming modules (`rtfm_failures`, `ingest`) handle its absence
  cleanly.
- **`pipeline/tests/test_f1_negative.py`**: test made portable (skips when
  the reference ref does not exist, overridable through
  `RESEARCH_F1_NEGATIVE_REF`).

### Added

- **`conftest.py`** at the root — provides a neutral default
  (`/tmp/paper-trail-test-vault`) for `RESEARCH_VAULT_PATH` during pytest,
  without contaminating a real vault.
- **`INSTALL.md`** — full documentation of the environment variables, the
  optional whitelist file, and the verification procedure.

## [0.2.0] — 2026-05-28

Major rework of the INGEST pipeline: split into 4 orthogonal passes
(identify / purge / acquire / linkify) + chronic SOTA ↔ registry
coherence guarantee. Breaking semantic change in the `citation-parser`
sub-agent contract.

### Added

- **`pipeline/sota_sync.py`** — central utility for propagating slug
  mutations (retract, merge) to all SOTAs in the vault. Replaces the
  silent desynchronization where `cmd_arbitrate retract` or
  `cmd_resolve_textbooks merge_into` mutated the registry without
  updating the wikilinks in SOTAs.

- **Automatic sync hook**: `cmd_arbitrate decision=retract`,
  `cmd_resolve_textbooks action=merge_into`, and
  `cmd_retract_uncited --apply` now trigger `update_wikilinks_in_sotas`
  automatically. Invariants I22/I23 become self-healing for future
  mutations.

- **Test suites**: `pipeline/tests/test_sota_sync.py` (9/9 unit),
  `pipeline/tests/test_p2_sync_branchements.py` (2/2 integration).

### Changed

- **`agents/citation-parser.md` v2** (breaking semantic):
  - Rule 10 (NEW): `raw` must be a strict literal substring of
    `input_text`. Enrichment of `year`/`title` from context is OK
    but `raw` stays the local short mention.
  - Rule 11 (NEW): multiple mentions of the same work produce
    multiple records, NOT one. Replaces the old destructive dedup
    rule 3.last ("return ONE record with the most complete mention").
  - Consequence: table cells like `| Younger 1967 |` now produce a
    record with `raw="Younger 1967"` (instead of being absorbed by the
    full citation), enabling wikilink substitution in tables.

- **`pipeline/ingest.py::ingest_citations`**: added validation that
  `cit.raw` is a literal substring of the SOTA text. Mismatch is logged
  in `IngestResult.errors` (not blocking — Tier 2 anchoring still
  catches via fuzzy match).

### INGEST rework plan — remaining phases

See `plans/compressed-painting-squid.md` for details.

- P4 — `pipeline/purge.py` + `/paper-trail:purge` (clean up invalid
  wikilinks: retracted, `_0000_*` orphans, ugly suffixes `_2_3_4`,
  technical paths `20_ATLAS/`, `.canvas`).
- P5 — `pipeline/identify.py` + `pipeline/linkify.py` + idempotent
  `## Statut des sources` section at the bottom of each SOTA.
- P6 — `pipeline/acquire.py` (targeted cascade wrapper).
- P7 — Auto-fix I22/I23 in `pipeline doctor --fix`.
- P8 — `/paper-trail:registry-cleanup` + global invariance tests.

## [0.1.0] — 2026-05-25

First release. Anti-hallucination Claude Code plugin for academic
research. Research-first workflow, strict state machine, 8-source
acquisition cascade (10 with the opt-in shadow libraries), page 1
anti-homonymy validation, per-citation audit.

### Added

#### Acquisition and validation engine

- **State machine (8 states)**: `candidate`, `uid_resolved`,
  `pdf_acquired`, `awaiting_rtfm_ocr`, `needs_reacquisition`,
  `page1_validated`, `sota_cited_confirmed`, `retracted` (plus
  `blocked_human:*` variants)
- **Acquisition cascade (8 legal sources)**: Crossref OA, arXiv,
  OpenAlex, Unpaywall, HAL, CORE, archive.org, WebSearch queue
- **Two shadow libraries opt-in**: Sci-Hub and Anna's Archive
  activated only via `RESEARCH_ENABLE_SHADOW_LIBS=1` (see
  `DISCLAIMER.md`)
- **Page 1 anti-homonymy validation**: required before accepting any
  downloaded PDF (expected author, title similarity ≥ 0.3, zero
  off-domain keywords)
- **19 mechanical invariants** (I1-I19) with safe auto-fix for
  cosmetic drift (I4, I6, I9, plus I5/I7 semi)
- **WorkerLock** (`fcntl`) to prevent concurrent mutating sessions
- **Per-source circuit breakers** with open-after-N-failures logic
- **Post-write validation** on every registry save (immediate
  rejection if YAML corrupts)
- **JSONL event log** with `pipeline events --since DATE --to STATE`
- **RTFM bridge** for OCR integration and failure correlation

#### Claude Code plugin layer

- **6 skills**: `pdf-cascade`, `registry-doctor`, `sota-writer`,
  `sota-auditor`, `citation-receipts`, `paper-writer`
- **9 slash commands**: `/paper-trail:status`, `:cascade`, `:doctor`,
  `:reactivate-ocr`, `:new-sota`, `:audit-sota`, `:audit-article`,
  `:receipts`, `:new-paper`
- **4 sub-agents**: `cascade-runner`, `page1-validator`, `researcher`,
  `claim-checker`
- **3 hooks**: `PreToolUse` (refuses writing a SOTA citing
  unvalidated references), `PostToolUse` (mini consistency check on
  edited reference), `SessionEnd` (full consistency sweep)
- **3 vault adapters**: `obsidian` (default), `flat`, `zotero` (V2
  stub)
- **5 Python utilities**: `reset_registry.py`, `identify_pdfs.py`,
  `citation_audit.py`, `precheck_sota_wikilinks.py`,
  `reinject_legacy_blocked.py`
- **Mechanical coverage guard** (`assert_coverage.py`) refuses to
  ship a new version without explicit test evidence for each
  component (4 fixes + 19 invariants + 6 skills)
- **Configuration via environment variables**: `RESEARCH_VAULT_PATH`,
  `RESEARCH_SOURCES_PATH`, `RESEARCH_REGISTRY_PATH`,
  `RESEARCH_VAULT_LAYOUT`, `RESEARCH_ENABLE_SHADOW_LIBS`,
  `RESEARCH_ENABLE_NOTEBOOKLM`, `RESEARCH_SKIP_END_DOCTOR`

#### Documentation

- README with quick start and architecture overview
- `docs/USAGE.md` — daily workflows
- `docs/ARCHITECTURE.md` — system diagrams (Mermaid)
- `docs/LEGAL.md` — licensing and attribution detail
- `DISCLAIMER.md` — shadow libraries opt-in policy and jurisdictional
  responsibilities
- `NOTICE.md` — third-party attribution
- `CHANGELOG.md`

### Inspiration patterns (no code copied)

- [`paper-fetch`](https://github.com/Agents365-ai/paper-fetch) (MIT):
  stable JSON output format, file naming convention
- [`receipts`](https://github.com/JamesWeatherhead/receipts) (MIT):
  local PDF↔claim audit pattern, `RECEIPTS.md` format
- [`phd-skills`](https://github.com/fcakyon/phd-skills) (MIT):
  integrity hooks (PreToolUse, PostToolUse, SessionEnd)
- [`claude-knowledge-vault`](https://github.com/Psypeal/claude-knowledge-vault)
  (MIT): YAML frontmatter for Obsidian, Sci-Hub opt-in pattern
- [`academic-research-skills`](https://github.com/Imbad0202/academic-research-skills)
  (CC BY-NC 4.0): research-write-review-revise pipeline architecture
  (**concept only, no code copied**)

See `NOTICE.md` for full attribution.

### Known limitations

- **Zotero adapter**: stub, raises `NotImplementedError`. Planned
  for V0.2.
- **Full ARS-style writing pipeline**: `sota-writer` covers the
  essential research-first workflow but the 10-stage pipeline with
  reviewer/revision/finalize stages is not implemented in V0.1.
- **`paper-search` MCP**: referenced by `sota-writer` and `researcher`
  agent but must be configured by the user in `~/.claude/mcp.json`
  (not bundled with the plugin).
- **WSL2 drvfs**: I/O performance on `/mnt/d/` is noticeably slower
  than native filesystems during large audits.

### Roadmap V0.2

- Full ARS-style writing pipeline (review + revision + finalize)
- Zotero adapter implementation
- Optional bundled `paper-search` MCP alternative
- Enriched RTFM correlation invariants (use `rtfm check --slug -f json`
  for persistent failure flags)
- Automated E2E test suite on representative fixtures

---

[0.4.0]: https://github.com/roomi-fields/paper-trail/releases/tag/v0.4.0
[0.3.17]: https://github.com/roomi-fields/paper-trail/releases/tag/v0.3.17
[0.3.16]: https://github.com/roomi-fields/paper-trail/releases/tag/v0.3.16
[0.3.15]: https://github.com/roomi-fields/paper-trail/releases/tag/v0.3.15
[0.3.14]: https://github.com/roomi-fields/paper-trail/releases/tag/v0.3.14

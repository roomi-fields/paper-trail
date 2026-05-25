# Disclaimer — Shadow Libraries (Anna's Archive, Sci-Hub)

## Default behavior

The `paper-trail` plugin does **not** enable shadow-library sources
(Anna's Archive, Sci-Hub) by default. Its PDF acquisition cascade
stops at legal open-access and institutional sources (Crossref OA,
arXiv, OpenAlex, Unpaywall, HAL, CORE, archive.org), then falls back
to a WebSearch queue (human intervention) if no legal source delivers.

References whose PDF is not accessible via legal sources remain in
state `blocked_human:cascade_exhausted` for human-driven decision.

## Explicit activation (opt-in)

Shadow-library activation is **explicitly** done by the user via an
environment variable:

```bash
export RESEARCH_ENABLE_SHADOW_LIBS=1
```

When activated:

- The cascade appends `scihub_optin` and `annas_archive_optin` as
  sources 9 and 10 (before the WebSearch queue)
- A disclaimer is printed to stderr on the first cascade load of the
  session
- All shadow-library acquisitions are traced in the registry
  (`acquisition_attempts[].via` prefixed with `_optin`)

## User responsibility

The user activating `RESEARCH_ENABLE_SHADOW_LIBS=1` acknowledges the
following:

1. **Jurisdiction-dependent legal status**

   Access to content via Anna's Archive and Sci-Hub may violate
   copyright law in your jurisdiction. In France, the European Union,
   the United States, and most signatories of the Berne Convention,
   downloading copyrighted content without authorization is illegal.

2. **Legal right to access the downloaded material**

   By enabling this option, you confirm that you have the legal
   right to access the downloaded material. This may include,
   depending on jurisdiction and context:

   - **Fair use / fair dealing** (academic citation, research)
   - **Right of citation** (critical analysis)
   - **Institutional access** (you are affiliated with an institution
     holding a license)
   - **Public-domain works**
   - **Works for which you are the author or hold an explicit license**

   Determining the legality of your specific use is your sole
   responsibility and depends on your jurisdictional situation.

3. **No copyrighted content hosted by paper-trail**

   This plugin **does not host any copyrighted content**. It operates
   purely as an HTTP client querying public remote services
   (Sci-Hub mirrors, Anna's Archive API). No PDF is pre-stored or
   distributed through the plugin.

4. **No automatic activation**

   No part of the plugin sets `RESEARCH_ENABLE_SHADOW_LIBS=1`
   automatically. Activation is strictly manual, via explicit
   definition of the variable in your shell or session environment.

## Deactivation

To permanently disable:

- Do not define `RESEARCH_ENABLE_SHADOW_LIBS` in your environment, or
- Explicitly set it to any value other than `1`:
  `export RESEARCH_ENABLE_SHADOW_LIBS=0`

## Special cases

### Strictly academic use

If your activation has a strictly academic purpose (citation,
research, verification of claims in peer-reviewed scientific
publications), you operate under **fair use** (US) or **right of
citation** (France/EU). These exceptions to copyright do **not** cover
redistribution of downloaded content. The plugin never redistributes
acquired content; it stores it locally for personal use only.

### Orphan works, out-of-print, or unavailable

For orphan works (untraceable author), out-of-print, or otherwise
unavailable works, some jurisdictions provide exceptions. Consult
your local laws.

### Works your institution has licensed

If your institution has paid for access (via licensing agreement with
the publisher) but you are working off-VPN, you may have the moral
right to access the content via other means. This is a legal grey
zone; consult your institutional library service.

## Logs and traceability

The plugin traces all shadow-library acquisitions in the registry
(`acquisition_attempts[].via` = `scihub_optin` or
`annas_archive_optin`). This allows distinguishing OA-acquired PDFs
from shadow-acquired PDFs if you ever need to audit.

The `acquisition_attempts` are **never** redistributed; they remain in
your local registry.

## If in doubt

**Do not enable** `RESEARCH_ENABLE_SHADOW_LIBS=1`. The plugin works
perfectly without shadow libraries for OA sources, covering roughly
60-70% of modern academic publications depending on the domain.
For the rest, the `blocked_human:cascade_exhausted` state lets you
decide case-by-case (institutional VPN access, inter-library loan,
direct author contact, etc.).

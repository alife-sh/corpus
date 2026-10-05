# Activity log

Append-only. Collection and ingestion are separate operations.

## [2026-10-04] setup | Initialize the Alife corpus

- Created the raw-paper collection and empty wiki structure.
- Added repository instructions and collection/ingestion conventions.
- Current mode: collect bookmarked files only; ingestion requires an explicit request.
- No papers collected or ingested. No alife.sh documentation imported.

## [2026-10-05] collect | arXiv:2206.01134v2

- Saved the linked HTML and version-specific PDF in
  [raw/papers/2206.01134v2](../raw/papers/2206.01134v2/).
- Recorded the source URLs, version, collection date, and file links in metadata.
- HTML-referenced assets were not downloaded.
- Collection only: no paper contents read, no summary or knowledge pages created,
  and no ingestion performed.

## [2026-10-05] collect | Add HTML figures for arXiv:2206.01134v2

- Downloaded the two original SVG figure assets to the relative paths expected
  by the saved HTML in raw/papers/2206.01134v2/2206.01134v2/.
- Checked local figure references and SVG image dependencies; no missing figure
  dependencies detected. Original HTML and PDF remain unchanged.
- Updated metadata with asset links and the remaining non-figure interface
  limitations. Site styles, scripts, icons, and other interface assets were not
  collected; this is not a fully offline copy of the arXiv site.
- Updated AGENTS.md and README.md to include HTML figures by default for future
  collections.
- Collection only: no ingestion or wiki knowledge pages created.

## [2026-10-05] setup | Add collect-arxiv project skill

- Added .agents/skills/collect-arxiv/SKILL.md and a Python standard-library
  collector for versioned arXiv PDF, HTML, figures, and figure dependencies.
- The collector preserves existing files, records hashes and gaps, and keeps
  collection separate from ingestion. Added offline tests with synthetic fixtures.
- Documented skill usage in README.md and linked it from AGENTS.md.
- No additional papers collected or ingested; existing paper files unchanged.

## [2026-10-05] collect | arXiv:2411.00114v1

- Used the collect-arxiv skill to save the version-specific PDF and HTML in
  [raw/papers/2411.00114v1](../raw/papers/2411.00114v1/).
- Collected 13 original figure assets at the relative paths expected by the HTML.
- Created metadata and a timestamped collection record with URLs, sizes, and
  SHA-256 hashes. Verified all 15 source/asset files and local figure references;
  no missing figure dependencies detected.
- Non-figure site styling, scripts, and interface assets were not collected;
  this is not a fully self-contained offline page.
- Collection only: no paper reading, summaries, or ingestion performed. No
  knowledge pages created. Files not staged or committed.

## [2026-10-05] collect | arXiv:2301.12050v2

- Used the collect-arxiv skill to save the version-specific PDF and HTML in
  [raw/papers/2301.12050v2](../raw/papers/2301.12050v2/).
- Collected 8 original figure assets at the relative paths expected by the HTML.
- Created metadata and a timestamped collection record with URLs, sizes, and
  SHA-256 hashes. Verified all 10 source/asset files and local figure references;
  no missing figure dependencies detected.
- Non-figure site styling, scripts, and interface assets were not collected;
  this is not a fully self-contained offline page.
- Collection only: no paper reading, summaries, or ingestion performed. No
  knowledge pages created. This paper's files were not staged or committed.

## [2026-10-05] collect | arXiv:2302.02662v5

- Used the collect-arxiv skill to save the version-specific PDF and HTML in
  [raw/papers/2302.02662v5](../raw/papers/2302.02662v5/).
- Collected 19 original figure assets at the relative paths expected by the HTML.
- Created metadata and a timestamped collection record with URLs, sizes, and
  SHA-256 hashes. Verified all 21 source/asset files and local figure references;
  no missing figure dependencies detected.
- Non-figure site styling, scripts, and interface assets were not collected;
  this is not a fully self-contained offline page.
- Collection only: no paper reading, summaries, or ingestion performed. No
  knowledge pages created. New files remain unstaged and uncommitted.

## [2026-10-05] collect | arXiv:2305.12487v1

- Used the collect-arxiv skill to save the version-specific PDF and HTML in
  [raw/papers/2305.12487v1](../raw/papers/2305.12487v1/).
- Collected 15 original figure assets at the relative paths expected by the HTML.
- Created metadata and a timestamped collection record with URLs, sizes, and
  SHA-256 hashes. Verified all 17 source/asset files and local figure references;
  no missing figure dependencies detected.
- Non-figure site styling, scripts, and interface assets were not collected;
  this is not a fully self-contained offline page.
- Collection only: no paper reading, summaries, or ingestion performed. No
  knowledge pages created. This collection remains unstaged and uncommitted.

## [2026-10-05] collect | arXiv:2012.09830v7

- Used the collect-arxiv skill to save the version-specific PDF and HTML in
  [raw/papers/2012.09830v7](../raw/papers/2012.09830v7/).
- Collected 4 original figure assets at the relative paths expected by the HTML.
- Created metadata and a timestamped collection record with URLs, sizes, and
  SHA-256 hashes. Verified all 6 source/asset files and local figure references;
  no missing figure dependencies detected.
- Non-figure site styling, scripts, and interface assets were not collected;
  this is not a fully self-contained offline page.
- Collection only: no paper reading, summaries, or ingestion performed. No
  knowledge pages created. This paper's collection files remain unstaged.

## [2026-10-05] collect | arXiv:2507.14172v2

- At the user's request to collect the latest version, resolved the unversioned
  URL via arXiv version links and pinned the collection to v2.
- Used the collect-arxiv skill to save the version-specific PDF and HTML in
  [raw/papers/2507.14172v2](../raw/papers/2507.14172v2/).
- Collected 10 original figure assets at the relative paths expected by the HTML.
- Created metadata and a timestamped collection record with URLs, sizes, and
  SHA-256 hashes. Verified all 12 source/asset files and local figure references;
  no missing figure dependencies detected.
- Non-figure site styling, scripts, and interface assets were not collected;
  this is not a fully self-contained offline page.
- Collection only: no paper reading, summaries, or ingestion performed. No
  knowledge pages created. New collection files were not staged or committed.

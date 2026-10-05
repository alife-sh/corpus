# Alife Corpus

A knowledge base for [Alife](https://alife.sh), built from curated sources using
[Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Structure

```text
AGENTS.md                   Agent conventions and workflows
raw/
  papers/
    <paper-id>/
      paper.pdf             Original paper (or other source format)
      paper.html            HTML snapshot, when available
      <asset-paths>/        Figures at the paths referenced by the HTML
      metadata.md           Optional bibliographic details
      notes.md              Optional human annotations
wiki/
  index.md                  Catalog of wiki pages
  log.md                    Append-only activity history
  sources/                  Paper summaries, created during ingestion
  concepts/                 Knowledge organized by topic
  syntheses/                Comparisons and cross-source analysis
```

The raw collection preserves sources. The wiki holds agent-maintained knowledge
derived from them. `AGENTS.md` defines how to maintain that separation.

## Collect arXiv papers with an agent

The project includes a [collect-arxiv skill](.agents/skills/collect-arxiv/SKILL.md).
Ask an agent to collect a versioned arXiv URL, or invoke it explicitly in Pi:

```text
/skill:collect-arxiv https://arxiv.org/html/2206.01134v2
```

Run `/reload` in Pi after adding the skill, and approve project trust if prompted.
The collector preserves the PDF, HTML, figures, and figure dependencies, and
records file hashes and any gaps. It requires an explicit version, never
overwrites existing source files, and does not ingest the paper.

## Ingest: turn sources into shared understanding

Start by putting original source files in `raw/papers/`. Adding a file only
collects it; **ingestion is the separate, supervised process of understanding
it and integrating that understanding into the wiki.**

Use a stable, readable folder name such as `author-year-short-title` or an arXiv
identifier. Keep each paper's supplementary files together in the same folder.
Preserve distinct versions rather than overwriting an earlier one.

For HTML papers, **collect the referenced figures by default**, in their original
formats, including any dependencies needed to display them. Keep their relative
paths so they load from the saved HTML without changing the original source.
Keep the version-specific PDF alongside it when available. Record any missing
assets or remaining network dependencies in metadata; local figures do not
necessarily make the site's styling and interface work offline. Collecting
these assets is not ingestion.

Metadata is optional. If the bookmark already includes useful
details, save them in `metadata.md`:

```markdown
# Paper title

- Authors:
- Year:
- DOI / arXiv:
- Source URL:
- Version:
- Collected:
```

Record only known details; missing metadata should not delay collection. Human
annotations can live in `notes.md`, clearly separate from the paper itself.
If you only have a URL, record it in metadata; it remains a bookmark until the
source file is collected.

When you are ready to ingest, sit down with an agent and work through one source
at a time in small, manageable chunks—for example, a section, an argument, or an
experiment. Read closely, discuss the claims and evidence, question the agent's
interpretation, and check the cited passages. Include relevant figures and
supplements, not just the abstract or conclusions.

**Do not hand a large source or a batch of papers to an agent and leave it to
process them unsupervised.** Your job is to guide the reading, decide what
matters, and review the understanding being recorded. The agent handles the
writing, cross-references, and bookkeeping.

As you work, the agent creates a cited source summary and updates relevant
concept and synthesis pages, noting limitations, uncertainties, and conflicts
with other sources. It also updates `wiki/index.md` and appends an entry to
`wiki/log.md`. Review those changes before moving on. If you stop partway
through a source, make sure the pages state what has and has not been covered.

The result is not just a paper summary: it is knowledge connected to the rest
of the corpus, ready to build on.

## Query: explore the accumulated knowledge

Once sources have been ingested and wiki pages exist, ask the agent questions
against the wiki. It starts with the index, reads the relevant pages, and
synthesizes an answer with citations. For example:

- How do these papers define intrinsic motivation, and where do they disagree?
- What evidence supports this mechanism, and what are its limitations?
- Which findings could inform Alife, and which connections are only hypotheses?

The wiki's value is that the summaries, connections, and disagreements persist;
you do not have to reconstruct them from raw papers for every question. Ask the
agent to distinguish established findings from interpretation and to identify
where the corpus lacks evidence.

Useful answers should not disappear into chat history. Have the agent save
substantial comparisons, analyses, and new connections as wiki pages, with
supporting citations, and update the index and log. Review these additions just
as you would during ingestion.

## Maintain: keep the wiki coherent

Periodically ask the agent to health-check (or “lint”) the wiki. Look for:

- Contradictions between pages and stale claims superseded by newer evidence
- Unsupported claims, missing citations, and broken links
- Orphan pages, missing cross-references, and important concepts without pages
- Gaps in coverage that suggest useful questions or additional sources

Review the findings together, decide what needs fixing, and have the agent
update the affected pages, index, and log. Keep disagreements and uncertainties
visible rather than forcing a tidy consensus. Suggestions for new sources are
leads for you to curate—not permission for unattended ingestion.

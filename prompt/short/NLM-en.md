# Short prompt for NotebookLM — English

## Full short version (for the Deep Research field)

```text
Research object: {{FIGURE or TOPIC}}. Primary sources — zhyrau poetry, küi legends, oral tradition.

Your role is source critic. Neither eulogist nor debunker: weigh evidential force.

Source weight: I contemporary testimony > II oral tradition (later zhyrs, shezhire genealogy, epic) > III archival document > IV academic work that cites its sources > V internet. Wikipedia is not evidence; it is the thing being checked.

Tag every claim: A corroborated (text and an independent source agree), B text only, C internet only (no reference), D disputed, E refuted.

Procedure: 1) extract the checkable claims from the text — names, clan, patronymic, nickname, numbers, years, place names, events, kinship, discipleship; leave poetic similes out. 2) test each in Kazakh, Russian and English. 3) build a register: line of text (quoted) → external source → level.

Mandatory checks: anachronism — does the text mention anything that did not exist in the author's lifetime; internal chronology — do the stated ages, years and event order cohere; two-witness rule — if two independent texts agree, the level is A; when a printed title contradicts the content, the content wins.

Prohibitions: do not fill gaps with conjecture, write "unknown"; do not smooth over contradictions, put both sides side by side; do not alter quotations; do not idealize the figure — report the criticism the primary source makes; do not invent source titles.

Output: 1) verification register (claim / quotation / external source / level); 2) a passport table with a level on every row; 3) list of contradictions; 4) list of what was not found; 5) bibliography.
```

## Compact version (if the field is very small)

```text
Research {{FIGURE}} as a source critic. Source weight: contemporary testimony > oral tradition > archive > academic work > internet (Wikipedia is not evidence, it is what gets checked). Tag every claim: A corroborated, B text only, C internet only, D disputed, E refuted. Run these checks: anachronism, internal chronology, two independent witnesses. Do not fill gaps with conjecture — write "unknown"; do not smooth over contradictions; do not idealize the figure. Output: a table of claim / quotation / external source / level, plus lists of contradictions and of what was not found.
```

---
name: book-project-guide
description: Use when adding a Nanocode book chapter or onboarding.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [book, teaching, markdown, chapters, onboarding, nanocode]
    related_skills: [make-book, markdown-book-two-pane, code-explanation, repo-docs-maintenance]
---

# book-project-guide: the Nanocode book, chapter by chapter

## When to Use

Load this when you are:

- adding, rewriting or reordering a chapter of the Nanocode book in this repo;
- a new agent starting on the repo with no context (read "Start here" first);
- rebuilding `EXPLAINER.md`, `book.html` or `book.pdf`;
- auditing that every chapter is registered in the build and test files.

It encodes the house rules worked out over chapters 1-15: what is generated vs.
hand-written, what a chapter folder is, what the prose must contain, and every
root file that must learn about a new chapter.

## Start here (fresh agent, no context)

Repo: the educational refactor of *Build Your Own Coding Agent*. It is the same
agent as the book, split into small modules, with a Rich terminal UI and an
OpenRouter-first brain. `ch01/` … `ch15/` are each a **complete runnable
snapshot** at the end of that chapter, not a diff. The book about them is
`EXPLAINER.md`, generated from `chNN/EXPLAINER_chNN.md`.

Read in this order:

1. `README.md` — what the repo is, how to run it, what each chapter adds.
2. `REFACTOR.md` — the module map and the deliberate deviations from the book.
3. `EXPLAINER.md` — front matter (chapter shape, conventions), then chapter 1.
4. `ch15/` — the newest, largest snapshot; read `nanocode.py` and `tools.py`.
5. `build_explainer.py` — the only place chapter order lives.

Commands that must work before you change anything:

```bash
uv sync
uv run pytest -q                    # 384 passed in ~7s, no API key needed
uv run ch12/nanocode.py --act       # needs .env (see below)
uv run python build_explainer.py
uv run python build_book.py --pdf   # book.html + book.pdf
```

`.env` in the repo root holds `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`,
`NANOCODE_BRAIN`. Never print, commit or rewrite it. Chapters 1-2 need no key;
every test runs offline against a `FakeBrain`.

## The repo on one screen

```
chNN/                     one complete snapshot per chapter
  nanocode.py             Memory, Agent (the loop), main()   <- policy
  llm.py                  Brain, Thought, one class per provider
  tools.py                Tool classes, execute(context, **args) -> str
  ui.py / ui.json         everything printed; colours live in JSON
  hooks.py                lifecycle events + JSONL trace
  sounds.py (ch13+)       hooks -> Windows sounds
  sandbox.py (ch14+)      where ACT mode may write
  workflows.py (ch15+)    fan_out, pipeline, map_reduce, critic_loop
  test_nanocode.py        the book's tests + the chapter's new ones
  nanocode_copy.py        the book's ORIGINAL single file, for diffing
  EXPLAINER_chNN.md       the chapter as prose
  README.md (ch12+)       file map, what changed, how to run
EXPLAINER.md              generated combined book
book.html, book.pdf       generated outputs, both tracked in git
build_explainer.py        chapter markdown -> EXPLAINER.md (chapter order here)
build_book.py             Markdown -> two-pane book.html (+ --pdf)
build_pdf.py              Chrome print + PDF outline + page numbers
conftest.py               private import root per chapter for one pytest run
run_all_tests.py          one pytest process per chapter (isolation view)
pyproject.toml            deps + testpaths
book_theme.toml           every colour, font and size in book.html
```

The dependency arrows point one way: `ui.py` knows nothing about LLMs or tools;
`llm.py` knows nothing about tools; `tools.py` knows nothing about the agent.

## Invariants (breaking one of these silently damages the book)

1. **Generated files are never hand-edited.** `EXPLAINER.md`, `book.html` and
   `book.pdf` come out of the scripts. Front matter lives in `HEADER` inside
   `build_explainer.py`; editing `EXPLAINER.md` loses the change on the next
   build.
2. **`nanocode_copy.py` is never modified.** It is the book's original file and
   the diff reference for readers.
3. **One chapter, one new idea.** If the title needs "and", split it.
4. **A chapter starts as a copy of the previous one.** Only files the new idea
   genuinely touches may change; everything else stays byte-identical so a
   reader can diff `ch14` against `ch15` and see the lesson.
5. **Earlier chapters' tests are never adapted.** They must pass unmodified;
   new behaviour gets new tests, appended to the copied `test_nanocode.py`.
   Tests use `FakeBrain`/temp dirs — no network, no API key.
6. **Prose matches the code.** Every claim names a real file and function, and
   traces are real output, not invented. If the code changed, the chapter and
   its README change in the same commit.
7. **No new dependencies** unless unavoidable. This project is stdlib +
   `requests`, `rich`, `python-dotenv`, `ddgs`, `pytest`.
8. **`ui.py` and `ui.json` stay shared.** They are identical in every chapter
   except where presentation is the lesson (ch14 adds `forbidden()` and
   `sandbox_scope()`, ch15 adds `scope()` and per-subagent labels). `hooks.py`
   only ever gains events.
9. **uv only.** Never `pip install`, never activate `.venv` by hand.

## Adding a chapter

### Step 1 — decide the idea and the number

New chapters after 15 are extensions beyond the book (ch13-15 already are), so
follow their shape: one new module or seam, demonstrated by a small addition to
the loop. Read `ch15/README.md` as the model for the write-up.

### Step 2 — scaffold the snapshot

```bash
cd <repo root>
cp -r ch15 ch16
rm -rf ch16/__pycache__
mv ch16/EXPLAINER_ch15.md ch16/EXPLAINER_ch16.md
```

Keep every inherited file. Add the new module (for example `ch16/telemetry.py` +
`telemetry.json`) and touch `nanocode.py` at exactly one seam, plus `ui.json` and
`hooks.py` only if the idea emits or renders something new. Never edit
`nanocode_copy.py`.

Then run the inherited suite from inside the new folder before writing a line of
prose:

```bash
cd ch16 && uv run pytest -q && cd ..
```

It must be green with the chapter-15 test count (92). Now append the new tests.

### Step 3 — write the chapter prose

`chNN/EXPLAINER_chNN.md` starts with a single `#` heading and follows the fixed
section order documented below. Start from
`references/chapter-template.md` in this skill.

### Step 4 — write `chNN/README.md`

From ch12 onward every chapter has one. Match `ch15/README.md`:

- one paragraph: "chapter N is chapter N-1 with one new verb/module";
- a file table (`File | Holds | Depends on`);
- `## What chapter N changed` fenced list of files and the exact additions;
- `## Run` commands, including the offline demo if any;
- a tests line with the new total;
- the invariant the chapter protects, as a short section.

### Step 5 — register the chapter everywhere

A chapter that is not registered builds but does not appear in the book, or
appears but is never tested. Every row below is required:

| File | Change |
|---|---|
| `build_explainer.py` | `CHAPTERS = [f"ch{n:02d}" for n in range(1, 17)]` |
| `build_explainer.py` `HEADER` | add the Contents row; update "chapters 1-15" prose |
| `build_explainer.py` `APPENDIX` | architecture tree, lifecycle-event list, glossary, `#chNN` anchor range, if the chapter adds a concept |
| `conftest.py` | add any new per-chapter module name to `CHAPTER_MODULES` |
| `pyproject.toml` | add `"ch16"` to `testpaths` |
| `run_all_tests.py` | add `"ch16"` to `CHAPTERS` |
| `README.md` | structure table row, chapter count, test total, run examples |
| `REFACTOR.md` | chapter/test counts and the module description |
| `ch16/README.md` | new |

`build_book.py` and `build_pdf.py` need no changes: chapters are discovered by
the regex `Chapter (\d+)`, and `#chNN` anchors are generated automatically.

### Step 6 — build and verify

```bash
uv run pytest -q                      # 384 + your new tests, all green
uv run python build_explainer.py      # prints line count, chapter count, missing files
uv run python build_book.py --pdf     # rewrites book.html and book.pdf

# no stale numbers or ranges left behind
grep -rn "384\|1-15\|fifteen\|fourteen" README.md REFACTOR.md build_explainer.py
```

Then check the artefacts as artefacts, not as source:

- `EXPLAINER.md` contains the new `## Chapter N — …` heading and its Contents row;
- `book.html` reports one more `<h2>` than before, and the sidebar shows the
  chapter with its sections nested;
- the new chapter's prev/next strip links to the correct neighbours;
- `book.pdf` has a bookmark for the chapter and a page number in its Contents.

The skill bundles `scripts/check_chapters.py`, which machine-checks registration
and missing explainers:

```bash
uv run python <skill-dir>/scripts/check_chapters.py .
```

## The chapter prose contract

Fixed order. A chapter that omits a section reads like documentation; a chapter
that keeps all of them reads like the book.

```markdown
# Chapter N — Title (the parenthetical states the tension)

> **You are here:** one to four lines: what this chapter adds and what it does not.

One to three paragraphs of motivation. Concrete, second person, present tense.

## The idea in one picture

```
ASCII only. `──►` is data flow, `▼` is time. Boxes are components; the text
inside is what passes between them.
```

## What's new on disk

```
chNN/
  new_file.py   what it holds        <- the whole chapter
  changed.py    what changed
```

## <The code sections>            (two to five H2s, named after the mechanism:
## The class                     "The contract", "The loop, annotated",
## The loop, annotated           "Retries: three cases, three behaviours")

## Watch it run (frame by frame)

Real program output, split into frames. Read top to bottom; it is the animation.

## Why it is built this way

**Question as a bold sentence.** The trade-off, stated as a trade-off, including
what the alternative would cost.

## Try it

1. An exercise that fails in an instructive way.
2. Another that changes one constant and predicts the result.

## Checkpoint

<details>
<summary>A question students actually ask?</summary>

The answer, in the same voice, two to five sentences.
</details>

## Extensions that teach the most      (ch13+ convention)

| Idea | Touch | What you learn |
|---|---|---|

**Closing line: chapter N-1 did X. Chapter N does Y — and the reason is Z.**
```

Rules that separate this book from a changelog:

- **Excerpts, not photocopies.** Join long expressions, mark omissions with
  `...`, add a comment only where the point is. Say so in the front matter.
- **No images, no Mermaid.** ASCII renders identically in Markdown, HTML, a
  terminal and print. Keep lines under ~80 columns so `<pre>` never wraps.
- **Every snippet is runnable-shaped.** If you show a class, show its real
  signature and a real call site from the chapter's files.
- **Numbers are verified.** "92 tests", "20 iterations", "4 in parallel" come
  from a run or a constant, never from memory.
- **Answers are collapsible.** `<details>`/`<summary>`; raw HTML passes through
  both `build_book.py` and pandoc.
- **Name the invariant, not the syntax.** "Safety by construction, not by
  instruction" is a chapter; `tool_definitions()` is a detail.
- **Do not add anchors.** `build_book.py` inserts `<a id="chNN"></a>` itself;
  a hand-written one becomes a paragraph-wrapped duplicate.
- **Line endings are mixed in this repo.** Some chapter files are CRLF. Write
  new files normally; do not mass-normalise existing ones.

## Pitfalls

- **Editing `EXPLAINER.md`.** It is overwritten. Change `HEADER`/`APPENDIX` in
  `build_explainer.py` and rebuild.
- **Forgetting the Contents table.** It is hard-coded in `HEADER`; chapter
  order in `CHAPTERS` does not generate it.
- **Heading level.** Per-chapter files use `#` for the chapter title because
  `demote()` pushes every heading down one level. Starting at `##` makes the
  chapter a section of the previous one.
- **Duplicate module names.** Every chapter has `nanocode.py`, `llm.py`, etc. A
  new per-chapter module must be added to `CHAPTER_MODULES` in `conftest.py`,
  or the combined `pytest` run leaks the wrong chapter's module.
- **ch02 is special.** It has `api_check.py`, no `nanocode.py`, and is excluded
  from `testpaths` and `run_all_tests.py` on purpose. Do not "fix" that.
- **Counting tests.** The total in README/REFACTOR is an assertion. Run
  `uv run pytest -q` and use the real number.
- **Stale `book.html`.** It is tracked in git. After a prose change, rebuild
  both HTML and PDF, or the repo ships a book that disagrees with its source.
- **Copying `__pycache__`.** Remove it after `cp -r`; it contains compiled
  modules from the previous chapter.
- **Windows shell.** The terminal is git-bash. Use `uv run …` from the repo
  root; pass native `C:/...` paths to native tools, not `/c/...`.

## Files

- `references/chapter-template.md` — copy-paste skeleton plus a worked
  registration diff.
- `scripts/check_chapters.py` — verifies every chapter folder is registered in
  the build/test files and that its explainer exists.

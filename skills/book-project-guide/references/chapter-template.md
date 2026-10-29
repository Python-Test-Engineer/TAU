# Chapter template and registration diff

Copy the skeleton, then replace every `<...>` placeholder. Delete sections only
if the chapter genuinely has nothing to put there; the order is the book's.

## Skeleton

```markdown
# Chapter 16 — <Title (the tension in parentheses)>

> **You are here:** <what this chapter adds>. <What it deliberately does not do.>

<Why the previous chapter leaves this problem open. Two or three paragraphs,
concrete and in the second person.>

## The idea in one picture

```
<ASCII diagram: ──► data flow, ▼ time, boxes are components>
```

<One paragraph reading the diagram: what enters, what leaves, what is new.>

## What's new on disk

```
ch16/
  <new_module>.py   <what it holds>          <- the whole chapter
  <changed>.py      <the one seam that changed>
```

<Why this belongs in a new file rather than in `nanocode.py`.>

## <Mechanism name>

<Introduce the object/function and the invariant it protects.>

```python
<real excerpt, ~10-25 lines, with `...` for omitted code>
```

<Walk the excerpt: what each non-obvious line buys.>

## <Second mechanism, if the idea needs one>

<Same shape: claim, excerpt, consequence.>

## Watch it run (frame by frame)

```
<real console output, split into frames with comments between them>
```

<Read the frames: point at the two lines that prove the new behaviour and at
the line that proves nothing else changed.>

## Why it is built this way

**Why not <the obvious alternative>?** <The trade-off, including what the
alternative would cost elsewhere in the repo.>

**Why <second decision>?** <The invariant it protects.>

## Try it

1. **<Exercise name>.** <What to change, what to predict, what surprising thing
   happens.>
2. **<Exercise name>.** <A second, independent knob.>
3. **<Break it>.** <How to disable the feature and prove it was the feature.>

## Checkpoint

<details>
<summary><Question a student actually asks?></summary>

<Answer, two to five sentences, same voice as the chapter.>
</details>

<details>
<summary><A question about the boundary or failure mode?></summary>

<Answer.>
</details>

## Extensions that teach the most

| Idea | Touch | What you learn |
|---|---|---|
| <extension> | `<file>` | <the concept it exposes> |
| <extension> | `<file>` | <the concept it exposes> |

**Chapter <N-1> did <X>. Chapter <N> does <Y> — and the reason is <Z>.**
```

## What the chapter's README must say

```markdown
# ch16 — <Title>

Chapter 16 is chapter 15 with **one new <verb/module>**: <one sentence>.

<One paragraph on the seam, naming the method/tool that carries it.>

| File | Holds | Depends on |
|------|-------|-----------|
| `<new_module>.py` | <what it holds> | <deps> |
| `nanocode.py` | <what it gained> | all of the above |

`nanocode_copy.py` is the book's original single file, kept for diffing.

## What chapter 16 changed

```
<new_module>.py   new - <contents>
nanocode.py       <the one seam>
ui.json           <new keys, if any>
test_nanocode.py  the ch15 suite + <n> tests (<total> total)
```

## Run

```bash
uv run ch16/nanocode.py
uv run ch16/nanocode.py --act
```

## <The invariant, as a short section heading>

<Why it is impossible to violate, not merely discouraged.>
```

## Worked registration diff

For `ch16`, from a clean tree at 15 chapters / 384 tests:

```diff
--- a/build_explainer.py
+++ b/build_explainer.py
@@
-CHAPTERS = [f"ch{n:02d}" for n in range(1, 16)]
+CHAPTERS = [f"ch{n:02d}" for n in range(1, 17)]
@@ HEADER
-1. **Cover to cover.** Read chapters 1-15 in order. Each builds on the last, and
+1. **Cover to cover.** Read chapters 1-16 in order. Each builds on the last, and
@@
 | [15](#ch15) | Subagents | one agent asks another; four ways to arrange them |
+| [16](#ch16) | <Title> | <the one new idea> |
@@ APPENDIX (only if the chapter adds a concept)
-  workflows.py   four arrangements over spawn(task)->str   <- composition (ch15+)
+  workflows.py   four arrangements over spawn(task)->str   <- composition (ch15+)
+  <module>.py    <one line>                                <- <role> (ch16+)
```

```diff
--- a/conftest.py
+++ b/conftest.py
@@
-CHAPTER_MODULES = ("ui", "llm", "tools", "hooks", "sounds", "sandbox", "workflows", "nanocode")
+CHAPTER_MODULES = ("ui", "llm", "tools", "hooks", "sounds", "sandbox", "workflows", "<module>", "nanocode")
```

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@
-testpaths = ["ch01", "ch03", ..., "ch15"]
+testpaths = ["ch01", "ch03", ..., "ch15", "ch16"]
```

```diff
--- a/run_all_tests.py
+++ b/run_all_tests.py
@@
-CHAPTERS = ["ch01", ..., "ch15"]
+CHAPTERS = ["ch01", ..., "ch15", "ch16"]
```

`README.md` and `REFACTOR.md` then need the new table row, the new chapter
count and the verified test total. `build_book.py` needs nothing.

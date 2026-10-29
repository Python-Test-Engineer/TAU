"""Check that every chapter in the Nanocode repo is registered and buildable.

    uv run python <skill-dir>/scripts/check_chapters.py [repo-root]

Looks at the repository, not at the book, so it catches the failure mode where
a chapter folder exists but no build/test file has learned about it.

Checks:
  * every `chNN/` with an EXPLAINER_chNN.md also has a README and tests
  * build_explainer.py's CHAPTERS range covers the highest chapter
  * build_explainer.py's HEADER Contents table has a row per chapter
  * pyproject.toml testpaths and run_all_tests.py CHAPTERS list every tested chapter
  * conftest.py CHAPTER_MODULES names every per-chapter module that exists

Exit code 0 when clean, 1 otherwise. No dependencies beyond the stdlib.
"""

import re
import sys
from pathlib import Path


def chapters(repo: Path):
    found = {}
    for directory in sorted(repo.glob("ch[0-9][0-9]")):
        found[int(directory.name[2:])] = directory
    return found


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = Path(argv[0] if argv else ".").resolve()
    problems = []

    dirs = chapters(repo)
    if not dirs:
        print(f"no chNN/ folders under {repo}")
        return 1

    numbers = sorted(dirs)
    highest = numbers[-1]
    print(f"chapters found: {len(numbers)} (ch01-ch{highest:02d})")

    # --- per-chapter files -------------------------------------------------
    for number in numbers:
        directory = dirs[number]
        name = f"ch{number:02d}"
        explainer = directory / f"EXPLAINER_{name}.md"
        if not explainer.exists():
            problems.append(f"{name}: missing {explainer.name}")
            continue
        first = explainer.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        if not first.startswith("# Chapter "):
            problems.append(f"{name}: explainer must start with '# Chapter N — ...' (got: {first[:60]!r})")
        if number >= 12 and not (directory / "README.md").exists():
            problems.append(f"{name}: missing README.md (ch12+ convention)")
        if number != 2 and not (directory / "test_nanocode.py").exists():
            problems.append(f"{name}: missing test_nanocode.py")

    # --- root registration ------------------------------------------------
    explainer_build = (repo / "build_explainer.py").read_text(encoding="utf-8")
    match = re.search(r"range\(1,\s*(\d+)\)", explainer_build)
    if not match:
        problems.append("build_explainer.py: cannot find CHAPTERS = range(1, N)")
    elif int(match.group(1)) != highest + 1:
        problems.append(
            f"build_explainer.py: CHAPTERS range(1, {match.group(1)}) stops before ch{highest:02d}"
        )

    for number in numbers:
        if f"](#ch{number:02d})" not in explainer_build:
            problems.append(f"build_explainer.py HEADER: Contents has no row for ch{number:02d}")

    tested = [n for n in numbers if (dirs[n] / "test_nanocode.py").exists()]

    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"testpaths\s*=\s*\[(.*?)\]", pyproject, re.S)
    listed = set(re.findall(r'"(ch\d\d)"', block.group(1))) if block else set()
    for number in tested:
        if f"ch{number:02d}" not in listed:
            problems.append(f"pyproject.toml: ch{number:02d} missing from testpaths")
    for name in sorted(listed - {f"ch{n:02d}" for n in tested}):
        problems.append(f"pyproject.toml: testpaths lists {name}, which has no test_nanocode.py")

    runner = (repo / "run_all_tests.py").read_text(encoding="utf-8")
    block = re.search(r"CHAPTERS\s*=\s*\[(.*?)\]", runner, re.S)
    runner_listed = set(re.findall(r'"(ch\d\d)"', block.group(1))) if block else set()
    for number in tested:
        if f"ch{number:02d}" not in runner_listed:
            problems.append(f"run_all_tests.py: ch{number:02d} missing from CHAPTERS")

    conftest = (repo / "conftest.py").read_text(encoding="utf-8")
    block = re.search(r"CHAPTER_MODULES\s*=\s*\((.*?)\)", conftest, re.S)
    modules = set(re.findall(r'"([a-z_]+)"', block.group(1))) if block else set()
    present = set()
    # Files that are scripts or frozen copies, not per-chapter importable
    # modules: `nanocode_copy.py` (the book's original), `api_check.py`
    # (ch02's throwaway request) and `demo_*.py` (offline demonstrations).
    ignored = {"nanocode", "nanocode_copy", "api_check"}
    for number in numbers:
        for path in dirs[number].glob("*.py"):
            if path.stem in ignored or path.stem.startswith(("test_", "demo_", "build_", "run_")):
                continue
            present.add(path.stem)
    # Modules that only exist in one chapter still need to be bindable there.
    for module in sorted(present - modules):
        problems.append(f"conftest.py: CHAPTER_MODULES has no '{module}'")

    # --- report -----------------------------------------------------------
    print(f"tested chapters: {len(tested)} (ch02 is excluded by design)")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  FAIL {problem}")
        return 1

    print("OK: every chapter is registered, has an explainer, tests and a README where required")
    return 0


if __name__ == "__main__":
    sys.exit(main())

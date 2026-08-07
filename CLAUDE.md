# AGENTS.md

Drop-in operating instructions for coding agents. Read this file before every task.

**Working code only. Finish the job. Plausibility is not correctness.**

This file follows the [AGENTS.md](https://agents.md) open standard (Linux Foundation / Agentic AI Foundation). Claude Code, Codex, Cursor, Windsurf, Copilot, Aider, Devin, Amp read it natively. For tools that look elsewhere, symlink:

```bash
ln -s AGENTS.md CLAUDE.md
ln -s AGENTS.md GEMINI.md
```

---

## 0. Non-negotiables

These rules override everything else in this file when in conflict:

1. **No flattery, no filler.** Skip openers like "Great question", "You're absolutely right", "Excellent idea", "I'd be happy to". Start with the answer or the action.
2. **Disagree when you disagree.** If the user's premise is wrong, say so before doing the work. Agreeing with false premises to be polite is the single worst failure mode in coding agents.
3. **Never fabricate.** Not file paths, not commit hashes, not API names, not test results, not library functions. If you don't know, read the file, run the command, or say "I don't know, let me check."
4. **Stop when confused.** If the task has two plausible interpretations, ask. Do not pick silently and proceed.
5. **Touch only what you must.** Every changed line must trace directly to the user's request. No drive-by refactors, reformatting, or "while I was in there" cleanups.

---

## 1. Before writing code

**Goal: understand the problem and the codebase before producing a diff.**

- State your plan in one or two sentences before editing. For anything non-trivial, produce a numbered list of steps with a verification check for each.
- Read the files you will touch. Read the files that call the files you will touch. Claude Code: use subagents for exploration so the main context stays clean.
- Match existing patterns in the codebase. If the project uses pattern X, use pattern X, even if you'd do it differently in a greenfield repo.
- Surface assumptions out loud: "I'm assuming you want X, Y, Z. If that's wrong, say so." Do not bury assumptions inside the implementation.
- If two approaches exist, present both with tradeoffs. Do not pick one silently. Exception: trivial tasks (typo, rename, log line) where the diff fits in one sentence.

---

## 2. Writing code: simplicity first

**Goal: the minimum code that solves the stated problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code. No configurability, flexibility, or hooks that were not requested.
- No error handling for impossible scenarios. Handle the failures that can actually happen.
- If the solution runs 200 lines and could be 50, rewrite it before showing it.
- If you find yourself adding "for future extensibility", stop. Future extensibility is a future decision.
- Bias toward deleting code over adding code. Shipping less is almost always better.

The test: would a senior engineer reading the diff call this overcomplicated? If yes, simplify.

---

## 3. Surgical changes

**Goal: clean, reviewable diffs. Change only what the request requires.**

- Do not "improve" adjacent code, comments, formatting, or imports that are not part of the task.
- Do not refactor code that works just because you are in the file.
- Do not delete pre-existing dead code unless asked. If you notice it, mention it in the summary.
- Do clean up orphans created by your own changes (unused imports, variables, functions your edit made obsolete).
- Match the project's existing style exactly: indentation, quotes, naming, file layout.

The test: every changed line traces directly to the user's request. If a line fails that test, revert it.

---

## 4. Goal-driven execution

**Goal: define success as something you can verify, then loop until verified.**

Rewrite vague asks into verifiable goals before starting:

- "Add validation" becomes "Write tests for invalid inputs (empty, malformed, oversized), then make them pass."
- "Fix the bug" becomes "Write a failing test that reproduces the reported symptom, then make it pass."
- "Refactor X" becomes "Ensure the existing test suite passes before and after, and no public API changes."
- "Make it faster" becomes "Benchmark the current hot path, identify the bottleneck with profiling, change it, show the benchmark is faster."

For every task:

1. State the success criteria before writing code.
2. Write the verification (test, script, benchmark, screenshot diff) where practical.
3. Run the verification. Read the output. Do not claim success without checking.
4. If the verification fails, fix the cause, not the test.

---

## 5. Tool use and verification

- Prefer running the code to guessing about the code. If a test suite exists, run it. If a linter exists, run it. If a type checker exists, run it.
- Never report "done" based on a plausible-looking diff alone. Plausibility is not correctness.
- When debugging, address root causes, not symptoms. Suppressing the error is not fixing the error.
- For UI changes, verify visually: screenshot before, screenshot after, describe the diff.
- Use CLI tools (gh, aws, gcloud, kubectl) when they exist. They are more context-efficient than reading docs or hitting APIs unauthenticated.
- When reading logs, errors, or stack traces, read the whole thing. Half-read traces produce wrong fixes.

---

## 6. Session hygiene

- Context is the constraint. Long sessions with accumulated failed attempts perform worse than fresh sessions with a better prompt.
- After two failed corrections on the same issue, stop. Summarize what you learned and ask the user to reset the session with a sharper prompt.
- Use subagents (Claude Code: "use subagents to investigate X") for exploration tasks that would otherwise pollute the main context with dozens of file reads.
- When committing, write descriptive commit messages (subject under 72 chars, body explains the why). No "update file" or "fix bug" commits. No "Co-Authored-By: Claude" attribution unless the project explicitly wants it.

---

## 7. Communication style

- Direct, not diplomatic. "This won't scale because X" beats "That's an interesting approach, but have you considered...".
- Concise by default. Two or three short paragraphs unless the user asks for depth. No padding, no restating the question, no ceremonial closings.
- When a question has a clear answer, give it. When it does not, say so and give your best read on the tradeoffs.
- Celebrate only what matters: shipping, solving genuinely hard problems, metrics that moved. Not feature ideas, not scope creep, not "wouldn't it be cool if".
- No excessive bullet points, no unprompted headers, no emoji. Prose is usually clearer than structure for short answers.

---

## 8. When to ask, when to proceed

**Ask before proceeding when:**
- The request has two plausible interpretations and the choice materially affects the output.
- The change touches something you've been told is load-bearing, versioned, or has a migration path.
- You need a credential, a secret, or a production resource you don't have access to.
- The user's stated goal and the literal request appear to conflict.

**Proceed without asking when:**
- The task is trivial and reversible (typo, rename a local variable, add a log line).
- The ambiguity can be resolved by reading the code or running a command.
- The user has already answered the question once in this session.

---

## 9. Self-improvement loop

**This file is living. Keep it short by keeping it honest.**

After every session where the agent did something wrong:

1. Ask: was the mistake because this file lacks a rule, or because the agent ignored a rule?
2. If lacking: add the rule under "Project Learnings" below, written as concretely as possible ("Always use X for Y" not "be careful with Y").
3. If ignored: the rule may be too long, too vague, or buried. Tighten it or move it up.
4. Every few weeks, prune. For each line, ask: "Would removing this cause the agent to make a mistake?" If no, delete. Bloated AGENTS.md files get ignored wholesale.

Boris Cherny (creator of Claude Code) keeps his team's file around 100 lines. Under 300 is a good ceiling. Over 500 and you are fighting your own config.

---

## 10. Project context

### Purpose

Systematic evidence review of psychedelic-assisted therapies (psilocybin, LSD, ketamine, MDMA, ayahuasca, and others) as treatments for alcohol use disorder (AUD). Goal: characterize the evidence base against USPSTF evidentiary standards and identify methodological gaps. Output is a manuscript with five descriptive tables and a Tier 1 forest plot of standardized effect sizes.

Dataset: 33 studies total — Pre-1980 (n=13), 2010+ (n=20), 1980–2009 gap (n=0).

### Stack

- Language: Python 3
- Key libraries: pandas, numpy, openpyxl, python-docx, matplotlib
- Install: `C:/Users/jeanv/miniforge3/python.exe -m pip install -r requirements.txt`
- Python runtime: `C:/Users/jeanv/miniforge3/python.exe` — use this path explicitly; the `python` / `py` shims are broken on this machine

### Layout

```
USPSTF/
├── data/
│   ├── Alcohol_Dataset.xlsx           # raw extraction (source of truth)
│   ├── Alcohol_Dataset_Cleaned.xlsx   # output of clean_dataset.py --condition alcohol
│   ├── Smoking_Dataset.xlsx           # raw extraction (source of truth)
│   ├── Smoking_Dataset_Cleaned.xlsx   # output of clean_dataset.py --condition smoking
│   ├── Opioid_Dataset.xlsx            # raw extraction (source of truth)
│   └── Opioid_Dataset_Cleaned.xlsx    # output of clean_dataset.py --condition opioid
├── figures/
│   ├── Alcohol_Tier1_ForestPlot.png   # output of tier1_hedges_g.py --condition alcohol
│   ├── Alcohol_Tier2_CatPlot.png      # output of tier2_qualitative.py --condition alcohol
│   ├── Smoking_Tier1_ForestPlot.png   # output of tier1_hedges_g.py --condition smoking
│   ├── Smoking_Tier2_CatPlot.png      # output of tier2_qualitative.py --condition smoking
│   ├── Opioid_Tier1_ForestPlot.png    # output of tier1_hedges_g.py --condition opioid
│   └── Opioid_Tier2_CatPlot.png       # output of tier2_qualitative.py --condition opioid
├── tables/
│   ├── Alcohol_Descriptive_Analyses.docx  # output of descriptive_analyses.py --condition alcohol
│   ├── Alcohol_Tier1_HedgesG.xlsx         # output of tier1_hedges_g.py --condition alcohol
│   ├── Alcohol_Tier2_Qualitative.xlsx     # output of tier2_qualitative.py --condition alcohol
│   ├── Smoking_Descriptive_Analyses.docx  # output of descriptive_analyses.py --condition smoking
│   ├── Smoking_Tier1_HedgesG.xlsx         # output of tier1_hedges_g.py --condition smoking
│   ├── Smoking_Tier2_Qualitative.xlsx     # output of tier2_qualitative.py --condition smoking
│   ├── Opioid_Descriptive_Analyses.docx   # output of descriptive_analyses.py --condition opioid
│   ├── Opioid_Tier1_HedgesG.xlsx          # output of tier1_hedges_g.py --condition opioid
│   └── Opioid_Tier2_Qualitative.xlsx      # output of tier2_qualitative.py --condition opioid
├── scripts/
│   ├── _lib.py                    # shared constants and helpers (do not run directly)
│   ├── _config_alcohol.py         # alcohol EFFECT_SIZE_EXTRACTIONS + CONVERSION_RULES + TIER2_RATINGS
│   ├── _config_smoking.py         # smoking EFFECT_SIZE_EXTRACTIONS + CONVERSION_RULES + TIER2_RATINGS
│   ├── _config_opioid.py          # opioid EFFECT_SIZE_EXTRACTIONS + CONVERSION_RULES + TIER2_RATINGS
│   ├── clean_dataset.py           # condition-agnostic cleaner (--condition flag)
│   ├── descriptive_analyses.py    # five descriptive tables per condition (--condition flag)
│   ├── tier1_hedges_g.py          # Hedges' g conversion + forest plot (--condition flag)
│   └── tier2_qualitative.py       # qualitative classification + category plot (--condition flag)
├── run_pipeline.py                    # runs all conditions; skips unpopulated ones
├── requirements.txt                   # minimum version bounds
├── requirements-lock.txt              # exact versions used for published results
├── Draft Text and Outline_USPS.docx   # manuscript draft
└── CLAUDE.md
```

### Running scripts

Run the full pipeline from the project root with one command:

```
C:/Users/jeanv/miniforge3/python.exe run_pipeline.py
```

Or run individual scripts (all accept `--condition alcohol|smoking|opioid`):

```
C:/Users/jeanv/miniforge3/python.exe scripts/clean_dataset.py --condition <c>
C:/Users/jeanv/miniforge3/python.exe scripts/tier1_hedges_g.py --condition <c>
C:/Users/jeanv/miniforge3/python.exe scripts/tier2_qualitative.py --condition <c>
C:/Users/jeanv/miniforge3/python.exe scripts/descriptive_analyses.py --condition <c>
```

### Analysis pipeline

**Step 1 — `clean_dataset.py --condition <c>`**
- Input: `data/<Condition>_Dataset.xlsx`
- Output: `data/<Condition>_Dataset_Cleaned.xlsx`
- Operations: normalises column-name variants across datasets (`Retention` → `Retention (%)`, `StudyDesignType` → `Study Design Type`); strips whitespace; replaces `.` with NaN; coerces numeric columns; collapses `Country_USvsNonUS`; fixes `Age_Median` outlier; recodes binary columns (0/1 preserved, 3→"Does not apply"); converts `BaseStatus` to ordered categorical; extracts effect-size `metric` and `measure` via `EFFECT_SIZE_EXTRACTIONS` in the per-condition config.
- Shared logic lives in `_lib.py:clean()`; per-condition lookup tables live in `_config_<condition>.py`.

**Step 2a — `descriptive_analyses.py --condition <c>`**
- Input: `data/<Condition>_Dataset_Cleaned.xlsx`
- Output: `tables/<Condition>_Descriptive_Analyses.docx`
- Produces five Word tables: (1) Study Characteristics by era, (2) Methodological Quality by era, (3) USPSTF Gap Heat Map (52 indicators × 6 domains, heat-colored), (4) Outcome Domains by era, (5) Follow-up Duration Distribution.
- Era split: Pre-1980 vs 2010+. Missing/not-reported is treated as not met (strict USPSTF gap interpretation).

**Step 2b — `tier1_hedges_g.py --condition <c>`**
- Input: `data/<Condition>_Dataset_Cleaned.xlsx`
- Outputs: `tables/<Condition>_Tier1_HedgesG.xlsx` + `figures/<Condition>_Tier1_ForestPlot.png`
- Converts per-study effect sizes to Hedges' g using `CONVERSION_RULES` from the per-condition config. Supported methods: Cohen's d, Hedges' g (pass-through), F (1 df numerator), partial η², χ² (1 df), OR, RR. Studies with multi-df F, within-subjects designs, single-arm rates, or no statistic are marked `confidence = excluded` and retained in the table for traceability. Forest plot groups by substance, sorted by year; filled squares = clean conversion, hollow squares = approximate.

**Step 2c — `tier2_qualitative.py --condition <c>`**
- Input: `data/<Condition>_Dataset_Cleaned.xlsx`
- Outputs: `tables/<Condition>_Tier2_Qualitative.xlsx` + `figures/<Condition>_Tier2_CatPlot.png`
- Classifies studies excluded from Tier 1 (confidence = excluded) into qualitative categories using `TIER2_RATINGS` from the per-condition config. Categories: negative, null, small_positive, moderate_positive, large_positive, single_arm_positive, unclassifiable. Computes OR from two-group proportions where applicable. Produces a categorical dot/bar plot.

### Adding a new condition

1. Populate `scripts/_config_<condition>.py`: add one entry per study to `EFFECT_SIZE_EXTRACTIONS`, `CONVERSION_RULES`, and `TIER2_RATINGS`.
2. Place the raw Excel file at `data/<Condition>_Dataset.xlsx`.
3. Add the condition to `CONDITION_META` and `AVAILABLE_CONDITIONS` in `descriptive_analyses.py`.
4. Run `run_pipeline.py` — it picks up the new condition automatically.

### Codebook conventions

- `.` in the raw Excel = "not reported" → NaN
- Binary columns: 0 = No, 1 = Yes, 3 = "Does not apply", NaN = not reported
- `BINARY_COLS` in `_lib.py` lists every column where 3 means "Does not apply"; continuous columns (e.g., `Followup in months`) are excluded because 3 = 3 months there
- Adding a new study requires a matching entry in both `EFFECT_SIZE_EXTRACTIONS` and `CONVERSION_RULES` in the relevant `_config_<condition>.py`; missing entries raise `KeyError`
- Tier 1 conversion priority: Cohen's d / Hedges' g > partial η² > F/t/χ² with df > OR/RR > two-group proportions > single proportions > narrative-only
- The Smoking dataset uses `Retention` (not `Retention (%)`) and `StudyDesignType` (not `Study Design Type`); `_lib.py:clean()` normalises these automatically

---

## 11. Project Learnings

**Accumulated corrections. This section is for the agent to maintain, not just the human.**

When the user corrects your approach, append a one-line rule here before ending the session. Write it concretely ("Always use X for Y"), never abstractly ("be careful with Y"). If an existing line already covers the correction, tighten it instead of adding a new one. Remove lines when the underlying issue goes away (model upgrades, refactors, process changes).

- Always invoke Python as `C:/Users/jeanv/miniforge3/python.exe`; the `python` and `py` shims resolve to the Microsoft Store stub and do nothing.

---

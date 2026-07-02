---
name: rehoboam
description: Multi-agent build orchestrator — one head that plans, parallel arms that execute, a fresh-context reviewer that verifies. Use this skill whenever the user invokes /rehoboam, asks to orchestrate a build task across multiple agents, wants a feature split into parallel sub-tasks, mentions "head and arms", "orchestrator", "parallel executors", "divergence", or asks to implement a non-trivial feature end-to-end (plan → build → review → integrate). Provider-agnostic - executors can run on Anthropic, OpenAI-compatible APIs, or local Ollama models, configured per-repo.
---

# REHOBOAM

One head that predicts. Many arms that act. Nothing diverges unreviewed.

The head (a strong model) scouts the codebase and splits the task into briefs.
The arms (cheaper/faster models, any provider) execute in parallel.
A reviewer with fresh context reads the real diff and judges against acceptance criteria.
The head runs the final end-to-end check and integrates.

```
USAGE:   /rehoboam <task to build>
```

## Step 0 — The Divergence Ring (intro)

Before anything else, run the intro animation once:

```bash
python3 scripts/rehoboam_intro.py
```

It renders the Westworld-style Rehoboam sphere with its rotating divergence
waveform (~4s, pure ANSI, no dependencies). If stdout is not a TTY it prints a
single static frame. Never let the animation block or crash the run — on any
error, skip it silently and continue.

## Step 1 — Load configuration

Look for `.rehoboam/config.json` in the repo root. If absent, use defaults
(copy `assets/config.example.json` to `.rehoboam/config.json` and tell the
user they can edit it).

```json
{
  "head":     { "provider": "anthropic", "model": "strongest-available" },
  "executor": { "provider": "anthropic", "model": "fast-capable" },
  "reviewer": { "provider": "anthropic", "model": "fast-capable" },
  "max_parallel_arms": 4,
  "max_revision_rounds": 2,
  "use_worktrees": "auto"
}
```

Supported providers: `anthropic`, `openai` (any OpenAI-compatible endpoint,
including Azure, Groq, Together, etc.), `ollama` (local). How to invoke each
provider for executor/reviewer runs is documented in
`references/providers.md` — read it before launching arms on a non-Anthropic
provider. When the provider is `anthropic` and a native subagent/Task tool is
available, prefer that over shelling out.

## Step 2 — THE HEAD (plan, never build)

The head is you, running on the session's model. Rules of the head:

1. **Scout the codebase read-only.** Map the areas the task touches: entry
   points, existing patterns, test setup, build commands. Do not write code.
2. **Split the task into briefs.** Each brief must be independently executable
   by an agent with zero conversation context. Aim for briefs that touch
   disjoint files; where overlap is unavoidable, mark the briefs as
   sequential or assign them to git worktrees.
3. **Never write the implementation yourself.** The head's output is the plan
   and the briefs — nothing else. (Exception: final integration in Step 5.)

### Brief format (one per arm)

```markdown
# BRIEF <n>: <title>
## Context
<what the repo is, where relevant code lives, patterns to follow — assume the
executor has never seen this codebase>
## Task
<precise, bounded instructions>
## Files in scope
<explicit list — the executor must not touch files outside it>
## Acceptance criteria
<objectively checkable list: commands that must pass, behaviors that must
exist, things that must NOT change>
```

Show the user the plan (briefs + parallelization strategy) before launching
the arms. If the task is trivial (one brief, one file), say so and offer to
do it directly instead of orchestrating — Rehoboam is overhead-heavy by
design and earns its cost only on multi-part tasks.

## Step 3 — THE ARMS (parallel executors)

Launch up to `max_parallel_arms` executors in parallel, one brief each:

- **Anthropic with subagent/Task tool available:** spawn one subagent per
  brief, passing the full brief text as the prompt.
- **Any provider via CLI/API:** use the adapter invocations in
  `references/providers.md` (`claude -p`, OpenAI-compatible chat call,
  `ollama run`), running each in the background and collecting output.

Isolation:
- `use_worktrees: "auto"` → create a git worktree per arm **only** when briefs
  share files or when more than 2 arms write code. `"always"`/`"never"` force
  the behavior.
- Worktree pattern: `git worktree add ../<repo>-arm-<n> -b rehoboam/arm-<n>`.

Each arm must end by producing a short self-report: files changed, commands
run, criteria it believes it satisfied.

## Step 4 — THE REVIEWER (fresh context, real diff)

For each completed arm, run a reviewer with **no memory of the planning
discussion** — its entire input is:

1. The brief (verbatim),
2. The real diff (`git diff` in the arm's worktree/branch — never accept the
   arm's self-report as a substitute for the diff),
3. The acceptance criteria, executed where they are commands.

The reviewer's verdict is exactly one of:

- **APPROVE** — criteria met, diff stays in scope.
- **REVISE: <numbered, actionable list>** — sent back to the **same executor
  with its context preserved** (same subagent conversation / same session).
  Maximum `max_revision_rounds` rounds; after that, escalate to the user with
  the reviewer's findings instead of looping.

The reviewer never fixes code itself. It only judges.

## Step 5 — THE HEAD again (final e2e check + integrate)

Once every arm is approved:

1. Merge worktree branches back. The head resolves trivial conflicts;
   non-trivial conflicts go back as a new mini-brief to the relevant arm.
2. Run the full build, the full test suite, and any e2e command the repo
   defines. A failure here becomes a targeted fix-brief for the responsible
   arm — not a silent patch by the head, unless it is a one-line integration
   fix, which the head may do and must declare in the summary.
3. Clean up: `git worktree remove` each worktree + delete merged
   `rehoboam/arm-*` branches.

## Step 6 — Summary to the user

Always end with this exact structure, headed by the divergence line:

```
◉ REHOBOAM — analysis complete. The loop has closed.

PLAN        <one-paragraph recap of the strategy>
SUB-TASKS   <table: arm · brief title · provider/model · rounds>
VERDICTS    <per arm: APPROVE at round N / escalated>
RESULTS     <build/test/e2e outcomes, files changed, how to try it>
```

## Failure doctrine

- An arm that errors out or times out → relaunch once with the same brief on
  the same provider; on a second failure → fall back to the head's provider;
  report both in the summary.
- Never let one failed arm block the others — collect all results first, then
  deal with failures.
- If `.rehoboam/config.json` names a provider whose credentials or binaries
  are missing, say exactly what is missing (which env var or binary) and fall
  back to the session's native model rather than aborting.
- Document everything: the plan, briefs, verdicts, and summary should be
  reproducible from the transcript alone.

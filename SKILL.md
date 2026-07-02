---
name: brigade
description: Multi-agent build orchestrator run like a kitchen brigade — one chef who writes the tickets, parallel cooks who fire them, a fresh-palate pass that tastes every diff. Use this skill whenever the user invokes /brigade (or the legacy /rehoboam), asks to orchestrate a build task across multiple agents, wants a feature split into parallel sub-tasks, mentions "chef and brigade", "tickets", "the pass", "refire", "orchestrator", "parallel executors", or asks to implement a non-trivial feature end-to-end (plan → build → review → integrate). Provider-agnostic - cooks can run on Anthropic, OpenAI-compatible APIs, or local Ollama models, configured per-repo.
---

# BRIGADE

*Formerly known as Rehoboam — the machine learned to cook.*

One chef who writes the menu. A brigade that cooks it. Nothing leaves the
pass untasted.

The chef (a strong model) scouts the kitchen and writes the tickets.
The brigade (cheaper/faster models, any provider) fires them in parallel,
each cook at their own station. The pass — a judge with a fresh palate —
tastes the real diff against the acceptance criteria. The chef runs final
service: build, test, integrate.

Glossary (kitchen → engineering): ticket = brief/sub-task · station = git
worktree · refire = revision round · 86'd = escalated to the user ·
service = final e2e check.

```
USAGE:   /brigade <task to build>
```

## Step 0 — Mise en place (intro)

Before anything else, run the intro animation once:

```bash
python3 scripts/brigade_intro.py
```

It renders the kitchen pass — steam over the toque, tickets printing on the
rail, service bell (~4s, pure ANSI, no dependencies). If stdout is not a TTY
it prints a single static frame. Never let the animation block or crash the
run — on any error, skip it silently and continue.

## Step 1 — Load configuration

Look for `.brigade/config.json` in the repo root. If absent, use defaults
(copy `assets/config.example.json` to `.brigade/config.json` and tell the
user they can edit it).

```json
{
  "chef": { "provider": "anthropic", "model": "strongest-available" },
  "cook": { "provider": "anthropic", "model": "fast-capable" },
  "pass": { "provider": "anthropic", "model": "fast-capable" },
  "max_parallel_cooks": 4,
  "max_refires": 2,
  "use_stations": "auto"
}
```

Supported providers: `anthropic`, `openai` (any OpenAI-compatible endpoint,
including Azure, Groq, Together, etc.), `ollama` (local). How to invoke each
provider for cook/pass runs is documented in `references/providers.md` —
read it before firing tickets on a non-Anthropic provider. When the provider
is `anthropic` and a native subagent/Task tool is available, prefer that
over shelling out.

Backward compatibility: if the repo has a legacy `.rehoboam/config.json`
with the old keys (`head`/`executor`/`reviewer`, `max_parallel_arms`,
`max_revision_rounds`, `use_worktrees`), read it, map the keys 1:1, and
offer to migrate it to `.brigade/config.json`.

## Step 2 — THE CHEF (writes the menu, never peels potatoes)

The chef is you, running on the session's model. Rules of the chef:

1. **Scout the kitchen read-only.** Map the areas the task touches: entry
   points, existing patterns, test setup, build commands. Do not write code.
2. **Write the tickets.** Split the task into tickets, each independently
   fireable by a cook with zero conversation context. Aim for tickets that
   touch disjoint files; where overlap is unavoidable, mark the tickets as
   sequential or assign them to separate stations (git worktrees).
3. **Never cook the dish yourself.** The chef's output is the menu (the
   plan) and the tickets — nothing else. (Exception: final integration at
   service, Step 5.)

### Ticket format (one per cook)

```markdown
# TICKET <n>: <title>
## Context
<what the repo is, where relevant code lives, patterns to follow — assume
the cook has never seen this kitchen>
## Task
<precise, bounded instructions>
## Files in scope
<explicit list — the cook must not touch files outside their station>
## Acceptance criteria
<objectively checkable list: commands that must pass, behaviors that must
exist, things that must NOT change>
```

Show the user the menu (tickets + parallelization strategy) before firing.
If the task is trivial (one ticket, one file), say so and offer to just cook
it directly instead of orchestrating — Brigade is overhead-heavy by design
and earns its cost only on multi-course tasks.

## Step 3 — THE BRIGADE (parallel cooks)

Fire up to `max_parallel_cooks` cooks in parallel, one ticket each:

- **Anthropic with subagent/Task tool available:** spawn one subagent per
  ticket, passing the full ticket text as the prompt.
- **Any provider via CLI/API:** use the adapter invocations in
  `references/providers.md` (`claude -p`, OpenAI-compatible chat call,
  `ollama run`), running each in the background and collecting output.

Stations (isolation):
- `use_stations: "auto"` → create a git worktree per cook **only** when
  tickets share files or when more than 2 cooks write code.
  `"always"`/`"never"` force the behavior.
- Station pattern: `git worktree add ../<repo>-station-<n> -b brigade/station-<n>`.

Each cook must end by producing a short self-report: files changed, commands
run, criteria they believe they plated.

## Step 4 — THE PASS (fresh palate, real diff)

For each plated ticket, run the pass with **no memory of the planning
discussion** — its entire input is:

1. The ticket (verbatim),
2. The real diff (`git diff` in the cook's station/branch — never accept
   the cook's self-report as a substitute for tasting the plate),
3. The acceptance criteria, executed where they are commands.

The pass's verdict is exactly one of:

- **APPROVE** — criteria met, diff stays in scope. The plate goes out.
- **REFIRE: <numbered, actionable list>** — sent back to the **same cook
  with their context preserved** (same subagent conversation / same
  session). Maximum `max_refires` rounds; after that, the ticket is 86'd —
  escalate to the user with the pass's findings instead of looping.

The pass never fixes the dish itself. It only tastes.

## Step 5 — THE CHEF again (service: final e2e + integrate)

Once every ticket is approved:

1. Merge station branches back. The chef resolves trivial conflicts;
   non-trivial conflicts go back as a new mini-ticket to the relevant cook.
2. Run the full build, the full test suite, and any e2e command the repo
   defines. A failure here becomes a targeted fix-ticket for the responsible
   cook — not a silent patch by the chef, unless it is a one-line
   integration fix, which the chef may do and must declare in the summary.
3. Clean the kitchen: `git worktree remove` each station + delete merged
   `brigade/station-*` branches.

## Step 6 — Summary to the user

Always end with this exact structure, headed by the service line:

```
🔔 BRIGADE — service complete. Kitchen closed, stations clean.

MENU      <one-paragraph recap of the strategy>
TICKETS   <table: cook · ticket title · provider/model · refires>
VERDICTS  <per ticket: APPROVE at refire N / 86'd>
PLATES    <build/test/e2e outcomes, files changed, how to taste it>
```

## Failure doctrine

- A cook that errors out or times out → refire once with the same ticket on
  the same provider; on a second failure → fall back to the chef's provider;
  report both in the summary.
- Never let one burned dish block the rest of service — collect all plates
  first, then deal with failures.
- If `.brigade/config.json` names a provider whose credentials or binaries
  are missing, say exactly what is missing (which env var or binary) and
  fall back to the session's native model rather than aborting.
- Document everything: the menu, tickets, verdicts, and summary should be
  reproducible from the transcript alone.

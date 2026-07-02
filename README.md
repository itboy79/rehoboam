<p align="center">
  <img src="docs/banner.svg" alt="REHOBOAM — divergence sphere" width="880"/>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0e7490.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-22d3ee.svg">
  <img alt="Claude Code Skill" src="https://img.shields.io/badge/claude--code-skill-e8b45a.svg">
  <img alt="Providers" src="https://img.shields.io/badge/providers-anthropic%20%7C%20openai%20%7C%20ollama-1d5b70.svg">
</p>

# Rehoboam

A multi-agent build orchestrator, packaged as a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills).

**One head that predicts. Many arms that act. Nothing diverges unreviewed.**

- 🧠 **The Head** — a strong model that scouts the codebase, splits the task
  into self-contained briefs, and *never writes the implementation itself*.
- 🦾🦾🦾 **The Arms** — parallel executors (cheaper/faster models, **any
  provider**: Anthropic, OpenAI-compatible, Ollama), isolated in git
  worktrees when needed.
- 🔍 **The Reviewer** — a fresh-context judge that reads the *real diff* and
  executes the acceptance criteria. Approves, or sends the work back to the
  *same* executor (context preserved) for up to 2 revision rounds.
- ✅ **The Head, again** — final end-to-end check: build, test, integrate,
  clean up.

```
USAGE:   /rehoboam <task to build>

you ─── /rehoboam "add rate limiting to the API"
 │
 ▼
┌──────────────────────────────────────────────────┐
│ 🧠 THE HEAD — orchestrator (strong model)        │
│ scouts the codebase · splits task into briefs    │
│ never writes the code itself                     │
└──────────────────────────────────────────────────┘
   │ brief #1        │ brief #2        │ brief #n
   ▼                 ▼                 ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    THE ARMS
│ executor │    │ executor │    │ executor │    run in parallel,
│ (any     │    │ (any     │    │ (any     │    worktrees if needed
│ provider)│    │ provider)│    │ provider)│
└──────────┘    └──────────┘    └──────────┘
   │                 │                 │
   ▼                 ▼                 ▼
┌──────────────────────────────────────────────────┐
│ 🔍 reviewer (fresh context)                      │
│ reads the real diff · runs acceptance criteria   │
└──────────────────────────────────────────────────┘
   │ approve                    │ revise (max 2 rounds)
   ▼                            └─▶ back to the SAME executor,
┌────────────────────────────┐      context preserved
│ 🧠 head — final e2e check  │
│ build · test · integrate   │
└────────────────────────────┘
   │
   ▼
◉ summary: plan · sub-tasks · verdicts · results
```

## Why

Big tasks fail in single-agent runs for two boring reasons: the context
window fills up with implementation noise, and the model grades its own
homework. Rehoboam splits the two problems apart — planning and building
happen in different contexts, and review happens in a context that has seen
*nothing* except the brief and the diff. The reviewer can't be charmed by
the executor's self-report, because it never reads it.

## Install

```bash
# personal skills (available in every project)
git clone https://github.com/YOUR_USERNAME/rehoboam.git ~/.claude/skills/rehoboam

# — or — project-level (committed with the repo)
git clone https://github.com/YOUR_USERNAME/rehoboam.git .claude/skills/rehoboam
```

Or run the installer, which does the first form and verifies python3:

```bash
./install.sh
```

Then in Claude Code:

```
/rehoboam add rate limiting to the API
```

The skill also triggers on natural phrasing — "orchestrate this across
agents", "split this feature into parallel sub-tasks", etc.

## Configuration

Per-repo config lives in `.rehoboam/config.json` (created from
[`assets/config.example.json`](assets/config.example.json) on first run):

```jsonc
{
  "head":     { "provider": "anthropic", "model": "claude-fable-5" },
  "executor": { "provider": "anthropic", "model": "claude-sonnet-5" },
  "reviewer": { "provider": "ollama",    "model": "llama3.3:70b" },
  "max_parallel_arms": 4,
  "max_revision_rounds": 2,
  "use_worktrees": "auto"   // auto | always | never
}
```

Any role can run on any provider — mixing them is encouraged: a reviewer on
a *different* provider than the executor has uncorrelated blind spots.

### Providers

| Provider    | How arms run                                              | REVISE context        |
| ----------- | --------------------------------------------------------- | --------------------- |
| `anthropic` | Native subagents, or `claude -p` (agentic: edits files)    | Session resume        |
| `openai`    | Codex CLI if present (agentic), else chat API in diff-mode | Stateless replay      |
| `ollama`    | Local chat API in diff-mode                                | Stateless replay      |

*Diff-mode:* a bare chat model can't touch the filesystem, so it returns
unified diffs and the head applies them (`git apply --check` first — a diff
that doesn't apply is an automatic REVISE). Full adapter details, including
`OPENAI_BASE_URL` for Azure/Groq/Together/LM Studio, are in
[`references/providers.md`](references/providers.md).

## The intro

Every run opens with the divergence ring — a Westworld-style ANSI animation
(pure Python, zero dependencies, degrades to a static frame when piped):

```bash
python3 scripts/rehoboam_intro.py
```

Set `REHOBOAM_NO_ANIM=1` to always get the static frame.

## Repository layout

```
rehoboam/
├── SKILL.md                    # the orchestrator playbook (what Claude reads)
├── scripts/
│   └── rehoboam_intro.py       # divergence-ring intro animation
├── references/
│   └── providers.md            # per-provider adapter invocations
├── assets/
│   └── config.example.json     # default .rehoboam/config.json
├── docs/
│   └── banner.svg              # the animated banner above
└── install.sh
```

## Design notes

- **The head never builds.** Its only outputs are the plan and the briefs
  (plus trivial, declared integration fixes at the very end). This keeps
  the planning context clean for the whole run.
- **Briefs are context-free.** Each one carries its own repo context, an
  explicit file scope, and objectively checkable acceptance criteria — an
  executor with zero conversation history must be able to run it.
- **Review reads the diff, not the report.** The executor's self-report is
  never accepted as evidence.
- **Revisions go back to the same arm.** Context preservation (session
  resume or message replay) is what makes round 2 cheaper than round 1.
- **Failure doctrine:** retry once on the same provider → fall back to the
  head's provider → report everything in the summary. One dead arm never
  blocks the others.

## License

[MIT](LICENSE) — Giorgio Gramegna.

*Not affiliated with HBO or Westworld. Rehoboam just really liked the
aesthetic of knowing what everyone will do next.*

# Provider adapters

How to launch an executor or reviewer on each supported provider. Every
adapter has the same contract:

- **Input:** a single prompt (the full brief, or the reviewer packet).
- **Output:** the agent's full text response, captured to
  `.rehoboam/runs/arm-<n>-round-<r>.md`.
- **Context preservation for REVISE rounds:** noted per adapter below —
  this is what makes "back to the SAME executor" work.

Before launching, verify the provider is actually usable (binary on PATH /
env var set / daemon running). If not, report exactly what's missing and fall
back to the session's native model.

---

## anthropic

**Preferred: native subagent / Task tool.** If the current environment can
spawn subagents, spawn one per brief with the brief as the prompt. REVISE
rounds continue the same subagent conversation — context is preserved
automatically.

**Fallback: Claude Code CLI.**

```bash
# first round — capture the session id
claude -p "$(cat brief-1.md)" \
  --model "$EXECUTOR_MODEL" \
  --output-format json > run.json
SESSION_ID=$(python3 -c "import json;print(json.load(open('run.json'))['session_id'])")

# REVISE round — resume the same session (context preserved)
claude -p "REVISE:\n$(cat review-notes.md)" --resume "$SESSION_ID" \
  --model "$EXECUTOR_MODEL"
```

Requires: `claude` on PATH, authenticated. Executors run with the repo (or
their worktree) as cwd so they can read/write files and run commands.

---

## openai (any OpenAI-compatible endpoint)

Works with OpenAI, Azure OpenAI, Groq, Together, LM Studio, etc. — anything
speaking `/v1/chat/completions`.

Env vars: `OPENAI_API_KEY`, optional `OPENAI_BASE_URL` (default
`https://api.openai.com/v1`).

If the OpenAI Codex CLI is installed, prefer it (it's agentic — it can edit
files and run commands itself):

```bash
codex exec --model "$EXECUTOR_MODEL" "$(cat brief-1.md)" \
  --cd "$ARM_WORKTREE"
# REVISE: codex exec resume --last "REVISE: ..."
```

Otherwise use the raw chat API. Note the crucial difference: a bare chat model
**cannot touch the filesystem**. In that mode the executor returns unified
diffs / full file contents, and the head applies them:

```bash
curl -s "$OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(python3 - <<'PY'
import json, pathlib
brief = pathlib.Path("brief-1.md").read_text()
print(json.dumps({
  "model": "MODEL_HERE",
  "messages": [
    {"role": "system", "content":
     "You are a Rehoboam arm. Return your changes as unified diffs in "
     "```diff blocks, plus the exact commands to verify them. Nothing else."},
    {"role": "user", "content": brief}
  ]
}))
PY
)"
```

REVISE rounds: replay the full message history (brief → assistant reply →
review notes) — the API is stateless, so *you* are the context preservation.
Apply returned diffs with `git apply --check` first; if a diff doesn't apply,
that's an automatic REVISE with the apply error included.

---

## ollama (local)

Env: daemon at `OLLAMA_HOST` (default `http://localhost:11434`). Check with
`curl -s $OLLAMA_HOST/api/tags`.

```bash
ollama run "$EXECUTOR_MODEL" < brief-1.md > run.md
```

Or the chat API (needed for REVISE rounds, same stateless replay as openai):

```bash
curl -s "$OLLAMA_HOST/api/chat" -d '{
  "model": "qwen2.5-coder:14b",
  "stream": false,
  "messages": [...]
}'
```

Same limitation as raw openai chat: diff-mode output, head applies. Local
models are weaker — prefer them for small, well-scoped briefs and for the
reviewer role (judging a diff against explicit criteria is easier than
writing code). Consider lowering `max_parallel_arms` to 2 to avoid saturating
local hardware.

---

## Mixing providers

The config sets one provider per role, but a brief may override it:
add `provider: ollama` / `model: ...` lines to a brief's front matter when a
sub-task is trivial enough for a cheap local model. The reviewer's provider
never has to match the executor's — a fresh-context reviewer on a *different*
provider is actually a feature (uncorrelated blind spots).

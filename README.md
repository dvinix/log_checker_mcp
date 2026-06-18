# 🔍 Log Checker MCP

> **AI-powered, fully automated bug detection → fix → GitHub PR pipeline.**
> Watches your live production logs, detects errors, fixes the code with Groq LLaMA 3.3-70b, and opens a GitHub PR — all while streaming everything to a real-time browser dashboard.

---

## Architecture

```
HuggingFace Space (dvinix/SecondBrain)
        │  live logs via huggingface-cli
        ▼
  log_watcher / dashboard watcher thread
        │  detects error blocks
        ▼
  orchestrator MCP  (orchestrator/main.py)
     ├── bug-identifier MCP  →  parses logs, extracts BugReport list
     ├── bug-fixer MCP       →  calls Groq LLaMA 3.3-70b to patch files
     └── github-pr MCP       →  cleans repo, commits, opens GitHub PR
        │
        ▼  SSE events  →  browser at http://localhost:8000
```

### Servers

| Server | Path | Responsibility |
|---|---|---|
| **Orchestrator** | `orchestrator/main.py` | `check_logs` tool — chains all three child servers |
| **Bug Identifier** | `servers/bug-identifier/main.py` | Regex-based Python + TypeScript error parser |
| **Bug Fixer** | `servers/bug-fixer/main.py` | Groq LLaMA-3.3-70b code patch generator |
| **GitHub PR** | `servers/github-pr/main.py` | Branch + commit + PR creation via GitHub REST API |
| **Dashboard** | `dashboard/main.py` | FastAPI SSE server + embedded HF log watcher |

---

## Demo Target Repository

**`dvinix/SecondBrain`** — a real FastAPI + React app deployed to HuggingFace Space `dvinix/SecondBrain`.

- Live HuggingFace logs → streamed via `huggingface-cli logs --tail dvinix/SecondBrain`
- Bug fixer patches real files: `backend/api/main.py`, `backend/pipeline/ingest.py`, etc.
- PRs appear on GitHub at `https://github.com/dvinix/SecondBrain/pulls`

---

## Prerequisites

```powershell
# 1. Python 3.14+ via uv
winget install astral-sh.uv

# 2. Install project dependencies
cd d:\log_checker_mcp
uv sync

# 3. HuggingFace login (for live log access)
uv run huggingface-cli login
```

---

## Configuration

Copy `.env` and fill in your secrets:

```env
GITHUB_TOKEN=ghp_...          # GitHub personal access token (repo + PR permissions)
GROQ_API_KEY=gsk_...          # Groq API key (https://console.groq.com)
HF_SPACE_ID=dvinix/SecondBrain         # HuggingFace Space to watch
TARGET_REPO_ROOT=d:\Assignment3\SecondBrain  # Local clone of the target repo
TARGET_GITHUB_OWNER=dvinix
TARGET_GITHUB_REPO=SecondBrain
```

---

## Running the Demo

### Option A — Real-Time Dashboard (recommended for mentor demo)

```powershell
# Start the dashboard (this also starts the HF log watcher automatically)
cd d:\log_checker_mcp
uv run uvicorn dashboard.main:app --port 8000

# Open in browser
start http://localhost:8000
```

The dashboard will:
1. Connect to `dvinix/SecondBrain` HuggingFace Space logs automatically
2. Stream every log line to your browser in real time
3. When an error is detected → trigger the full MCP pipeline
4. Show each pipeline step animating live (Analyzing → Fixing → PR Created)
5. Display the GitHub PR link with a click-to-open button

### Option B — CLI Watcher (headless)

```powershell
# Watch HuggingFace live logs (WATCH_HUGGINGFACE = True in log_watcher.py)
uv run python log_watcher.py

# Or watch local app_errors.log file (set WATCH_HUGGINGFACE = False)
uv run python log_watcher.py
```

### Option C — Manual Pipeline Trigger (for testing)

```powershell
# Trigger the orchestrator directly with a log snippet
uv run python -c "
import asyncio, sys
sys.path.insert(0, '.')

async def test():
    from mcp.client.stdio import stdio_client
    from mcp.client.session import ClientSession
    from mcp import StdioServerParameters

    params = StdioServerParameters(command='uv', args=['run', 'orchestrator/main.py'])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool('check_logs', {
                'repoRoot': r'd:\Assignment3\SecondBrain',
                'githubOwner': 'dvinix',
                'githubRepo': 'SecondBrain',
                'logContent': 'ERROR File \"backend/api/main.py\", line 42\nAttributeError: NoneType has no attribute fetch',
                'dryRun': True
            })
            print(res.content[0].text)

asyncio.run(test())
"
```

---

## MCP Tool Reference

### `check_logs` (Orchestrator)

| Parameter | Type | Required | Description |
|---|---|---|---|
| `repoRoot` | str | ✅ | Absolute path to local repo clone |
| `githubOwner` | str | ✅ | GitHub org/user (e.g. `dvinix`) |
| `githubRepo` | str | ✅ | Repo name (e.g. `SecondBrain`) |
| `logContent` | str | ⚠️* | Raw log text to analyze |
| `logFilePath` | str | ⚠️* | Path to a log file on disk |
| `maxBugs` | int | ❌ | Max bugs to process (default: 10) |
| `dryRun` | bool | ❌ | If true, fixes files but doesn't push/PR |
| `baseBranch` | str | ❌ | PR base branch (default: `main`) |
| `prLabels` | list | ❌ | PR labels (default: `["bug","automated-fix"]`) |

*One of `logContent` or `logFilePath` must be provided.

---

## Pipeline Flow

```
1. Bug Identifier   parse_logs_to_bugs()
   ├── Regex scan for Python "Error/Exception" lines
   ├── Extract file paths from stack traces (Python + TypeScript)
   └── Return list of BugReport {id, filePath, lineNumber, errorMessage, stackTrace}

2. Bug Fixer        fix_multiple_bugs()
   ├── Read full source file content
   ├── Prompt Groq LLaMA-3.3-70b with error context + file
   ├── Parse {fixedCode, explanation} JSON response
   └── Write patched file back to disk

3. GitHub PR        create_fix_pr()
   ├── _cleanup_repo(): remove __pycache__, .pyc, .DS_Store
   ├── git checkout -B fix-bugs-{sessionId[:8]}
   ├── git add . && git commit
   ├── git push -f -u <remote> <branch>
   └── POST /repos/{owner}/{repo}/pulls via GitHub REST API
```

---

## Project Structure

```
log_checker_mcp/
├── .env                     # Secrets (GITHUB_TOKEN, GROQ_API_KEY)
├── pyproject.toml           # uv project config
├── log_watcher.py           # Standalone CLI watcher (local file or HF)
├── test_orchestrator.py     # Manual pipeline test
├── app_errors.log           # Sample/static error log
│
├── orchestrator/
│   └── main.py              # Orchestrator MCP server (FastMCP)
│
├── servers/
│   ├── bug-identifier/
│   │   └── main.py          # BugReport extraction from logs
│   ├── bug-fixer/
│   │   └── main.py          # Groq LLaMA code patching
│   └── github-pr/
│       └── main.py          # Branch + commit + PR creation
│
├── dashboard/
│   ├── main.py              # FastAPI + SSE server + HF watcher thread
│   └── static/
│       └── index.html       # Real-time browser dashboard UI
│
└── shared/
    └── types.py             # Pydantic models: BugReport, CodeFix, etc.
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `huggingface-cli not found` | Run `uv run huggingface-cli login` and authenticate |
| `GITHUB_TOKEN not set` | Add token to `.env` — needs `repo` + `pull_requests` scope |
| `No bugs found` — logs parsed but 0 bugs | Ensure stack trace contains `File "..."` Python format |
| Git push fails | Confirm the local repo at `TARGET_REPO_ROOT` has the correct remote |
| Dashboard shows "Reconnecting" | Make sure `uvicorn dashboard.main:app --port 8000` is running |

---

## Key Design Decisions

- **Mode A (HuggingFace live stream)** — chosen for real demo. Uses `huggingface-cli logs --tail` which streams stdout from a deployed Space. No synthetic injection needed.
- **Thread + asyncio bridge** — The blocking log subprocess runs in a daemon thread; events are pushed thread-safely into asyncio queues via `loop.call_soon_threadsafe()`.
- **Pipeline deduplication** — A `_pipeline_running` flag prevents concurrent pipeline runs when multiple errors appear in rapid succession.
- **Code cleanup on PR** — `github-pr` server removes `__pycache__`, `.pyc`, and `.DS_Store` before committing so the PR diff is clean.

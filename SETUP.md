# Griffin Setup Guide

## Quick Start

### 1. Install Dependencies

**Frontend & Orchestrator (Bun):**
```bash
bun install
cd frontend && bun install
cd ../backend/orchestrator && bun install
```

**ML Pipeline (Python):**
```bash
cd ML
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

**Required for ML Pipeline:**
- `GOOGLE_API_KEY` - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- OR `OPENROUTER_API_KEY` - Get from [OpenRouter](https://openrouter.ai/)
- `GITHUB_TOKEN` - Get from [GitHub Settings](https://github.com/settings/tokens) (needs `repo` scope)
- `GITHUB_OWNER` - Your GitHub username

**Optional (for TypeScript wrappers):**
- `LLM_API_KEY` - Groq API key for PM wrapper
- `LLM_SPECIALIST_API_KEY` - Groq API key for specialist wrappers

### 3. Start the System

**Terminal 1 - Orchestrator:**
```bash
bun run dev:orchestrator
```

**Terminal 2 - PM Wrapper:**
```bash
bun run dev:wrapper:pm
```

**Terminal 3 - ML Pipeline Wrapper:**
```bash
bun run dev:wrapper:ml-pipeline
```

**Terminal 4 - Frontend:**
```bash
bun run dev:frontend
```

**Optional - Additional Wrappers:**
```bash
# Terminal 5
bun run dev:wrapper:frontend

# Terminal 6
bun run dev:wrapper:backend-api

# Terminal 7
bun run dev:wrapper:security
```

### 4. Open the UI

Navigate to [http://localhost:3000](http://localhost:3000)

## How It Works

### Chat Flow

1. **User types in Chat** → "Create a Snake game"
2. **PM Wrapper** analyzes the request
3. **ML Pipeline Wrapper** receives the prompt
4. **Python ML System** executes:
   - CEO Office: Plans the project
   - Product Office: Designs architecture
   - Engineering Office: Writes code
   - DevOps Office: Deploys to GitHub
5. **Progress updates** stream back to the UI
6. **GitHub link** appears when complete

### Architecture

```
Frontend (Next.js)
    ↓ WebSocket
Orchestrator (Bun)
    ↓ WebSocket
PM Wrapper (TypeScript)
    ↓ Routes to
ML Pipeline Wrapper (TypeScript)
    ↓ Spawns subprocess
ML System (Python/LangGraph)
    ↓ Generates & deploys
GitHub Repository
```

## Troubleshooting

### "Python not found"
- Install Python 3.10+ from [python.org](https://www.python.org/)
- Make sure `python` or `python3` is in your PATH

### "ML dependencies missing"
```bash
cd ML
pip install -r requirements.txt
```

### "Orchestrator connection failed"
- Make sure orchestrator is running on port 9100
- Check `ORCHESTRATOR_URL` in `.env`

### "GitHub push failed"
- Verify `GITHUB_TOKEN` has `repo` scope
- Verify `GITHUB_OWNER` matches your username
- Check token hasn't expired

### "Rate limit errors"
- Google Gemini free tier: 15 requests/minute
- Add delays or upgrade to paid tier
- Use OpenRouter as alternative

## Development

### Test ML Pipeline Standalone
```bash
python -m ML.main "Create a todo app"
```

### View Logs
```bash
# ML pipeline logs
ls ML/logs/

# Orchestrator logs (console only)
```

### Add New Wrappers
1. Create `backend/wrappers/your-wrapper/index.ts`
2. Register with orchestrator on startup
3. Add to `package.json` scripts
4. Update PM wrapper's `WRAPPER_NAMES` and `PLANNER_SYSTEM_PROMPT`

## Architecture Decisions

### Why Two Systems?

- **TypeScript Wrappers**: Fast, real-time, single-component generation
- **ML Pipeline**: Complete projects with proper architecture

### Why Subprocess?

- Python ML system is mature and tested
- Easier to maintain separate codebases
- Can run ML pipeline standalone via CLI
- Future: Could replace with HTTP API

### Why Sequential (Not Parallel)?

- Simpler debugging
- Avoids rate limits
- Each file can reference previous files
- More predictable output

## Next Steps

- [ ] Add streaming code preview to Workstation
- [ ] Support canceling in-progress ML pipeline
- [ ] Add cost estimation before running
- [ ] Cache common project templates
- [ ] Add project history/versioning

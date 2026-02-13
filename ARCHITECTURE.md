# Griffin Architecture

## Overview

Griffin is a simplified AI software studio that generates complete projects from a single prompt. The architecture has been streamlined to use just 2 services.

## System Architecture

```
User Input (Frontend)
    ↓ WebSocket
ML Service (Bun)
    ↓ Spawns subprocess
Python ML Pipeline (LangGraph)
    ↓ 4 Sequential Offices
GitHub Repository
```

## Services

### 1. ML Service (`backend/ml-service/`)
- **Runtime**: Bun + TypeScript
- **Port**: 9100
- **Purpose**: WebSocket server that receives prompts and spawns Python ML pipeline
- **Key Features**:
  - Receives chat messages from frontend
  - Spawns `python -m ML.main "prompt"` subprocess
  - Streams all stdout/stderr back to frontend in real-time
  - Sends progress updates and terminal output

### 2. Frontend (`frontend/`)
- **Runtime**: Next.js 16 + React 19
- **Port**: 3000
- **Purpose**: UI for chat, terminal, and visualization
- **Key Features**:
  - Chat interface for sending prompts
  - Terminal view showing all ML pipeline output
  - Real-time progress updates
  - GitHub link display on completion

### 3. ML Pipeline (`ML/`)
- **Runtime**: Python 3.10+ with LangGraph
- **Purpose**: Sequential 4-office agent system
- **Offices**:
  1. **CEO**: Plans project structure and file manifest
  2. **Product**: Designs architecture and tech stack
  3. **Engineering**: Writes code file-by-file
  4. **DevOps**: Creates GitHub repo and pushes code

## Data Flow

### 1. User Sends Prompt
```typescript
// Frontend: chat-page.tsx
sendChatMessage("Create a Snake game")
  ↓
// Store: orchestrator-store.ts
ws.send(JSON.stringify({ type: 'prompt', data: text }))
```

### 2. ML Service Receives & Executes
```typescript
// Backend: ml-service/index.ts
spawn('python', ['-m', 'ML.main', prompt])
  ↓
// Streams output back
ws.send({ type: 'terminal', data: line })
ws.send({ type: 'progress', data: importantLine })
```

### 3. Python Pipeline Executes
```python
# ML/main.py
chain = build_graph()  # CEO → Product → Engineering → DevOps
final_state = chain.invoke(initial_state)
```

### 4. Results Stream Back
```typescript
// Frontend receives:
{ type: 'progress', data: '✅ CEO OFFICE — Planning...' }
{ type: 'terminal', data: 'Writing file: index.html' }
{ type: 'complete', data: '🎉 Project complete!', githubUrl: '...' }
```

## File Structure

```
griffin/
├── backend/
│   └── ml-service/
│       ├── index.ts          # WebSocket server
│       └── package.json
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── chat-page.tsx           # Main chat UI
│       │   └── god-mode-terminal.tsx   # Terminal output
│       └── lib/
│           └── orchestrator-store.ts   # WebSocket client + state
├── ML/
│   ├── main.py              # CLI entry point
│   ├── graph.py             # LangGraph chain
│   ├── state.py             # Shared state
│   ├── config.py            # LLM config
│   └── offices/
│       ├── ceo.py           # Project planning
│       ├── product.py       # Architecture design
│       ├── engineering.py   # Code generation
│       └── devops.py        # GitHub deployment
└── package.json             # Root scripts
```

## Key Design Decisions

### Why 2 Services Instead of Complex Orchestrator?
- **Simplicity**: Direct WebSocket connection, no message routing
- **Reliability**: Fewer moving parts, easier to debug
- **Performance**: No intermediate hops

### Why Subprocess Instead of HTTP API?
- **Existing Code**: Python ML pipeline already works standalone
- **Isolation**: Each run is independent
- **Streaming**: Easy to capture stdout/stderr in real-time

### Why Sequential Office Execution?
- **Rate Limits**: Avoids hitting LLM API limits
- **Context**: Later files can reference earlier ones
- **Predictability**: Easier to debug and understand

## Environment Variables

```env
# ML Pipeline (required)
GOOGLE_API_KEY=your_key          # Or OPENROUTER_API_KEY
GITHUB_TOKEN=your_token          # For auto-deployment
GITHUB_OWNER=your_username

# ML Service (optional)
ML_SERVICE_PORT=9100             # Default: 9100

# Frontend (optional)
NEXT_PUBLIC_ML_SERVICE_URL=ws://localhost:9100
```

## Running the System

### Development
```bash
# Terminal 1: ML Service
bun run dev:ml

# Terminal 2: Frontend
bun run dev:frontend
```

### Production
```bash
# Build frontend
cd frontend && bun run build

# Run ML service
cd backend/ml-service && bun run start

# Serve frontend
cd frontend && bun run start
```

## Message Protocol

### Frontend → ML Service
```typescript
{ type: 'prompt', data: 'Create a Snake game' }
```

### ML Service → Frontend
```typescript
// Progress update (important lines)
{ type: 'progress', data: '✅ CEO OFFICE — Planning complete' }

// Terminal output (all lines)
{ type: 'terminal', data: 'Writing file: index.html' }

// Error output
{ type: 'terminal', data: '[ERROR] Failed to write file' }

// Completion
{
  type: 'complete',
  data: '🎉 Project complete!',
  githubUrl: 'https://github.com/user/project',
  projectName: 'snake-game'
}

// Error
{ type: 'error', data: '❌ ML pipeline failed: ...' }
```

## State Management

### Frontend Store (Zustand)
```typescript
interface OrchestratorState {
  connected: boolean;
  chatMessages: ChatMessage[];      // User + Griffin responses
  agentMessages: ChatMessage[];     // ML pipeline progress
  terminalLogs: string[];           // All ML output
  projectGithubUrl: string | null;
  projectName: string | null;
}
```

### Python State (LangGraph)
```python
class OfficeState(TypedDict):
    project_goal: str
    project_name: str
    file_manifest: list[str]
    tech_stack: dict[str, str]
    codebase: dict[str, str]
    github_url: str
    execution_logs: list[str]
```

## Error Handling

### Connection Errors
- Frontend auto-reconnects every 3 seconds
- Shows "Offline" indicator when disconnected

### Python Errors
- Captured in stderr
- Sent to frontend with `[ERROR]` prefix
- Displayed in terminal view

### Subprocess Errors
- Spawn failures caught and reported
- Exit code checked (0 = success)

## Performance Considerations

### Frontend
- Messages scroll automatically
- Terminal limited to prevent memory issues
- WebSocket reconnection with exponential backoff

### ML Service
- One subprocess per prompt
- Streams output line-by-line
- Cleans up on completion

### Python Pipeline
- Sequential execution (no parallelism)
- 1-second delay between files
- Rate limit friendly

## Security

### Sandboxing
- Python writes to `ML/sandbox/[project-name]/`
- No access to parent directories

### Environment Variables
- Secrets loaded from `.env`
- Never exposed to frontend

### WebSocket
- Local only (localhost:9100)
- No authentication (local dev)

## Future Improvements

- [ ] Add authentication for WebSocket
- [ ] Support canceling in-progress pipelines
- [ ] Add cost estimation before running
- [ ] Cache common project templates
- [ ] Add project history/versioning
- [ ] Support multiple concurrent projects
- [ ] Add progress percentage tracking

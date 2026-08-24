# Griffin 

**AI-Powered Software Studio** , Generate complete, production-ready projects from a single prompt.

Griffin is an intelligent multi-agent system that transforms natural language descriptions into fully functional applications, complete with code, tests, documentation, GitHub repositories, and live Vercel deployments.

---

## What It Does

Simply describe what you want to build, and Griffin's AI Office Chain handles the entire development lifecycle:

1. **CEO Office** , Analyzes requirements and plans the project structure
2. **Product Office** , Designs architecture and selects optimal tech stack  
3. **Engineering Office** , Writes all code files with best practices
4. **DevOps Office** , Creates GitHub repo, pushes code, and deploys to Vercel

**Example:**
```
User: "Create a Snake game with a score counter"
Griffin: [Generates HTML, CSS, JS, tests, README] → Pushes to GitHub → Deploys live URL
```

---

## Features

- **🤖 Multi-Agent AI Pipeline** , a dynamic chain of specialized AI offices, selected per prompt by the CEO office and run in sequence
- **⚡ Real-time Streaming** , Watch office status and logs stream live as the pipeline runs
- **📁 Complete Project Generation** , Source code, tests, documentation
- **🔗 Auto GitHub Integration** , Repositories created and code pushed automatically
- **🌐 Auto Vercel Deployment** , Live URLs generated for every project
- **💬 Interactive Chat Interface** , Natural conversation with the AI studio
- **🖥️ Terminal View** , Full visibility into the generation process
- **🎨 Modern UI** , Built with Next.js 16, React 19, and Tailwind CSS

---

## Implemented vs Roadmap

Griffin is an early prototype. This section separates what runs today from what is
still planned, so nothing here is oversold. The wider vision lives in
[REQUIREMENTS.md](REQUIREMENTS.md), which is a target specification rather than a
description of the current build.

### Implemented today

- **Dynamic office chain (LangGraph).** The CEO office runs first, picks which
  offices to activate for a given prompt, and the graph routes through only those
  offices before finishing at DevOps.
- **Two dozen offices.** The core set (CEO, Product Manager, Architect, Cost
  Optimizer, UI Designer, API Designer, Frontend, Backend, and Database Engineers,
  QA, Security, Tech Writer, DevOps) plus an expanded catalog: Legal and Compliance,
  UX Research, Design Systems, Localization, Performance, Accessibility, Marketing,
  Data Science, AI and ML, 3D, Game Dev, Mobile, and IoT. Each ships at least one
  real artifact file.
- **FastAPI backend with persistence.** `backend/api` exposes REST plus a WebSocket
  endpoint, mirrors the ml-service message contract, and persists projects, offices,
  and messages. It defaults to SQLite and uses Postgres when `DATABASE_URL` is set.
- **Containerized backend.** The repo root `Dockerfile` builds the FastAPI service
  plus the pipeline and is verified in CI to build, run, and complete a pipeline over
  its WebSocket.
- **GitHub and Vercel automation.** The DevOps office creates a GitHub repo, pushes
  the generated code, deploys to Vercel, writes a CI workflow into each generated
  project, and posts a QR code for the live URL.
- **Offline mock provider and tests.** `LLM_PROVIDER=mock` runs the whole chain with
  no API key and no network, covered by a pytest suite.
- **GitHub Actions CI.** Python tests, a frontend build, an ml-service bundle check,
  the FastAPI tests, and a full backend container build and run on every push and PR.
- **Live Blueprint Canvas.** Office status events stream over the WebSocket and drive
  node states in real time, including THINKING, edges colored by data type, and an
  office interior panel on click.
- **Monaco Workstation.** Generated files stream in as code artifacts and ghost type
  into a read only Monaco editor, with a live preview tab.
- **Cost Dashboard.** Fed by the real per-call token usage recorded during a run.
- **Communication Hub.** Auto channels grouped from tagged agent messages.
- **God Mode terminal.** `/evacuate`, `/deploy --force`, and `/status` dispatch real
  commands to the backend and read live state.
- **Deployment monitor widget.** Shows the live git and deploy steps during a run.
- **QA and Security offices.** QA runs real offline checks (`node --check`, Python
  `compile()`) and records results; Security runs a static scan and writes a
  measured `security_audit.md`.
- **Constitution checks.** Generated code is scanned against the file rules and a
  report is produced; secrets are masked in reports.
- **Real multiverse instances.** The Multiverse view maps one card per real git
  branch.
- **Project naming.** The generated project name flows through to the UI.

### Roadmap (not yet implemented)

- **The full 26-office catalog and the Head Agent plus Worker Drone structure.**
  About two dozen offices exist; a few specialized ones and the internal head and
  drone decomposition are still planned.
- **xterm terminal and per-character token streaming.** The God Mode view uses a
  custom log view rather than xterm, and the Workstation ghost types from completed
  artifacts rather than a per-character server stream.
- **The wider REQUIREMENTS.md v3 concepts** not listed above (for example the
  time scrubber, voice intercom, and metropolis views).

---

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   Frontend      │ ◄────────────────► │   ML Service     │
│  (Next.js 16)   │      Port 9100     │   (Bun + TS)     │
│    Port 3000    │                    │                  │
└─────────────────┘                    └────────┬─────────┘
                                                │
                                                │ Spawns
                                                ▼
                                       ┌──────────────────┐
                                       │  Python Pipeline │
                                       │   (LangGraph)    │
                                       │                  │
                                       │  CEO → Product   │
                                       │    → Eng → DevOps│
                                       └────────┬─────────┘
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          ▼                     ▼                     ▼
                   ┌─────────────┐      ┌──────────────┐      ┌─────────────┐
                   │   GitHub    │      │    Vercel    │      │   Sandbox   │
                   │   Repository│      │  Deployment  │      │   (Local)   │
                   └─────────────┘      └──────────────┘      └─────────────┘
```

---

## Tech Stack

### Frontend
- **Framework:** Next.js 16.1.6 + React 19.2.3
- **Styling:** Tailwind CSS 4 + Framer Motion
- **State:** Zustand 5
- **UI Components:** Radix UI primitives
- **3D Visuals:** React Three Fiber + Three.js
- **Workflow Diagrams:** XYFlow (React Flow)
- **Icons:** Lucide React

### Backend
- **ML Service:** Bun + TypeScript WebSocket service that spawns the pipeline
- **API Service:** Python FastAPI with REST plus WebSocket and SQLite or Postgres persistence (`backend/api`)
- **Container:** Repo root `Dockerfile` builds the API service plus the pipeline
- **Process Management:** Subprocess spawning for the Python pipeline

### AI Pipeline (Python)
- **Agent Framework:** LangGraph + LangChain
- **LLM Providers:** Google Gemini, OpenRouter, or an offline mock (`LLM_PROVIDER=mock`)
- **Git Integration:** PyGithub + GitPython
- **Deployment:** Vercel REST API + Requests
- **Environment:** Python 3.10+

---

## Prerequisites

### Required
- [Bun](https://bun.sh/) 1.0+ (JavaScript runtime)
- [Python](https://python.org/) 3.10+ 
- Git

### API Keys (for full functionality)
- **Google API Key** (for Gemini LLM) OR **OpenRouter API Key**
- **GitHub Token** (for auto-repository creation)
- **Vercel Token** (for auto-deployment)

---

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd griffin

# Install JavaScript dependencies for every package in one step
bun run setup

# Install Python dependencies
cd ML
pip install -r requirements.txt
cd ..
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required for AI (choose one)
GOOGLE_API_KEY=your_google_api_key_here
# OR
OPENROUTER_API_KEY=your_openrouter_key_here

# Required for GitHub integration
GITHUB_TOKEN=ghp_your_github_token
GITHUB_OWNER=your_github_username

# Required for Vercel deployment
VERCEL_TOKEN=your_vercel_token

# Optional (defaults shown)
ML_SERVICE_PORT=9100
NEXT_PUBLIC_ML_SERVICE_URL=ws://localhost:9100
```

### 3. Run the Application

Start both the ML service and the frontend together:

```bash
bun run dev
```

Or run them in separate terminals:

```bash
bun run dev:ml        # Terminal 1: ML WebSocket service on port 9100
bun run dev:frontend  # Terminal 2: Next.js dev server on port 3000
```

The application will be available at `http://localhost:3000`

---

## 🎯 Usage

1. Open `http://localhost:3000` in your browser
2. Type a project description in the chat (e.g., "Create a todo app")
3. Watch as the AI Office Chain generates your project in real-time
4. Get your live Vercel URL and GitHub repository link when complete

---

## 📁 Project Structure

```
griffin/
├── backend/
│   ├── ml-service/           # WebSocket server (Bun + TS)
│   │   ├── index.ts          # Main server with WebSocket handlers
│   │   └── package.json
│   └── api/                  # FastAPI service with persistence (Python)
│
├── frontend/                 # Next.js 16 application
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── chat-page.tsx         # Main chat interface
│   │   │   └── god-mode-terminal.tsx # Terminal output view
│   │   └── lib/
│   │       └── orchestrator-store.ts # WebSocket client + state
│   └── package.json
│
├── ML/                      # Python AI Pipeline
│   ├── main.py              # CLI entry point
│   ├── graph.py             # LangGraph orchestration
│   ├── config.py            # LLM configuration
│   ├── requirements.txt     # Python dependencies
│   └── offices/             # AI agent implementations
│       ├── ceo.py               # Project planning and office selection
│       ├── product_manager.py   # Requirements
│       ├── architect.py         # Tech stack and structure
│       ├── frontend_engineer.py # Code generation (plus backend and database)
│       └── devops.py            # GitHub and Vercel deployment
│
├── sandbox/                 # Generated projects (auto-created)
├── package.json            # Root package with dev scripts
└── .env                    # Environment variables (you create this)
```

---

## 🔧 Development

### Available Scripts

```bash
# Setup
bun run setup          # Install dependencies for every package

# Development
bun run dev            # Start ML service and frontend together
bun run dev:ml         # Start ML service only (port 9100)
bun run dev:frontend   # Start Next.js dev server only (port 3000)
bun run dev:tauri      # Start Tauri desktop app

# Production
bun run build          # Build the frontend for production
bun run start          # Start the production frontend server
```

### Running Tests

The pipeline ships with an offline mock provider, so the full office chain runs with
no API key and no network. From the repo root:

```bash
pip install -r ML/requirements-dev.txt
python -m pytest
```

To run the whole generator offline against a prompt (writes to `ML/sandbox/`):

```bash
LLM_PROVIDER=mock python -m ML.main "make a simple counter page"
```

---

## 🔐 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes* | - | Google Gemini API key |
| `OPENROUTER_API_KEY` | Yes* | - | OpenRouter API key (alternative) |
| `GITHUB_TOKEN` | No | - | GitHub Personal Access Token |
| `GITHUB_OWNER` | No | - | GitHub username/organization |
| `VERCEL_TOKEN` | No | - | Vercel API token |
| `ML_SERVICE_PORT` | No | `9100` | WebSocket server port |
| `NEXT_PUBLIC_ML_SERVICE_URL` | No | `ws://localhost:9100` | WebSocket URL |

*Only one LLM provider key is required.

---

## 🌐 Deployment

Griffin ships as two deployable pieces: the Next.js frontend and a Python backend
that runs the office pipeline. They talk over a WebSocket.

### 1. Backend (FastAPI plus the Python pipeline)

The repo root `Dockerfile` builds the backend container (the FastAPI service in
`backend/api` plus the `ML/` pipeline it spawns). It works on any container host
(Railway, Render, Fly, or your own server). `railway.toml` is preconfigured to build it.

Build and run locally:

```bash
docker build -t griffin-backend .
docker run -e LLM_PROVIDER=gemini -e GOOGLE_API_KEY=... -p 8000:8000 griffin-backend
```

Set these environment variables on the host for a real run (see the reference table):
`LLM_PROVIDER` and its key (`GOOGLE_API_KEY` or `OPENROUTER_API_KEY`), and optionally
`GITHUB_TOKEN`, `GITHUB_OWNER`, and `VERCEL_TOKEN` so generated projects are pushed and
deployed. `DATABASE_URL` switches persistence from the default SQLite to Postgres. With
no keys the backend runs in offline mock mode. The health check is `GET /`; the
WebSocket endpoint is `/ws`.

### 2. Frontend (Vercel)

1. Import the repository in Vercel and set the root directory to `frontend`.
2. Set `NEXT_PUBLIC_ORCHESTRATOR_URL` to your backend WebSocket URL, for example
   `wss://your-backend-host/ws` (use `wss` from an https site).
3. Deploy. The frontend build keeps the app router API routes; static export is only
   used for the Tauri desktop bundle.

### Local full stack

```bash
bun run dev   # starts the ML websocket service and the frontend together
```

---

## 🐛 Troubleshooting

### Common Issues

**WebSocket Connection Failed**
- Ensure ML Service is running on port 9100
- Check `NEXT_PUBLIC_ML_SERVICE_URL` matches your setup
- Verify no firewall blocking localhost:9100

**Python Module Not Found**
- Run `pip install -r ML/requirements.txt`
- Ensure Python 3.10+ is active

**API Key Errors**
- Verify `.env` file exists in project root
- Check that keys are valid and have necessary permissions

**GitHub Push Fails**
- Ensure `GITHUB_TOKEN` has `repo` scope
- Verify `GITHUB_OWNER` matches your username

**Vercel Deployment Fails**
- Check `VERCEL_TOKEN` is valid
- Ensure token has project creation permissions

**Frontend build reports missing modules on Windows**
- Bun plus the Turbopack builder can fail to resolve some nested transitive
  modules (for example `picocolors`) on Windows. If you hit this locally, install
  the frontend with `npm install` inside `frontend/` as a workaround. This affects
  local Windows builds only, not CI or Vercel.

**Production build fails with an `output: export` error**
- The default `bun run build` produces a normal server build so the API routes
  work. Static export is opt in and only for the Tauri desktop bundle, enabled with
  `NEXT_OUTPUT_EXPORT=1`.

### Getting API Keys

- **Google API Key:** [Google AI Studio](https://aistudio.google.com/app/apikey)
- **GitHub Token:** Settings → Developer settings → Personal access tokens → Tokens (classic)
- **Vercel Token:** [Vercel Dashboard](https://vercel.com/account/tokens)

---

## 🗺️ Roadmap

- [ ] Authentication system
- [ ] Project history and versioning
- [ ] Support for multiple concurrent projects
- [ ] Template caching for faster generation
- [ ] Cost estimation before running
- [ ] Cancel in-progress pipelines
- [ ] Additional deployment targets (Netlify, AWS)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Built with [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration
- Powered by [Google Gemini](https://deepmind.google/technologies/gemini/) / OpenRouter
- UI components from [Radix UI](https://www.radix-ui.com/)
- Icons by [Lucide](https://lucide.dev/)

---

**Built with ❤️ by the Griffin Team**

*Transform ideas into production-ready software, one prompt at a time.*

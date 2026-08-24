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
- **⚡ Real-time Streaming** , Watch progress live as code is generated
- **📁 Complete Project Generation** , Source code, tests, documentation
- **🔗 Auto GitHub Integration** , Repositories created and code pushed automatically
- **🌐 Auto Vercel Deployment** , Live URLs generated for every project
- **💬 Interactive Chat Interface** , Natural conversation with the AI studio
- **🖥️ Terminal View** , Full visibility into the generation process
- **🎨 Modern UI** , Built with Next.js 16, React 19, and Tailwind CSS

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
- **ML Service:** Bun + TypeScript
- **WebSocket:** Real-time bidirectional communication
- **Process Management:** Subprocess spawning for Python pipeline

### AI Pipeline (Python)
- **Agent Framework:** LangGraph + LangChain
- **LLM Providers:** Google Gemini / OpenRouter
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

# Install JavaScript dependencies for each package
bun install
cd frontend && bun install && cd ..
cd backend/ml-service && bun install && cd ../..

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

**Terminal 1 , Start ML Service:**
```bash
bun run dev:ml
```

**Terminal 2 , Start Frontend:**
```bash
bun run dev:frontend
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
│   └── ml-service/           # WebSocket server (Bun + TS)
│       ├── index.ts          # Main server with WebSocket handlers
│       └── package.json
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
│       ├── ceo.py           # Project planning
│       ├── product.py       # Architecture design
│       ├── engineering.py    # Code generation
│       └── devops.py        # GitHub + Vercel deployment
│
├── sandbox/                 # Generated projects (auto-created)
├── package.json            # Root package with dev scripts
└── .env                    # Environment variables (you create this)
```

---

## 🔧 Development

### Available Scripts

```bash
# Development
bun run dev:ml         # Start ML Service (port 9100)
bun run dev:frontend   # Start Next.js dev server (port 3000)
bun run dev:tauri      # Start Tauri desktop app

# Production
cd frontend && bun run build   # Build frontend for production
cd frontend && bun run start   # Start production server
```

### Running Tests

```bash
cd ML
python -m pytest tests/  # If tests exist
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

### Vercel (Recommended)

1. Push your code to GitHub
2. Import repository in Vercel dashboard
3. Set environment variables in Vercel settings
4. Deploy

### Manual Server

```bash
# Build frontend
cd frontend
bun run build

# Start production servers
cd backend/ml-service && bun run start  # Terminal 1
cd frontend && bun run start            # Terminal 2
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

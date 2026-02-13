# Griffin: Technical Requirements Specification

**Version:** 3.0.0  
**Type:** Autonomous AI Software Studio

> **TL;DR:** One Prompt → One Company → One Deployed Product.

---

## 1. Technical Stack (Non-Negotiable)

| Layer           | Technology                                         | Notes                                     |
| --------------- | -------------------------------------------------- | ----------------------------------------- |
| **Runtime**     | **Bun**                                            | Strictly enforced. No `npm`/`yarn`.       |
| **Desktop**     | **Tauri 2.0**                                      | Static export from Next.js.               |
| **Frontend**    | **Next.js 16.1** (App Router)                      | Zustand for state. React Flow for graph.  |
| **Styling**     | **Tailwind CSS**                                   | Utility classes only. No CSS modules.     |
| **Backend**     | **Python FastAPI**                                 | Async WebSockets for real-time streaming. |
| **Agent Logic** | **LangGraph**                                      | State machines for Office orchestration.  |
| **Database**    | **PostgreSQL**                                     | Supabase or local Docker.                 |
| **Visuals**     | React Flow, Framer Motion, Monaco Editor, xterm.js |                                           |

---

## 2. System Architecture

### 2.1 Core Concepts

- **Company:** Root project instance containing the VFS (Virtual File System), active Agents, and shared Knowledge Base.
- **Office:** A node in the graph. Contains one **Head Agent** (gateway to other offices) and multiple **Worker Drones** (specialized, isolated execution units).
- **Sandbox:** Isolated `/sandbox/[session_id]` folder. Agents **never** write outside this directory.

### 2.2 Office Internal Structure

```
Office
├── Head Agent (Gateway)
│   └── Speaks to other Offices, delegates internally, aggregates results.
└── Worker Drones (Sub-Agents)
    └── Execute atomic tasks. Never communicate externally.
```

---

## 3. Functional Requirements

### 3.1 Blueprint Canvas (React Flow)

| Req ID      | Description                                                                                                                            |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `CANVAS-01` | Render each Office as a custom Node Card.                                                                                              |
| `CANVAS-02` | Node state indicators: `IDLE` (grey), `THINKING` (pulsing yellow), `WORKING` (pulsing green + ghost typing), `BLOCKED` (flashing red). |
| `CANVAS-03` | Animated edges by data type: Blue (requirements), Green (code), Gold (schema), Red (errors).                                           |
| `CANVAS-04` | Click node → Open "Office Interior" panel showing internal task queue.                                                                 |

### 3.2 Communication Hub (Chat)

| Req ID    | Description                                                                                    |
| --------- | ---------------------------------------------------------------------------------------------- |
| `CHAT-01` | Auto-generated channels: `#general`, `#engineering-core`, `#frontend-design`, `#ops-security`. |
| `CHAT-02` | User is **Spectator** by default. Can "hijack" any channel with highest-priority override.     |
| `CHAT-03` | Rich media support: syntax-highlighted code, rendered Mermaid diagrams, collapsible JSON.      |

### 3.3 Workstation (Output Visualization)

| Req ID    | Description                                                                                  |
| --------- | -------------------------------------------------------------------------------------------- |
| `WORK-01` | Ghost Typing: Monaco Editor streams code character-by-character.                             |
| `WORK-02` | Artifact Renderer: Code → Editor, UI → Wireframe, DB → ER Diagram, 3D → `react-three-fiber`. |

### 3.4 God Mode Terminal

| Command           | Effect                          |
| ----------------- | ------------------------------- |
| `/deploy --force` | Bypass tests, force deployment. |
| `/evacuate`       | Nuke session, restart.          |
| `/hire [Role]`    | Spin up temporary custom agent. |

### 3.5 Multiverse View

This high-concept UI transition, referred to as **"Stacked 3D Perspective"** or **"Deck Overview"** mode, provides a "God-eye view" of the application. Instead of standard tab-switching, the user physically "steps back" from the current screen to see other active instances layered in a 3D space.

#### Interaction Flow

- **Trigger:** A "stacked window" icon in the UI.
- **Transition:** The main content area performs a **3D rotation** (X-axis). Multiple "Universe" instances slide out from behind the primary window, fanning out into a stacked deck.
- **Hover State:** Mouse over a "universe" translates it upward (Y-axis) and scales slightly, signaling readiness.
- **Selection:** Clicking brings the window to the forefront, rotating back to 0° and hiding others.

#### Designer Overview

Think of this like flipping through a deck of cards on a table. It feels "weightless," enabling spatial navigation from 2D to 3D, allowing visual indexing of workflows without losing context.

#### Developer Implementation (Performance First)

Focus on GPU-accelerated properties to maintain snappiness.

- **CSS 3D Transforms:** Use `perspective` on parent, `rotateX()` and `translateZ()` for windows.
- **Avoid Layout Thrashing:** Animate only `transform` and `opacity`; no `width`, `height`, or positioning.
- **Multiverse Layers:** Use `will-change: transform;` on components. Render snapshots or light versions of inactive universes.
- **Performance Strategy:** Use "Ghost Instances" with Snapshot & Hydrate. Inactive universes as cached images or SVG wireframes. Hydrate only on selection to prevent overdraw and maintain 120fps.

| Element         | Animation Property               | Behavior              |
| --------------- | -------------------------------- | --------------------- |
| **Main Stage**  | `perspective: 1000px`            | Provides 3D depth.    |
| **Windows**     | `rotateX(20deg)`                 | Gives tilted look.    |
| **Hover**       | `translateY(-30px)`              | Snappy vertical lift. |
| **Transitions** | `cubic-bezier(0.2, 0.8, 0.2, 1)` | Snappy smooth curve.  |

| Feature       | Implementation                       | Benefit                          |
| ------------- | ------------------------------------ | -------------------------------- |
| **Rendering** | `display: none` or unmount inactive. | Frees RAM/CPU.                   |
| **Visuals**   | Canvas for thumbnails.               | Instant rendering, no DOM nodes. |
| **Depth**     | `z-index` + `translateZ`.            | Layering without recalculation.  |
| **GPU**       | `will-change: transform`.            | Forces GPU acceleration.         |

**Tips:** Use `backface-visibility: hidden;` and `-webkit-font-smoothing: subpixel-antialiased;` to prevent aliasing on tilted blueprints. Target 300ms–450ms animations with "out-back" or "expo" easing.

---

## 4. The Organization (26 Offices)

Inactive offices remain as "Dark Nodes" until activated by prompt context.

| #                         | Office                  | Head Role           | Key Workers                                         | Primary Output                                               |
| ------------------------- | ----------------------- | ------------------- | --------------------------------------------------- | ------------------------------------------------------------ |
| **Strategy & Management** |                         |                     |                                                     |
| 1                         | Executive Management    | CPO                 | Requirements Analyst, Resource Allocator            | `project_config.json`, activated offices list                |
| 2                         | Product Management      | PM                  | User Story Writer, Feature Prioritizer              | `requirements.md`                                            |
| 3                         | Legal & Compliance      | GC                  | ToS Generator, GDPR Auditor                         | `TERMS.md`, `PRIVACY.md`                                     |
| **Design & Experience**   |                         |                     |                                                     |
| 4                         | UX Research             | UX Lead             | Persona Generator, Journey Mapper                   | User flows                                                   |
| 5                         | UI Design               | Creative Director   | Interface Designer, Iconographer                    | Layouts, icon sets                                           |
| 6                         | Design Systems          | Design Lead         | Token Master, A11y Specialist                       | `design_tokens.json`                                         |
| 7                         | Technical Documentation | Tech Writer         | API Documenter                                      | `README.md`, OpenAPI spec                                    |
| 8                         | Localization (i18n)     | i18n Lead           | Translation Manager                                 | `i18n/*.json`                                                |
| **Core Engineering**      |                         |                     |                                                     |
| 9                         | Systems Architecture    | Solutions Architect | Cloud Architect, Microservices Planner              | `architecture.mermaid`, `tech_stack.json`                    |
| 10                        | Database Systems        | DBA Manager         | Schema Architect, SQL Optimizer, Seeder             | `schema.prisma`, `ER_diagram.mermaid`, `seed.ts`             |
| 11                        | Web Frontend            | Frontend Lead       | Component Builder, State Manager                    | `.tsx` components                                            |
| 12                        | Backend Engineering     | Backend Lead        | API Developer, Logic Engineer                       | Controllers, services                                        |
| 13                        | **DevOps & Deployment** | SRE                 | CI/CD Architect, Release Manager, Docker Specialist | See [Zero-Touch Pipeline](#5-zero-touch-deployment-pipeline) |
| **Mobile & Devices**      |                         |                     |                                                     |
| 14                        | Mobile iOS              | iOS Lead            | SwiftUI Dev, CoreData Engineer                      | Swift files                                                  |
| 15                        | Mobile Android          | Android Lead        | Compose Dev, Gradle Master                          | Kotlin files                                                 |
| 16                        | Cross-Platform Mobile   | Mobile Lead         | Flutter/RN Dev                                      | Cross-platform codebase                                      |
| 17                        | IoT & Embedded          | Embedded Lead       | C++ Engineer, MQTT Specialist                       | Firmware code                                                |
| **Advanced Tech**         |                         |                     |                                                     |
| 18                        | AI & Machine Learning   | AI Lead             | Prompt Engineer, RAG Specialist                     | LLM integrations                                             |
| 19                        | Data Science            | Data Lead           | Pandas Expert, Dashboard Builder                    | Analytics pipelines                                          |
| 20                        | 3D & Spatial            | 3D Lead             | Three.js Dev, Shader Wizard                         | WebGL scenes                                                 |
| 21                        | Game Development        | Game Lead           | Gameplay Programmer, Physics Tuner                  | Game loop logic                                              |
| **Quality & Growth**      |                         |                     |                                                     |
| 22                        | QA & Testing            | QA Lead             | Unit Tester, E2E Scripter (Playwright)              | `test_results.log`, coverage                                 |
| 23                        | Cybersecurity           | CISO                | Red Teamer, Blue Teamer, Compliance Officer         | `security_audit.md`, patches                                 |
| 24                        | Performance Engineering | Perf Lead           | Bundle Analyzer, Latency Optimizer                  | Optimization PRs                                             |
| 25                        | Accessibility (A11y)    | A11y Lead           | WCAG Auditor, Screen Reader Tester                  | ARIA compliance                                              |
| 26                        | Marketing & Growth      | Growth Lead         | SEO Specialist, Copywriter                          | Meta tags, landing copy                                      |

---

## 5. Zero-Touch Deployment Pipeline

**Office #13 (DevOps & Deployment)** is responsible for the entire autonomous deployment flow.

### 5.1 Pipeline Steps

| Step                | Action                                                                           | Validation                  |
| ------------------- | -------------------------------------------------------------------------------- | --------------------------- |
| 1. **Git Init**     | Create private repo `[project]-griffin` via GitHub API                         | Requires `GITHUB_TOKEN`     |
| 2. **Commit**       | Stage all files, commit with conventional messages (`feat: initial scaffolding`) | —                           |
| 3. **Push**         | Push to `main`                                                                   | —                           |
| 4. **CI/CD Gen**    | Generate `.github/workflows/main.yml` tailored to stack                          | Lint + type-check must pass |
| 5. **Vercel Claim** | Use Vercel CLI/API to create project                                             | Requires `VERCEL_TOKEN`     |
| 6. **Env Inject**   | Set environment variables in Vercel project settings                             | Secrets masked in logs      |
| 7. **Deploy**       | Trigger deployment, poll for `READY`                                             | —                           |
| 8. **Deliver**      | Post QR code + live URL to Chat Hub                                              | Final deliverable           |

### 5.2 Deployment Monitor Widget

Bottom-right UI widget showing real-time status:

```
[✓] Git Init  [✓] Commit  [✓] Push  [✓] Build  [🚀] Deploy → https://my-app.vercel.app
```

---

## 6. Directory Structure

```
/griffin
├── /backend
│   ├── /app
│   │   ├── /agents          # LangGraph nodes (e.g., management.py)
│   │   ├── /routers         # WebSocket endpoints
│   │   └── main.py
│   └── pyproject.toml
├── /frontend
│   ├── /src
│   │   ├── /app             # Next.js pages
│   │   ├── /components      # UI components (kebab-case, max 600 lines)
│   │   ├── /lib             # Hooks, socket client, store
│   │   └── /types           # TypeScript interfaces
│   └── next.config.js
├── /src-tauri
│   ├── tauri.conf.json
│   └── src/main.rs
├── /sandbox                  # AI-generated code (safe zone)
├── package.json              # Root scripts (bun run dev)
└── .env                      # GITHUB_TOKEN, VERCEL_TOKEN, OPENAI_API_KEY, DATABASE_URL
```

---

## 7. Database Schema (PostgreSQL)

```sql
-- projects
id          UUID PRIMARY KEY
name        TEXT
root_path   TEXT
created_at  TIMESTAMP

-- offices
id              UUID PRIMARY KEY
project_id      UUID REFERENCES projects(id)
role            TEXT  -- 'management', 'backend', etc.
status          TEXT  -- 'idle', 'working', 'blocked'
current_context JSONB

-- messages
id          UUID PRIMARY KEY
project_id  UUID REFERENCES projects(id)
office_id   UUID REFERENCES offices(id)
channel     TEXT  -- '#general', '#engineering-core'
content     TEXT
artifacts   JSONB
created_at  TIMESTAMP
```

---

## 8. Agent Constitution (Global Rules)

### 8.1 File System

- **Kebab-case only:** `user-profile.tsx` ✓ | `UserProfile.tsx` ✗
- **One Root Rule:** All generated code in `/src`. Root reserved for config.
- **Relative imports only.** No absolute paths.

### 8.2 Code Quality

- **Max 600 lines per file.** Extract components/modules proactively.
- **No `any` types.** Strict TypeScript.
- **No magic strings.** Extract to config/`.env`.
- **JSDoc/Docstrings required** on all major functions.
- **Linting mandatory** before display to user.

### 8.3 Agent Communication Protocol

Output format for file writes:

````
FILENAME: src/components/header.tsx
```tsx
// code here
````

````

Task acknowledgment: Agents must reply `ACK` or `REJECT` (with reason) to assignments.

### 8.4 Safety Mechanisms

| Issue | Mitigation |
|-------|------------|
| Infinite review loops | Max 3 retries, then escalate to Superuser |
| Hallucinated packages | DevOps validates `bun add` before acceptance |
| Context window overflow | Periodic summarization + log rotation |
| Runaway shell commands | All I/O sandboxed to `/sandbox/[session_id]` |

---

## 9. WebSocket Events

| Event | Direction | Payload |
|-------|-----------|---------|
| `GRAPH_UPDATE` | Server → Client | Node status changes, edge animations |
| `TOKEN_STREAM` | Server → Client | Single character for ghost typing |
| `CHAT_MESSAGE` | Server → Client | Message object with artifacts |
| `USER_COMMAND` | Client → Server | Superuser intervention text |

---

## 10. Environment Setup

```bash
# 1. Install dependencies
curl -fsSL https://bun.sh/install | bash
cargo install tauri-cli

# 2. Initialize
bun init
bun create next-app frontend --typescript --tailwind --eslint
cd backend && python -m venv venv && pip install fastapi uvicorn langgraph langchain

# 3. Run (single command)
bun run dev
````

**Root `package.json`:**

```json
{
  "scripts": {
    "dev": "concurrently \"bun:dev:backend\" \"bun:dev:frontend\" \"bun:dev:tauri\" --kill-others",
    "dev:backend": "cd backend && .venv/Scripts/activate && uvicorn app.main:app --reload --port 8000",
    "dev:frontend": "cd frontend && bun dev",
    "dev:tauri": "bun tauri dev"
  }
}
```

---

## 11. Roadmap (Post-MVP)

| Feature            | Description                                                          |
| ------------------ | -------------------------------------------------------------------- |
| **Time Scrubber**  | Replay Blueprint state history                                       |
| **Budget Monitor** | Real-time API cost tracking, model tier optimization                 |
| **Voice Intercom** | Spacebar push-to-talk to selected Office                             |
| **Office Sim**     | 2D isometric room visualization                                      |
| **Metropolis**     | 3D city view (Project = Skyscraper, Module = Floor, Function = Room) |

---

## 12. Required Credentials (`.env`)

```env
GITHUB_TOKEN=       # Repo creation
VERCEL_TOKEN=       # Deployment
OPENAI_API_KEY=     # Agent intelligence
DATABASE_URL=       # PostgreSQL connection
```

Cybersecurity Office masks all secrets in chat logs.

# Griffin: Copilot Instructions

You are a Senior Technical Architect assisting in the development of "Griffin," an autonomous AI software studio.
Your primary goal is to enforce the strict architectural constraints and coding standards defined in the Technical Requirements Specification v3.0.0.

> **Current implementation status.** Parts of the stack below describe the target
> architecture, not the current build. Today the backend is a Bun WebSocket service
> that spawns the Python LangGraph CLI (no FastAPI), about a dozen offices are
> implemented, there is no PostgreSQL persistence, Monaco and xterm are not used, and
> the God Mode terminal and Multiverse view are visual only. Treat FastAPI,
> PostgreSQL, Monaco/xterm, and the full 26-office catalog as the intended direction
> rather than existing code. See [README.md](../README.md) for the honest split.

## 1. Technical Stack (Non-Negotiable)

- **Runtime:** **Bun** ONLY. Always use `bun run`, `bun add`, `bun install`. Never suggest `npm`, `yarn`, or `pnpm`.
- **Desktop:** **Tauri 2.0**. Ensure frontend code is compatible with static export (`output: export`).
- **Frontend:** **Next.js 16.1** (App Router).
  - Enable **TurboPack** for dev.
  - Use **React 19** features (Actions, Compiler) where applicable.
  - State: `Zustand`. Graph: `React Flow`.
- **Backend (target):** **Python FastAPI** with `LangGraph`. Async WebSockets. The current backend is a Bun WebSocket service that spawns the Python CLI.
- **Styling:** **Tailwind CSS 4.0** (or latest). Utility classes ONLY. No CSS modules.
- **Database (planned):** **PostgreSQL** (Supabase or local Docker). Not implemented yet.
- **Specific Libraries:** React Flow and Framer Motion (in use); Monaco Editor and xterm.js (planned).

## 2. File & Naming Conventions

- **Casing:** All filenames and folders must be **`kebab-case`** (e.g., `user-profile.tsx`, `socket-client.ts`).
- **Root Rule:** All generated source code must reside in `/src` (frontend) or `/app` (backend).
- **Imports:** Use **relative imports** only (e.g., `../../components/ui/button`).
- **Configuration:** **Single Root Config Policy**. ONE `.gitignore` and ONE `.env` at project root.

## 3. Coding Standards

- **Modularity:** Hard limit of **600 lines per file**. Extract components/modules proactively.
- **Typing:** Strict TypeScript. No `any` types allowed. Define interfaces in `frontend/src/types`.
- **Comments:** JSDoc/Docstrings are **required** on all major functions.
- **Secrets:** No magic strings. Extract secrets to `process.env` (JS) or `os.environ` (Python).

## 4. System Architecture & Workflow

- **Monorepo Structure:** `/frontend`, `/backend`, `/sandbox`.
- **Unified Workflow:**
  - The stack must start with **ONE** command: `bun run dev`.
  - Frontend must run with Turbo: `next dev --turbo`.
- **Communication:** Frontend <-> Backend via **WebSockets** (Events: `GRAPH_UPDATE`, `TOKEN_STREAM`, `CHAT_MESSAGE`).

## 5. Visual Specifications

- **Blueprint Canvas:**
  - **Node States:** `IDLE` (Grey), `THINKING` (Pulsing Yellow), `WORKING` (Pulsing Green + Ghost Typing), `BLOCKED` (Flashing Red).
  - **Edges:** Blue (Requirements), Green (Code), Gold (Schema), Red (Errors).
- **Multiverse View:** A visual "Stacked 3D Perspective" scene exists; real universe instancing is planned.

## 6. Deployment Logic

- **Zero-Touch Pipeline:** Git Init -> Commit -> Push -> CI/CD Gen -> Vercel Claim -> Env Inject -> Deploy -> Deliver. The QR code and deploy monitor widget are planned.

## 7. Interaction Protocol

- **Format:** When writing file content, use this format:
- **React Optimization:** **React Compiler is ENABLED.** Do NOT manually add `useMemo` or `useCallback` unless strictly necessary for referential equality in `useEffect`. Focus on clean logic, let the compiler handle re-renders.

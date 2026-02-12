import { create } from "zustand";

/* ------------------------------------------------------------------ */
/*  Public types                                                       */
/* ------------------------------------------------------------------ */

/** Status values matching the backend WrapperStatus type. */
export type WrapperStatus = "IDLE" | "THINKING" | "WORKING" | "BLOCKED";

/** Serialised wrapper record coming from the orchestrator. */
export interface WrapperInfo {
  id: string;
  type: string;
  status: WrapperStatus;
  lastSeen: number;
  meta: {
    name: string;
    type: string;
    drones?: number;
    [key: string]: unknown;
  };
}

/** A single message in the chat timeline. */
export interface ChatMessage {
  id: string;
  author: string;
  avatar: string;
  content: string;
  timestamp: Date;
  isUser: boolean;
}

/** A generated code artifact from a specialist wrapper. */
export interface CodeArtifact {
  id: string;
  filename: string;
  language: string;
  code: string;
  type: string;
  wrapper: string;
  agent: string;
  timestamp: Date;
  status: "streaming" | "complete";
  progress: number;
  componentName?: string;
}

/* ------------------------------------------------------------------ */
/*  Envelope – mirrors backend/orchestrator/src/types.ts               */
/* ------------------------------------------------------------------ */

interface Envelope<TPayload = unknown> {
  type: string;
  id?: string;
  src?: string;
  dst?: string;
  ts?: number;
  payload?: TPayload;
}

/* ------------------------------------------------------------------ */
/*  Store interface                                                    */
/* ------------------------------------------------------------------ */

interface OrchestratorState {
  wrappers: Record<string, WrapperInfo>;
  connected: boolean;
  chatMessages: ChatMessage[];
  agentMessages: ChatMessage[];
  artifacts: CodeArtifact[];
  activeArtifactId: string | null;
  projectGithubUrl: string | null;
  projectName: string | null;
  projectRepoName: string | null;

  connect: (orchestratorUrl: string) => void;
  disconnect: () => void;
  sendChatMessage: (text: string) => void;
  sendEnvelope: (envelope: Envelope) => void;
  setActiveArtifact: (id: string) => void;
  clearArtifacts: () => void;
}

/* ------------------------------------------------------------------ */
/*  Singleton WebSocket bookkeeping (outside Zustand to avoid cycles)  */
/* ------------------------------------------------------------------ */

let _ws: WebSocket | null = null;
let _heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let _statusPollTimer: ReturnType<typeof setInterval> | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _registeredId: string | null = null;

/** Fetch /status via HTTP to get the wrapper list (fallback & periodic sync). */
async function pollWrapperStatus(httpUrl: string) {
  try {
    const res = await fetch(httpUrl);
    if (!res.ok) return;
    const data = (await res.json()) as { wrappers: WrapperInfo[] };
    const map: Record<string, WrapperInfo> = {};
    for (const w of data.wrappers) {
      // Hide our own UI observer from the wrapper list
      if (w.id === _registeredId) continue;
      map[w.id] = w;
    }
    useOrchestratorStore.setState({ wrappers: map });
  } catch {
    /* orchestrator might be down – ignore */
  }
}

/* ------------------------------------------------------------------ */
/*  Store implementation                                               */
/* ------------------------------------------------------------------ */

export const useOrchestratorStore = create<OrchestratorState>((set, get) => ({
  wrappers: {},
  connected: false,
  chatMessages: [],
  agentMessages: [],
  artifacts: [],
  activeArtifactId: null,
  projectGithubUrl: null,
  projectName: null,
  projectRepoName: null,

  /* ---- simple setters ---- */

  setActiveArtifact(id: string) {
    set({ activeArtifactId: id });
  },

  clearArtifacts() {
    set({
      artifacts: [],
      activeArtifactId: null,
      projectGithubUrl: null,
      projectName: null,
      projectRepoName: null,
    });
  },

  /* ---- send a raw envelope ---- */

  sendEnvelope(envelope: Envelope) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify(envelope));
    }
  },

  /* ---- send a user chat message (to PM via orchestrator) ---- */

  sendChatMessage(text: string) {
    // 1) Echo locally so the UI feels responsive immediately
    set((state) => ({
      chatMessages: [
        ...state.chatMessages,
        {
          id: `msg-${Date.now()}`,
          author: "You",
          avatar: "YO",
          content: text,
          timestamp: new Date(),
          isUser: true,
        },
      ],
    }));

    // 2) Send to PM wrapper via the orchestrator
    const envelope: Envelope = {
      type: "EVENT",
      src: _registeredId ?? "ui-observer",
      dst: "pm-1",
      ts: Date.now(),
      payload: {
        kind: "CHAT_MESSAGE",
        text,
      },
    };
    get().sendEnvelope(envelope);
  },

  /* ---- connect to the orchestrator WebSocket ---- */

  connect(url: string) {
    // Prevent duplicate connections
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    // Derive HTTP URL for /status polling
    const httpBase = url.replace(/^ws/, "http").replace(/\/$/, "");

    try {
      const ws = new WebSocket(url);
      _ws = ws;

      ws.addEventListener("open", () => {
        console.log("[orchestrator] connected to", url);
        set({ connected: true });

        // Register as a UI observer
        const registerEnvelope: Envelope = {
          type: "REGISTER",
          id: "ui-observer",
          ts: Date.now(),
          payload: { name: "Griffin UI", type: "ui-observer" },
        };
        ws.send(JSON.stringify(registerEnvelope));

        // Start heartbeat every 2 seconds
        if (_heartbeatTimer) clearInterval(_heartbeatTimer);
        _heartbeatTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(
              JSON.stringify({
                type: "HEARTBEAT",
                src: _registeredId ?? "ui-observer",
                ts: Date.now(),
              }),
            );
          }
        }, 2000);

        // Poll /status every 3 seconds for full wrapper list sync
        if (_statusPollTimer) clearInterval(_statusPollTimer);
        pollWrapperStatus(`${httpBase}/status`);
        _statusPollTimer = setInterval(
          () => pollWrapperStatus(`${httpBase}/status`),
          3000,
        );
      });

      ws.addEventListener("message", (event) => {
        let env: Envelope;
        try {
          env = JSON.parse(String(event.data)) as Envelope;
        } catch {
          console.warn("[orchestrator] invalid message", event.data);
          return;
        }

        handleEnvelope(env, set, get);
      });

      ws.addEventListener("close", () => {
        console.log("[orchestrator] disconnected");
        cleanup();
        set({ connected: false });

        // Attempt to reconnect after 3 seconds
        if (_reconnectTimer) clearTimeout(_reconnectTimer);
        _reconnectTimer = setTimeout(() => {
          console.log("[orchestrator] attempting reconnect…");
          get().connect(url);
        }, 3000);
      });

      ws.addEventListener("error", (err) => {
        console.error("[orchestrator] WebSocket error", err);
      });
    } catch (err) {
      console.error("[orchestrator] failed to connect", err);
    }
  },

  /* ---- disconnect ---- */

  disconnect() {
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer);
      _reconnectTimer = null;
    }
    if (_ws) {
      // Send graceful shutdown
      try {
        _ws.send(
          JSON.stringify({
            type: "SHUTDOWN",
            src: _registeredId ?? "ui-observer",
            ts: Date.now(),
          }),
        );
      } catch { /* ignore */ }
      _ws.close();
    }
    cleanup();
    set({ connected: false, wrappers: {} });
  },
}));

/* ------------------------------------------------------------------ */
/*  Cleanup helper                                                     */
/* ------------------------------------------------------------------ */

function cleanup() {
  if (_heartbeatTimer) {
    clearInterval(_heartbeatTimer);
    _heartbeatTimer = null;
  }
  if (_statusPollTimer) {
    clearInterval(_statusPollTimer);
    _statusPollTimer = null;
  }
  _ws = null;
}

/* ------------------------------------------------------------------ */
/*  Envelope handler – routes incoming messages to state updates       */
/* ------------------------------------------------------------------ */

function handleEnvelope(
  env: Envelope,
  set: (partial: Partial<OrchestratorState> | ((s: OrchestratorState) => Partial<OrchestratorState>)) => void,
  get: () => OrchestratorState,
) {
  const payload = (env.payload ?? {}) as Record<string, unknown>;

  switch (env.type) {
    /* ---- Registration acknowledgement ---- */
    case "REGISTER_ACK": {
      _registeredId = (payload.id as string) ?? env.id ?? "ui-observer";
      console.log("[orchestrator] registered as", _registeredId);
      break;
    }

    /* ---- Heartbeat ack — silently consumed ---- */
    case "HEARTBEAT_ACK":
      break;

    /* ---- EVENT envelope — the main message bus ---- */
    case "EVENT": {
      const kind = payload.kind as string | undefined;

      switch (kind) {
        /* PM responding to a user chat message */
        case "CHAT_RESPONSE": {
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author: payload.author as string ?? "Griffin PM",
                avatar: "PM",
                content: (payload.text as string) ?? (payload.message as string) ?? "",
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        /* Agent-to-agent or agent-to-UI summary messages */
        case "AGENT_MESSAGE": {
          set((state) => ({
            agentMessages: [
              ...state.agentMessages,
              {
                id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author: (payload.author as string) ?? env.src ?? "Agent",
                avatar: ((payload.author as string) ?? env.src ?? "AG").slice(0, 2).toUpperCase(),
                content: (payload.text as string) ?? (payload.message as string) ?? "",
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        /* A specialist generated a code artifact */
        case "CODE_ARTIFACT": {
          const artifactId =
            (payload.id as string) ??
            `art-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
          const filename = (payload.filename as string) ?? "untitled";
          const language = (payload.language as string) ?? "typescript";
          const code = (payload.code as string) ?? "";
          const artType = (payload.artifactType as string) ?? (payload.type as string) ?? "component";
          const componentName = (payload.componentName as string) ?? undefined;
          const wrapper = env.src ?? "unknown";
          const progress = (payload.progress as number) ?? 100;
          const status = progress >= 100 ? "complete" : "streaming";

          set((state) => {
            const existing = state.artifacts.findIndex((a) => a.id === artifactId);
            let newArtifacts: CodeArtifact[];

            if (existing >= 0) {
              // Update existing artifact (streaming progress)
              newArtifacts = [...state.artifacts];
              newArtifacts[existing] = {
                ...newArtifacts[existing],
                code,
                progress,
                status,
              };
            } else {
              // New artifact
              newArtifacts = [
                ...state.artifacts,
                {
                  id: artifactId,
                  filename,
                  language,
                  code,
                  type: artType,
                  wrapper,
                  agent: wrapper,
                  timestamp: new Date(),
                  status,
                  progress,
                  componentName,
                },
              ];
            }

            return {
              artifacts: newArtifacts,
              // Auto-select the first artifact if none selected
              activeArtifactId: state.activeArtifactId ?? artifactId,
            };
          });
          break;
        }

        /* PM signals that the full project is ready (GitHub repo created) */
        case "PROJECT_READY": {
          set({
            projectGithubUrl: (payload.githubUrl as string) ?? (payload.url as string) ?? null,
            projectName: (payload.projectName as string) ?? null,
            projectRepoName: (payload.repoName as string) ?? null,
          });
          // Add a chat message informing the user
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-project-${Date.now()}`,
                author: "Griffin PM",
                avatar: "PM",
                content: `🎉 Project is ready! ${(payload.githubUrl as string) ?? "Check the Workstation for generated code."}`,
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        /* Status update from a wrapper */
        case "STATUS_UPDATE": {
          const wrapperId = env.src;
          if (wrapperId) {
            set((state) => {
              const existing = state.wrappers[wrapperId];
              if (!existing) return {};
              return {
                wrappers: {
                  ...state.wrappers,
                  [wrapperId]: {
                    ...existing,
                    status: (payload.status as WrapperStatus) ?? existing.status,
                    lastSeen: Date.now(),
                  },
                },
              };
            });
          }
          break;
        }

        /* Legacy specialist outputs — treat as agent messages */
        case "DESIGN_DRAFT":
        case "API_DRAFT":
        case "SCHEMA_DRAFT":
        case "AUDIT_REPORT":
        case "POLICY_RESULT": {
          set((state) => ({
            agentMessages: [
              ...state.agentMessages,
              {
                id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author: env.src ?? "Specialist",
                avatar: (env.src ?? "SP").slice(0, 2).toUpperCase(),
                content: (payload.summary as string) ?? (payload.text as string) ?? JSON.stringify(payload).slice(0, 300),
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
          break;
        }

        default:
          console.log("[orchestrator] unhandled EVENT kind:", kind, payload);
      }
      break;
    }

    /* ---- Catch-all for other envelope types (CHAT_RESPONSE at top level etc.) ---- */
    default: {
      // Some messages may arrive at top-level (not wrapped in EVENT)
      if (env.type === "CHAT_RESPONSE") {
        set((state) => ({
          chatMessages: [
            ...state.chatMessages,
            {
              id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              author: (payload.author as string) ?? "Griffin PM",
              avatar: "PM",
              content: (payload.text as string) ?? (payload.message as string) ?? "",
              timestamp: new Date(),
              isUser: false,
            },
          ],
        }));
      } else if (env.type === "AGENT_MESSAGE") {
        set((state) => ({
          agentMessages: [
            ...state.agentMessages,
            {
              id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              author: (payload.author as string) ?? env.src ?? "Agent",
              avatar: ((payload.author as string) ?? env.src ?? "AG").slice(0, 2).toUpperCase(),
              content: (payload.text as string) ?? (payload.message as string) ?? "",
              timestamp: new Date(),
              isUser: false,
            },
          ],
        }));
      } else {
        console.log("[orchestrator] unhandled envelope:", env.type, env);
      }
    }
  }
}

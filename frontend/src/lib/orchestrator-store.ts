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
  /** Optional routing channel derived from the author or office name. */
  channel?: string;
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

/** A single deployment pipeline step reported by the backend. */
export interface DeployStep {
  step: string;
  status: string;
  url?: string;
}

/** A single LLM call token usage record. */
export interface TokenUsageEntry {
  office: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_s: number;
  timestamp: number;
}

/** Per-office aggregated stats. */
export interface PerOfficeStat {
  office: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  totalLatency: number;
}

/** Aggregated cost summary derived from tokenUsageLog. */
export interface CostSummary {
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCostUsd: number;
  totalCalls: number;
  perOffice: PerOfficeStat[];
}

/* ------------------------------------------------------------------ */
/*  Envelope - mirrors backend/orchestrator/src/types.ts               */
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
  terminalLogs: string[];
  artifacts: CodeArtifact[];
  projectFiles: string[];
  activeArtifactId: string | null;
  projectGithubUrl: string | null;
  projectName: string | null;
  projectRepoName: string | null;
  tokenUsageLog: TokenUsageEntry[];
  costSummary: CostSummary;
  costMessages: string[];
  deploySteps: DeployStep[];

  connect: (orchestratorUrl: string) => void;
  disconnect: () => void;
  sendChatMessage: (text: string) => void;
  sendEnvelope: (envelope: Envelope) => void;
  sendUserCommand: (command: string) => void;
  setActiveArtifact: (id: string) => void;
  clearArtifacts: () => void;
  clearTerminal: () => void;
  clearCostData: () => void;
}

/* ------------------------------------------------------------------ */
/*  Singleton WebSocket bookkeeping (outside Zustand to avoid cycles)  */
/* ------------------------------------------------------------------ */

let _ws: WebSocket | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;

/** Recompute the cost summary from the full token usage log. */
function _recomputeCostSummary(log: TokenUsageEntry[]): CostSummary {
  let totalIn = 0;
  let totalOut = 0;
  let totalCost = 0;
  const perOfficeMap: Record<string, PerOfficeStat> = {};

  for (const entry of log) {
    totalIn += entry.input_tokens;
    totalOut += entry.output_tokens;
    totalCost += entry.cost_usd;

    // Derive short office name for grouping
    const officeKey = entry.office
      .replace(/[(\[].*[)\]]/g, "")
      .replace(/-retry/g, "")
      .trim()
      .split(" ")[0] || entry.office;

    if (!perOfficeMap[officeKey]) {
      perOfficeMap[officeKey] = {
        office: officeKey,
        calls: 0,
        inputTokens: 0,
        outputTokens: 0,
        costUsd: 0,
        totalLatency: 0,
      };
    }
    perOfficeMap[officeKey].calls += 1;
    perOfficeMap[officeKey].inputTokens += entry.input_tokens;
    perOfficeMap[officeKey].outputTokens += entry.output_tokens;
    perOfficeMap[officeKey].costUsd += entry.cost_usd;
    perOfficeMap[officeKey].totalLatency += entry.latency_s;
  }

  return {
    totalInputTokens: totalIn,
    totalOutputTokens: totalOut,
    totalCostUsd: Math.round(totalCost * 1e6) / 1e6,
    totalCalls: log.length,
    perOffice: Object.values(perOfficeMap).sort((a, b) => b.costUsd - a.costUsd),
  };
}

/**
 * Derive a routing channel from an author or office name.
 * Engineer offices (frontend/backend/database engineer) map to "engineering-core";
 * ui/frontend design maps to "frontend-design"; devops/security maps to "ops-security";
 * everything else falls back to "general".
 */
function deriveChannel(nameOrOffice: string): string {
  const s = (nameOrOffice ?? "").toLowerCase();
  if (s.includes("engineer") || s.includes("backend") || s.includes("database")) {
    return "engineering-core";
  }
  if (s.includes("ui") || s.includes("frontend")) {
    return "frontend-design";
  }
  if (s.includes("devops") || s.includes("security")) {
    return "ops-security";
  }
  return "general";
}

/**
 * Derive the artifact type from its filename, falling back to language.
 * Only real UI component files (.tsx / .jsx) are typed "component" so the
 * Workstation LivePreview renders them as React; every other file (.py, .css,
 * .md, .json, plain .js, etc.) is typed "code" so it is shown as source only
 * and never injected into the React preview iframe.
 */
function deriveArtifactType(filename: string, language: string): string {
  const name = (filename ?? "").toLowerCase();
  const lang = (language ?? "").toLowerCase();
  if (
    name.endsWith(".tsx") ||
    name.endsWith(".jsx") ||
    lang === "tsx" ||
    lang === "jsx"
  ) {
    return "component";
  }
  return "code";
}

/* ------------------------------------------------------------------ */
/*  Store implementation                                               */
/* ------------------------------------------------------------------ */

export const useOrchestratorStore = create<OrchestratorState>((set, get) => ({
  wrappers: {},
  connected: false,
  chatMessages: [],
  agentMessages: [],
  terminalLogs: [],
  artifacts: [],
  projectFiles: [],
  activeArtifactId: null,
  projectGithubUrl: null,
  projectName: null,
  projectRepoName: null,
  tokenUsageLog: [],
  costSummary: {
    totalInputTokens: 0,
    totalOutputTokens: 0,
    totalCostUsd: 0,
    totalCalls: 0,
    perOffice: [],
  },
  costMessages: [],
  deploySteps: [],

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
      projectFiles: [],
    });
  },

  clearTerminal() {
    set({ terminalLogs: [] });
  },

  clearCostData() {
    set({
      tokenUsageLog: [],
      costSummary: {
        totalInputTokens: 0,
        totalOutputTokens: 0,
        totalCostUsd: 0,
        totalCalls: 0,
        perOffice: [],
      },
      costMessages: [],
    });
  },

  /* ---- send a raw envelope ---- */

  sendEnvelope(envelope: Envelope) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify(envelope));
    }
  },

  /* ---- send a control command to the ML service ---- */

  sendUserCommand(command: string) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({ type: "user_command", command }));
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

    // 2) Send prompt directly to ML service
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({ type: 'prompt', data: text }));
    }
  },

  /* ---- connect to the orchestrator WebSocket ---- */

  connect(url: string) {
    // Prevent duplicate connections
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    // Avoid mixed-content blocking: when the page is served over https,
    // upgrade an insecure ws:// endpoint to wss:// before opening the socket.
    let target = url;
    if (
      typeof window !== "undefined" &&
      window.location.protocol === "https:" &&
      target.startsWith("ws://")
    ) {
      target = "wss://" + target.slice("ws://".length);
    }

    try {
      const ws = new WebSocket(target);
      _ws = ws;

      ws.addEventListener("open", () => {
        console.log("[ml-service] connected to", target);
        set({ connected: true });
      });

      ws.addEventListener("message", (event) => {
        let msg: { type: string; data: string; githubUrl?: string; projectName?: string };
        try {
          msg = JSON.parse(String(event.data));
        } catch {
          console.warn("[ml-service] invalid message", event.data);
          return;
        }

        // Handle progress updates
        if (msg.type === 'progress') {
          let logLine = msg.data;

          // Only show "ML Pipeline" as author for the starting message
          // Otherwise extract office name from content (e.g., "🏢 CEO OFFICE" -> "CEO OFFICE")
          let author = 'ML Pipeline';
          let avatar = 'ML';

          if (!logLine.includes('Starting ML pipeline for:')) {
            // Match an optional emoji prefix, an ALL CAPS office name, then a
            // separator (em dash, hyphen or colon) at start of line or after whitespace.
            const officeMatch = logLine.match(/^(?:[🏢⚡️✅⏳🔧🚀📁🔗📤📝❌⚠️])?\s*([A-Z][A-Z\s]*(?:OFFICE|DESIGN|API|SECURITY|CEO|PM|DEVOPS))\s*[\u2014\-:]\s*/) ||
              logLine.match(/(?:^|\s)([A-Z][A-Z\s]*(?:OFFICE|DESIGN|API|SECURITY|CEO|PM|DEVOPS))\s*[\u2014\-:]\s*/);

            if (officeMatch) {
              // Extract author from the matched pattern
              author = officeMatch[1].trim();
              avatar = author.slice(0, 2).toUpperCase();
              // Remove the prefix from the content to avoid repetition
              logLine = logLine.replace(officeMatch[0], '').trim();
            } else {
              // Fallback: look for bracketed names or any ALL_CAPS word
              const fallbackMatch = logLine.match(/\[([A-Z][A-Z_]+)\]/) ||
                logLine.match(/\b(CEO|PM|DEVOPS|DESIGN|API|SECURITY)\b/);
              if (fallbackMatch) {
                author = fallbackMatch[1].trim();
                avatar = author.slice(0, 2).toUpperCase();
              } else {
                // Default to System for other messages
                author = 'System';
                avatar = 'SY';
              }
            }
          }

          set((state) => ({
            agentMessages: [
              ...state.agentMessages,
              {
                id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                author,
                avatar,
                content: logLine,
                timestamp: new Date(),
                isUser: false,
                channel: deriveChannel(author),
              },
            ],
            terminalLogs: [...state.terminalLogs, msg.data], // Keep original in terminal
          }));
        }

        // Handle raw terminal output
        if (msg.type === 'terminal') {
          set((state) => ({
            terminalLogs: [...state.terminalLogs, msg.data],
          }));
        }

        // Handle file information
        if (msg.type === 'file') {
          const fileData = (msg as any).data as { filename: string; language: string; path: string };
          set((state) => ({
            projectFiles: [...state.projectFiles, fileData.filename],
          }));
        }

        // Handle per-call token usage (streamed from backend)
        if (msg.type === 'token_usage') {
          const entry = msg.data as unknown as TokenUsageEntry;
          if (entry && typeof entry.input_tokens === 'number') {
            const newEntry: TokenUsageEntry = {
              office: entry.office ?? 'unknown',
              input_tokens: entry.input_tokens,
              output_tokens: entry.output_tokens,
              cost_usd: entry.cost_usd,
              latency_s: entry.latency_s,
              timestamp: Date.now(),
            };
            set((state) => {
              const newLog = [...state.tokenUsageLog, newEntry];
              return {
                tokenUsageLog: newLog,
                costSummary: _recomputeCostSummary(newLog),
              };
            });
          }
        }

        // Handle cost optimizer text updates
        if (msg.type === 'cost_update') {
          set((state) => ({
            costMessages: [...state.costMessages, msg.data],
          }));
        }

        // Handle live office status updates -> Blueprint Canvas nodes
        if (msg.type === 'office_status') {
          const evt = msg.data as unknown as {
            office: string;
            name: string;
            status: string;
            dataType?: string;
          };
          if (evt && evt.office) {
            const valid: WrapperStatus[] = ["IDLE", "THINKING", "WORKING", "BLOCKED"];
            // THINKING/WORKING/IDLE/BLOCKED pass through unchanged; anything
            // unexpected falls back to WORKING.
            const status = (valid.includes(evt.status as WrapperStatus)
              ? evt.status
              : "WORKING") as WrapperStatus;
            const displayName = evt.name ?? evt.office;
            const channel = deriveChannel(displayName || evt.office);
            const statusLabel = status.charAt(0) + status.slice(1).toLowerCase();
            set((state) => ({
              wrappers: {
                ...state.wrappers,
                [evt.office]: {
                  id: evt.office,
                  type: evt.office,
                  status,
                  lastSeen: Date.now(),
                  meta: { name: displayName, type: evt.office, dataType: evt.dataType },
                },
              },
              agentMessages: [
                ...state.agentMessages,
                {
                  id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                  author: displayName,
                  avatar: displayName.slice(0, 2).toUpperCase(),
                  content: evt.dataType
                    ? `${statusLabel} on ${evt.dataType}`
                    : statusLabel,
                  timestamp: new Date(),
                  isUser: false,
                  channel,
                },
              ],
            }));
          }
        }

        // Handle a code artifact streamed from the pipeline -> Workstation
        if (msg.type === 'code_artifact') {
          const evt = msg.data as unknown as {
            filename: string;
            language?: string;
            code?: string;
            progress?: number;
            status?: string;
          };
          if (evt && evt.filename) {
            const artifactId = evt.filename;
            set((state) => {
              const existing = state.artifacts.findIndex((a) => a.id === artifactId);
              const record: CodeArtifact = {
                id: artifactId,
                filename: evt.filename,
                language: evt.language ?? "plaintext",
                code: evt.code ?? "",
                type: deriveArtifactType(evt.filename, evt.language ?? ""),
                wrapper: "pipeline",
                agent: "pipeline",
                timestamp: new Date(),
                status: "complete",
                progress: 100,
              };

              let newArtifacts: CodeArtifact[];
              if (existing >= 0) {
                newArtifacts = [...state.artifacts];
                newArtifacts[existing] = { ...newArtifacts[existing], ...record };
              } else {
                newArtifacts = [...state.artifacts, record];
              }

              return {
                artifacts: newArtifacts,
                activeArtifactId: state.activeArtifactId ?? artifactId,
              };
            });
          }
        }

        // Handle a deployment pipeline step (git_init/commit/push/build/deploy)
        if (msg.type === 'deploy_step') {
          const evt = msg.data as unknown as {
            step: string;
            status: string;
            url?: string;
          };
          if (evt && evt.step) {
            set((state) => {
              const idx = state.deploySteps.findIndex((s) => s.step === evt.step);
              const record: DeployStep = {
                step: evt.step,
                status: evt.status,
                url: evt.url,
              };

              let newSteps: DeployStep[];
              if (idx >= 0) {
                newSteps = [...state.deploySteps];
                newSteps[idx] = record;
              } else {
                newSteps = [...state.deploySteps, record];
              }

              return { deploySteps: newSteps };
            });
          }
        }

        // Handle completion
        if (msg.type === 'complete') {
          const files = (msg as any).files as string[] | undefined;
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}`,
                author: 'Griffin',
                avatar: 'GR',
                content: msg.data,
                timestamp: new Date(),
                isUser: false,
              },
            ],
            projectGithubUrl: msg.githubUrl || null,
            projectName: msg.projectName || null,
            projectFiles: files || state.projectFiles,
          }));
        }

        // Handle errors
        if (msg.type === 'error') {
          set((state) => ({
            chatMessages: [
              ...state.chatMessages,
              {
                id: `msg-${Date.now()}`,
                author: 'Griffin',
                avatar: 'GR',
                content: msg.data,
                timestamp: new Date(),
                isUser: false,
              },
            ],
          }));
        }
      });

      ws.addEventListener("close", () => {
        console.log("[ml-service] disconnected");
        cleanup();
        set({ connected: false });

        // Attempt to reconnect after 3 seconds
        if (_reconnectTimer) clearTimeout(_reconnectTimer);
        _reconnectTimer = setTimeout(() => {
          console.log("[ml-service] attempting reconnect…");
          get().connect(url);
        }, 3000);
      });

      ws.addEventListener("error", (err) => {
        console.error("[ml-service] WebSocket error", err);
      });
    } catch (err) {
      console.error("[ml-service] failed to connect", err);
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
            src: "ui-observer",
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
  _ws = null;
}

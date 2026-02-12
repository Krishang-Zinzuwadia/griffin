import { create } from "zustand";

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
  setActiveArtifact: (id: string) => void;
  clearArtifacts: () => void;
}

export const useOrchestratorStore = create<OrchestratorState>((set) => ({
  wrappers: {},
  connected: false, // Connection disabled
  chatMessages: [],
  agentMessages: [],
  artifacts: [],
  activeArtifactId: null,
  projectGithubUrl: null,
  projectName: null,
  projectRepoName: null,

  setActiveArtifact(id: string) {
    set({ activeArtifactId: id });
  },

  clearArtifacts() {
    set({ artifacts: [], activeArtifactId: null, projectGithubUrl: null, projectName: null, projectRepoName: null });
  },

  sendChatMessage(text: string) {
    // Echo locally so the UI feels responsive, but do not send to backend
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
  },

  connect(_url: string) {
    console.log("Orchestrator connection disabled.");
  },

  disconnect() {
    set({ connected: false });
  },
}));

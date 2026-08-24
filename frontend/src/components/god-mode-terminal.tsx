"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Terminal as TerminalIcon,
  Zap,
  AlertTriangle,
  UserPlus,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useOrchestratorStore } from "@/lib/orchestrator-store";

interface TerminalLine {
  id: string;
  type: "input" | "output" | "error" | "success" | "system";
  content: string;
  timestamp: Date;
}

const initialLines: TerminalLine[] = [
  {
    id: "1",
    type: "system",
    content: "Griffin God Mode Terminal v3.0.0",
    timestamp: new Date(),
  },
  {
    id: "2",
    type: "system",
    content: "Type /help for available commands",
    timestamp: new Date(),
  },
];

/** Quick command buttons rendered under the input. */
const quickCommands: { label: string; value: string }[] = [
  { label: "/help", value: "/help" },
  { label: "/status", value: "/status" },
  { label: "/deploy --force", value: "/deploy --force" },
  { label: "/evacuate", value: "/evacuate" },
  { label: "/hire", value: "/hire " },
];

const lineColors: Record<TerminalLine["type"], string> = {
  input: "text-foreground",
  output: "text-primary",
  error: "text-destructive",
  success: "text-accent",
  system: "text-secondary",
};

const lineIcons: Record<TerminalLine["type"], LucideIcon | null> = {
  input: ChevronRight,
  output: null,
  error: AlertTriangle,
  success: Zap,
  system: TerminalIcon,
};

/** Build a terminal line with a unique id for use as a React key. */
function createLine(type: TerminalLine["type"], content: string): TerminalLine {
  return {
    id: `${type}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    type,
    content,
    timestamp: new Date(),
  };
}

export function GodModeTerminal() {
  const {
    connected,
    wrappers,
    artifacts,
    costSummary,
    deploySteps,
    terminalLogs,
    clearTerminal,
    sendUserCommand,
  } = useOrchestratorStore();
  const [lines, setLines] = useState<TerminalLine[]>(initialLines);
  const [inputValue, setInputValue] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Function to detect and linkify URLs
  const linkifyContent = (content: string) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = content.split(urlRegex);

    return parts.map((part, index) => {
      if (urlRegex.test(part)) {
        return (
          <a
            key={index}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 underline cursor-pointer"
            onClick={(e) => e.stopPropagation()}
          >
            {part}
          </a>
        );
      }
      return part;
    });
  };

  // Merge terminal logs from ML pipeline with local command output
  const allLines = [
    ...lines,
    ...terminalLogs.map((log, idx) => ({
      id: `ml-${idx}`,
      type: (log.includes('[ERROR]') ? 'error' : 'output') as TerminalLine['type'],
      content: log,
      timestamp: new Date(),
    })),
  ];

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allLines.length]);

  const executeCommand = (cmd: string) => {
    const raw = cmd.trim();
    if (!raw) return;

    // Normalise case and collapse internal whitespace for command matching.
    const normalized = raw.toLowerCase().replace(/\s+/g, " ");

    // Echo the typed line and record it in history.
    setLines((prev) => [...prev, createLine("input", raw)]);
    setHistory((prev) => [...prev, raw]);
    setHistoryIndex(-1);

    const appendLines = (newLines: TerminalLine[]) => {
      setLines((prev) => [...prev, ...newLines]);
    };

    // /clear: wipe both the local view and the live ML log stream.
    if (normalized === "/clear") {
      setLines([]);
      clearTerminal();
      return;
    }

    // /help: list the real commands.
    if (normalized === "/help") {
      appendLines([
        createLine("output", "Available commands:"),
        createLine("output", "  /status            Show live system status"),
        createLine("output", "  /deploy --force    Force deploy, bypassing gates"),
        createLine("output", "  /evacuate          Kill the running pipeline and clear the log"),
        createLine("output", "  /hire [role]       Request a custom agent from the orchestrator"),
        createLine("output", "  /clear             Clear the terminal"),
        createLine("output", "  /help              Show this help"),
      ]);
      return;
    }

    // /status: print real live values pulled from the store.
    if (normalized === "/status") {
      const officeCount = Object.keys(wrappers).length;
      const deploySummary = (() => {
        if (deploySteps.length === 0) return "no steps reported";
        const last = deploySteps[deploySteps.length - 1];
        const plural = deploySteps.length === 1 ? "" : "s";
        return `${deploySteps.length} step${plural}, latest ${last.step} (${last.status})`;
      })();

      appendLines([
        createLine("output", "System status:"),
        createLine(
          connected ? "success" : "error",
          `  Connection: ${connected ? "connected" : "disconnected"}`,
        ),
        createLine("output", `  Active offices: ${officeCount}`),
        createLine("output", `  Artifacts: ${artifacts.length}`),
        createLine("output", `  Total cost: $${costSummary.totalCostUsd.toFixed(4)}`),
        createLine("output", `  Deploy: ${deploySummary}`),
      ]);
      return;
    }

    // /evacuate: kill the running pipeline and clear the live log.
    if (normalized === "/evacuate") {
      sendUserCommand("/evacuate");
      clearTerminal();
      appendLines([
        connected
          ? createLine(
              "success",
              "Evacuation signal sent to ML service. Running pipeline terminated; live log cleared.",
            )
          : createLine(
              "error",
              "No active ML connection. Live log cleared, but the evacuation signal was not delivered.",
            ),
      ]);
      return;
    }

    // /deploy [--force]: only --force is a real backend action (arms the force flag).
    if (normalized === "/deploy" || normalized.startsWith("/deploy ")) {
      if (!normalized.includes("--force")) {
        appendLines([
          createLine(
            "output",
            "Deployment runs automatically after the pipeline. Use /deploy --force to override the gates.",
          ),
        ]);
        return;
      }
      sendUserCommand("/deploy --force");
      appendLines([
        connected
          ? createLine("success", "Force deploy armed. Sent /deploy --force to the ML service.")
          : createLine("error", "No active ML connection. /deploy --force could not be delivered."),
      ]);
      return;
    }

    // /hire [role]: no dedicated hire endpoint, so forward the request over the socket.
    if (normalized === "/hire" || normalized.startsWith("/hire ")) {
      const role = raw.slice("/hire".length).trim();
      if (!role) {
        appendLines([
          createLine("output", "Usage: /hire [role], for example /hire Security Auditor"),
        ]);
        return;
      }
      sendUserCommand(`/hire ${role}`);
      appendLines([
        connected
          ? createLine("success", `Hire request for "${role}" dispatched to the orchestrator.`)
          : createLine(
              "error",
              `No active ML connection. Hire request for "${role}" was not delivered.`,
            ),
      ]);
      return;
    }

    // Any other slash command is unknown.
    if (normalized.startsWith("/")) {
      appendLines([createLine("error", `Unknown command: ${raw}`)]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      executeCommand(inputValue);
      setInputValue("");
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInputValue(history[history.length - 1 - newIndex]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInputValue(history[history.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInputValue("");
      }
    }
  };

  return (
    <div className="h-full flex flex-col bg-background text-foreground text-sm" style={{ fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace' }}>
      {/* Header */}
      <div className="h-12 border-b border-border/20 flex items-center justify-between px-4 bg-card/5">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-4 h-4 text-secondary" />
          <span className="font-semibold">God Mode Terminal</span>
        </div>
        <Badge
          variant="outline"
          className="text-xs border-destructive/30 text-destructive"
        >
          ROOT ACCESS
        </Badge>
      </div>

      {/* Output Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2 min-h-0">
        {allLines.map((line) => {
          const Icon = lineIcons[line.type];

          // Check if line contains folder structure or box drawing characters
          const hasBoxChars = /[─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬]/.test(line.content);
          const isStructureLine = /^[\s│├└─]+/.test(line.content) ||
                                  line.content.includes('├──') ||
                                  line.content.includes('└──') ||
                                  line.content.includes('│') ||
                                  hasBoxChars;

          return (
            <motion.div
              key={line.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className={cn("flex items-start gap-2", lineColors[line.type])}
            >
              {Icon && <Icon className="w-4 h-4 mt-0.5 shrink-0" />}
              {isStructureLine ? (
                <pre className="whitespace-pre font-mono text-sm m-0 p-0" style={{ fontFamily: 'inherit' }}>{line.content}</pre>
              ) : (
                <span className="break-all">{linkifyContent(line.content)}</span>
              )}
            </motion.div>
          );
        })}
        <div ref={scrollRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border/20 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-accent">root@griffin</span>
          <span className="text-muted-foreground">:</span>
          <span className="text-primary">~</span>
          <span className="text-muted-foreground">$</span>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent outline-none text-foreground ml-2"
            placeholder="Enter command..."
            autoFocus
          />
        </div>
      </div>

      {/* Quick Commands */}
      <div className="px-4 pb-4 flex gap-2 flex-wrap flex-shrink-0">
        <button
          onClick={() => {
            setLines([]);
            clearTerminal();
          }}
          className="px-2 py-1 text-xs rounded bg-muted/20 hover:bg-muted/30 transition-colors"
        >
          Clear All
        </button>
        {quickCommands.map((cmd) => (
          <button
            key={cmd.label}
            onClick={() => {
              setInputValue(cmd.value);
              inputRef.current?.focus();
            }}
            className="px-2 py-1 text-xs rounded bg-muted/20 hover:bg-muted/30 transition-colors"
          >
            {cmd.label}
          </button>
        ))}
      </div>
    </div>
  );
}

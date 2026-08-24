"use client";

import {
  Fragment,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Hash,
  Code2,
  Workflow,
  ShieldCheck,
  Eye,
  Radio,
  FileJson,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  useOrchestratorStore,
  type ChatMessage,
} from "@/lib/orchestrator-store";

/* ------------------------------------------------------------------ */
/*  Channels (CHAT-01)                                                 */
/* ------------------------------------------------------------------ */

/** Channel ids mirror the `channel` field the store stamps onto messages. */
type ChannelId =
  | "general"
  | "engineering-core"
  | "frontend-design"
  | "ops-security";

interface ChannelDef {
  id: ChannelId;
  label: string;
  description: string;
  icon: LucideIcon;
}

/** The four auto-generated channels. Ids match the store `channel` values. */
const CHANNELS: ChannelDef[] = [
  {
    id: "general",
    label: "general",
    description: "Project chat with Griffin",
    icon: Hash,
  },
  {
    id: "engineering-core",
    label: "engineering-core",
    description: "Backend, database and core engineering",
    icon: Code2,
  },
  {
    id: "frontend-design",
    label: "frontend-design",
    description: "UI, frontend and design",
    icon: Workflow,
  },
  {
    id: "ops-security",
    label: "ops-security",
    description: "DevOps and security",
    icon: ShieldCheck,
  },
];

/** Route a store message into one channel; anything unknown lands in #general. */
function channelOf(message: ChatMessage): ChannelId {
  switch (message.channel) {
    case "engineering-core":
    case "frontend-design":
    case "ops-security":
      return message.channel;
    default:
      return "general";
  }
}

/* ------------------------------------------------------------------ */
/*  Rich media rendering (CHAT-03)                                     */
/* ------------------------------------------------------------------ */

/** Parse a string as a JSON object or array. Returns null when it is not JSON. */
function tryParseJson(raw: string): unknown {
  const trimmed = raw.trim();
  if (!trimmed || (trimmed[0] !== "{" && trimmed[0] !== "[")) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

const CODE_TOKEN =
  /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|\b(const|let|var|function|return|import|from|export|default|if|else|for|while|class|new|async|await|def|print|type|interface|extends|implements|public|private|protected|null|undefined|true|false|None|True|False)\b|\b(\d+(?:\.\d+)?)\b/g;

/** Dependency-free syntax tint returning React nodes (never innerHTML, so XSS safe). */
function highlightCode(code: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  let match: RegExpExecArray | null;
  CODE_TOKEN.lastIndex = 0;

  while ((match = CODE_TOKEN.exec(code)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(code.slice(lastIndex, match.index));
    }
    const [text, comment, str, keyword, num] = match;
    let className = "";
    if (comment) className = "italic text-emerald-500/70";
    else if (str) className = "text-amber-400";
    else if (keyword) className = "text-sky-400";
    else if (num) className = "text-fuchsia-400";
    nodes.push(
      <span key={key++} className={className}>
        {text}
      </span>,
    );
    lastIndex = match.index + text.length;
    if (CODE_TOKEN.lastIndex === match.index) CODE_TOKEN.lastIndex++;
  }
  if (lastIndex < code.length) nodes.push(code.slice(lastIndex));
  return nodes;
}

/** A fenced code block shown in a monospace, syntax-tinted panel. */
function CodeBlock({ code, lang }: { code: string; lang: string }) {
  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-border/60 bg-zinc-950/70">
      <div className="flex items-center gap-2 border-b border-border/60 px-3 py-1.5">
        <Code2 className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {lang || "code"}
        </span>
      </div>
      <pre className="overflow-x-auto px-3 py-2.5 text-xs leading-relaxed">
        <code className="font-mono">{highlightCode(code)}</code>
      </pre>
    </div>
  );
}

/** A JSON payload shown in a collapsible, pretty-printed block. */
function JsonBlock({ value }: { value: unknown }) {
  const pretty = JSON.stringify(value, null, 2);
  const size = Array.isArray(value)
    ? `${value.length} items`
    : `${Object.keys(value as Record<string, unknown>).length} keys`;

  return (
    <details className="group mt-2 overflow-hidden rounded-lg border border-border/60 bg-zinc-950/70">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground">
        <FileJson className="h-3.5 w-3.5" />
        <span className="font-medium">JSON payload</span>
        <span className="text-[10px] opacity-70">{size}</span>
        <ChevronRight className="ml-auto h-3.5 w-3.5 transition-transform group-open:rotate-90" />
      </summary>
      <pre className="overflow-x-auto border-t border-border/60 px-3 py-2.5 text-xs leading-relaxed">
        <code className="font-mono">{highlightCode(pretty)}</code>
      </pre>
    </details>
  );
}

/** Render a non-fenced run of text: whole-run JSON collapses, otherwise a paragraph. */
function renderText(text: string): ReactNode[] {
  if (!text.trim()) return [];
  const parsed = tryParseJson(text);
  if (parsed !== null) return [<JsonBlock value={parsed} />];
  return [
    <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
      {text.trim()}
    </p>,
  ];
}

const FENCE = /```([\w-]*)\n?([\s\S]*?)```/g;

/** Split message content into text, fenced code, and JSON blocks. */
function MessageContent({ content }: { content: string }) {
  const blocks: ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  FENCE.lastIndex = 0;

  while ((match = FENCE.exec(content)) !== null) {
    if (match.index > cursor) {
      blocks.push(...renderText(content.slice(cursor, match.index)));
    }
    const lang = match[1] ?? "";
    const body = match[2].replace(/\n$/, "");
    const parsed = tryParseJson(body);
    if (parsed !== null) {
      blocks.push(<JsonBlock value={parsed} />);
    } else {
      blocks.push(<CodeBlock code={body} lang={lang} />);
    }
    cursor = match.index + match[0].length;
  }
  if (cursor < content.length) {
    blocks.push(...renderText(content.slice(cursor)));
  }
  if (blocks.length === 0) {
    blocks.push(...renderText(content));
  }

  return (
    <div className="space-y-1">
      {blocks.map((block, index) => (
        <Fragment key={index}>{block}</Fragment>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Communication Hub                                                  */
/* ------------------------------------------------------------------ */

const EMPTY_COUNTS: Record<ChannelId, number> = {
  "general": 0,
  "engineering-core": 0,
  "frontend-design": 0,
  "ops-security": 0,
};

const EMPTY_FLAGS: Record<ChannelId, boolean> = {
  "general": false,
  "engineering-core": false,
  "frontend-design": false,
  "ops-security": false,
};

export function CommunicationHub() {
  const chatMessages = useOrchestratorStore((s) => s.chatMessages);
  const agentMessages = useOrchestratorStore((s) => s.agentMessages);
  const sendChatMessage = useOrchestratorStore((s) => s.sendChatMessage);
  const connected = useOrchestratorStore((s) => s.connected);
  const connect = useOrchestratorStore((s) => s.connect);

  const [activeChannel, setActiveChannel] = useState<ChannelId>("general");
  const [inputValue, setInputValue] = useState("");
  const [hijacked, setHijacked] = useState<Record<ChannelId, boolean>>(EMPTY_FLAGS);
  const [seen, setSeen] = useState<Record<ChannelId, number>>(EMPTY_COUNTS);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-connect. The store de-dupes, so calling this from several views is safe.
  useEffect(() => {
    if (!connected) {
      connect(process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "ws://localhost:9100");
    }
  }, [connected, connect]);

  // Group every store message into exactly one channel, ordered by time.
  const messagesByChannel = useMemo(() => {
    const map: Record<ChannelId, ChatMessage[]> = {
      "general": [],
      "engineering-core": [],
      "frontend-design": [],
      "ops-security": [],
    };
    const all = [...agentMessages, ...chatMessages].sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );
    for (const message of all) {
      map[channelOf(message)].push(message);
    }
    return map;
  }, [agentMessages, chatMessages]);

  const activeMessages = messagesByChannel[activeChannel];
  const activeCount = activeMessages.length;

  // The channel the spectator is currently watching counts as read.
  useEffect(() => {
    setSeen((prev) =>
      prev[activeChannel] === activeCount
        ? prev
        : { ...prev, [activeChannel]: activeCount },
    );
  }, [activeChannel, activeCount]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeCount, activeChannel]);

  const isHijacked = hijacked[activeChannel];
  const activeDef =
    CHANNELS.find((channel) => channel.id === activeChannel) ?? CHANNELS[0];

  const toggleHijack = () => {
    setHijacked((prev) => ({ ...prev, [activeChannel]: !prev[activeChannel] }));
  };

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || !isHijacked) return;
    sendChatMessage(text);
    setInputValue("");
  };

  return (
    <div className="flex h-full overflow-hidden bg-background">
      {/* Channel sidebar */}
      <div className="w-64 flex-shrink-0 border-r border-border bg-card/50">
        <div className="p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Channels
          </h2>
        </div>
        <nav className="space-y-0.5 px-2">
          {CHANNELS.map((channel) => {
            const Icon = channel.icon;
            const total = messagesByChannel[channel.id].length;
            const unread = Math.max(0, total - seen[channel.id]);
            const isActive = channel.id === activeChannel;

            return (
              <button
                key={channel.id}
                onClick={() => setActiveChannel(channel.id)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="flex-1 truncate text-left">
                  #{channel.label}
                </span>
                {unread > 0 ? (
                  <Badge
                    variant="default"
                    className="h-5 min-w-[1.25rem] justify-center px-1.5 text-xs"
                  >
                    {unread}
                  </Badge>
                ) : (
                  total > 0 && (
                    <span className="text-xs tabular-nums text-muted-foreground/60">
                      {total}
                    </span>
                  )
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Active channel */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Header */}
        <div className="flex h-14 flex-shrink-0 items-center justify-between gap-3 border-b border-border px-4">
          <div className="flex min-w-0 items-center gap-2">
            <Hash className="h-5 w-5 shrink-0 text-muted-foreground" />
            <span className="truncate font-semibold">{activeDef.label}</span>
            <span className="hidden truncate text-xs text-muted-foreground lg:inline">
              {activeDef.description}
            </span>
          </div>
          <div className="flex flex-shrink-0 items-center gap-2">
            {connected ? (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Live
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs text-red-400">
                <span className="h-1.5 w-1.5 rounded-full bg-red-400" /> Offline
              </span>
            )}
            <Badge
              variant={isHijacked ? "default" : "secondary"}
              className="gap-1 text-xs"
            >
              {isHijacked ? (
                <Radio className="h-3 w-3" />
              ) : (
                <Eye className="h-3 w-3" />
              )}
              {isHijacked ? "Hijacked" : "Spectator"}
            </Badge>
            <Button
              variant={isHijacked ? "default" : "outline"}
              size="sm"
              className="gap-1.5"
              onClick={toggleHijack}
            >
              <Radio className="h-3.5 w-3.5" />
              {isHijacked ? "Release channel" : "Hijack channel"}
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          {activeMessages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-sm text-muted-foreground">
              <Hash className="mb-2 h-8 w-8 opacity-40" />
              <p>No messages in #{activeDef.label} yet.</p>
              <p className="mt-1 text-xs opacity-60">
                Agent chatter routed to this channel will appear here.
              </p>
            </div>
          )}

          <AnimatePresence mode="popLayout">
            {activeMessages.map((message, index) => {
              const showAvatar =
                index === 0 ||
                activeMessages[index - 1].author !== message.author;

              return (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={cn("flex gap-3", !showAvatar && "pl-[52px]")}
                >
                  {showAvatar && (
                    <Avatar className="h-10 w-10 shrink-0">
                      <AvatarFallback
                        className={cn(
                          "text-xs font-medium",
                          message.isUser
                            ? "bg-muted"
                            : "bg-gradient-to-br from-gray-200 to-gray-400 text-black",
                        )}
                      >
                        {message.avatar}
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div className="min-w-0 flex-1">
                    {showAvatar && (
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-sm font-semibold">
                          {message.author}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(message.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                        {!message.isUser && (
                          <Badge
                            variant="outline"
                            className="h-4 px-1 text-[10px]"
                          >
                            AI
                          </Badge>
                        )}
                      </div>
                    )}
                    <MessageContent content={message.content} />
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
          <div ref={scrollRef} />
        </div>

        {/* Input (CHAT-02) */}
        <div className="flex-shrink-0 border-t border-border p-4">
          <div className="mb-2 flex items-center gap-1.5 text-xs">
            {isHijacked ? (
              <span className="flex items-center gap-1.5 text-primary">
                <Radio className="h-3.5 w-3.5" />
                Hijack active. Messages you send route to Griffin, the same as the
                main chat.
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <Eye className="h-3.5 w-3.5" />
                Spectator mode. Hijack #{activeDef.label} to post into the stream.
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handleSend()}
              disabled={!isHijacked}
              placeholder={
                isHijacked
                  ? `Message #${activeDef.label}...`
                  : "Spectator mode, hijack the channel to send"
              }
              className="flex-1"
            />
            <Button
              onClick={handleSend}
              size="icon"
              disabled={!isHijacked || !inputValue.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

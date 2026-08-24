"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import Editor from "@monaco-editor/react";
import {
  FileCode,
  Eye,
  Database,
  Box,
  Play,
  Pause,
  RotateCcw,
  Download,
  Copy,
  Check,
  ExternalLink,
  GitBranch,
  type LucideIcon,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  useOrchestratorStore,
  type CodeArtifact,
} from "@/lib/orchestrator-store";


const typeIcons: Record<string, LucideIcon> = {
  component: Eye,
  "api-route": FileCode,
  schema: Database,
  style: Box,
};

const typeColors: Record<string, string> = {
  component: "text-blue-400",
  "api-route": "text-emerald-400",
  schema: "text-amber-400",
  style: "text-purple-400",
};

/** Map a loosely typed artifact language onto a Monaco language id. */
function toMonacoLanguage(language: string): string {
  const lang = (language ?? "").trim().toLowerCase();
  const map: Record<string, string> = {
    ts: "typescript",
    typescript: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    javascript: "javascript",
    mjs: "javascript",
    cjs: "javascript",
    py: "python",
    python: "python",
    rb: "ruby",
    ruby: "ruby",
    go: "go",
    rs: "rust",
    rust: "rust",
    java: "java",
    c: "c",
    cpp: "cpp",
    cs: "csharp",
    php: "php",
    json: "json",
    html: "html",
    htm: "html",
    css: "css",
    scss: "scss",
    less: "less",
    md: "markdown",
    markdown: "markdown",
    yml: "yaml",
    yaml: "yaml",
    xml: "xml",
    sql: "sql",
    sh: "shell",
    bash: "shell",
    shell: "shell",
    dockerfile: "dockerfile",
  };
  return map[lang] ?? (lang || "plaintext");
}

/** Read only Monaco options shared by the artifact source view. */
const MONACO_OPTIONS = {
  readOnly: true,
  domReadOnly: true,
  automaticLayout: true,
  minimap: { enabled: false },
  fontSize: 13,
  lineNumbers: "on",
  scrollBeyondLastLine: false,
  smoothScrolling: true,
  wordWrap: "on",
  renderLineHighlight: "none",
  padding: { top: 12, bottom: 12 },
  scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
  fontLigatures: true,
} as const;

/**
 * Progressively reveal `code` character by character over a short, bounded
 * duration whenever the active artifact changes, producing a ghost typing
 * effect that settles on the full content.
 */
function useGhostReveal(code: string, artifactId: string) {
  const [state, setState] = useState<{ revealed: number; done: boolean }>({
    revealed: 0,
    done: false,
  });
  const codeRef = useRef(code);
  codeRef.current = code;
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    setState({ revealed: 0, done: false });
    const start = performance.now();

    const step = (now: number) => {
      const total = codeRef.current.length;
      const duration = Math.min(1200, Math.max(350, total * 2.5));
      const t = total === 0 ? 1 : Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      if (t < 1) {
        setState({ revealed: Math.floor(total * eased), done: false });
        frameRef.current = requestAnimationFrame(step);
      } else {
        setState({ revealed: total, done: true });
      }
    };

    frameRef.current = requestAnimationFrame(step);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, [artifactId]);

  return state;
}

/** Monaco based, read only source viewer with a ghost typing reveal. */
function MonacoCodeView({ artifact }: { artifact: CodeArtifact }) {
  const { revealed, done } = useGhostReveal(artifact.code, artifact.id);
  const [copied, setCopied] = useState(false);

  const value = done ? artifact.code : artifact.code.slice(0, revealed);
  const streaming = !done || artifact.progress < 100;
  const percent = done
    ? artifact.progress
    : Math.floor((revealed / Math.max(1, artifact.code.length)) * 100);

  function handleCopy() {
    navigator.clipboard.writeText(artifact.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-lg border border-border bg-[#1e1e1e]">
      <div className="min-h-0 flex-1">
        <Editor
          height="100%"
          theme="vs-dark"
          path={artifact.filename}
          language={toMonacoLanguage(artifact.language)}
          value={value}
          options={MONACO_OPTIONS}
          loading={
            <span className="text-sm text-muted-foreground">Loading editor…</span>
          }
        />
      </div>

      <div className="flex h-8 items-center gap-4 border-t border-border bg-card px-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          {streaming ? (
            <>
              <motion.span
                animate={{ opacity: [1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity }}
                className="w-2 h-2 rounded-full bg-emerald-400"
              />
              Typing…
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Complete
            </>
          )}
        </span>
        <Separator orientation="vertical" className="h-4" />
        <span>{percent}%</span>
        <div className="flex-1" />
        <button
          onClick={handleCopy}
          className="hover:text-foreground transition-colors flex items-center gap-1"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
        <Separator orientation="vertical" className="h-4" />
        <span>{artifact.language}</span>
        <span>UTF-8</span>
      </div>
    </div>
  );
}


/**
 * Build a self-contained HTML document that renders a React component
 * using CDN-loaded React + Babel + Tailwind.
 */
function buildPreviewHtml(code: string, componentName?: string): string {
  const exportDefault = componentName ?? "App";

  // Strip `export default` so Babel can handle it as a plain function declaration
  const cleaned = code
    .replace(/export\s+default\s+function\s+/, "function ")
    .replace(/export\s+default\s+/, "");

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.tailwindcss.com"><\/script>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"><\/script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"><\/script>
  <script crossorigin src="https://unpkg.com/@babel/standalone/babel.min.js"><\/script>
  <style>
    body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: #0a0a0a; color: #fafafa; }
    #root { min-height: 100vh; }
    .error-banner { background: #7f1d1d; color: #fca5a5; padding: 1rem; font-family: monospace; white-space: pre-wrap; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" data-type="module">
    try {
      ${cleaned}
      const root = ReactDOM.createRoot(document.getElementById('root'));
      root.render(React.createElement(${exportDefault}));
    } catch (err) {
      document.getElementById('root').innerHTML =
        '<div class="error-banner">Render Error:\\n' + err.message + '</div>';
    }
  <\/script>
</body>
</html>`;
}

function LivePreview({ artifact }: { artifact: CodeArtifact | null }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!artifact || artifact.type !== "component" || artifact.progress < 100) return;
    setError(null);

    try {
      const html = buildPreviewHtml(artifact.code, artifact.componentName);
      const blob = new Blob([html], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      if (iframeRef.current) {
        iframeRef.current.src = url;
      }
      return () => URL.revokeObjectURL(url);
    } catch (err) {
      setError(String(err));
    }
  }, [artifact?.id, artifact?.progress, artifact?.code, artifact?.componentName, artifact?.type]);

  if (!artifact) {
    return (
      <div className="h-full bg-muted/30 rounded-lg flex items-center justify-center text-muted-foreground">
        No component to preview yet. Send a request to generate code.
      </div>
    );
  }

  if (artifact.type !== "component") {
    return (
      <div className="h-full bg-muted/30 rounded-lg flex flex-col items-center justify-center text-muted-foreground gap-2">
        <FileCode className="w-8 h-8" />
        <span>Preview is available for React components only.</span>
        <span className="text-xs text-muted-foreground/60">
          This is a {artifact.type} artifact ({artifact.language}).
        </span>
      </div>
    );
  }

  if (artifact.progress < 100) {
    return (
      <div className="h-full bg-muted/30 rounded-lg flex items-center justify-center text-muted-foreground">
        <motion.span
          animate={{ opacity: [1, 0.4] }}
          transition={{ duration: 1, repeat: Infinity }}
        >
          Generating component… {artifact.progress}%
        </motion.span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full bg-red-950/30 rounded-lg p-4 text-red-400 font-mono text-sm overflow-auto">
        {error}
      </div>
    );
  }

  return (
    <iframe
      ref={iframeRef}
      title="Live Preview"
      sandbox="allow-scripts"
      className="w-full h-full rounded-lg border border-border bg-black"
    />
  );
}
export function Workstation() {
  const artifacts = useOrchestratorStore((s) => s.artifacts);
  const activeArtifactId = useOrchestratorStore((s) => s.activeArtifactId);
  const setActiveArtifact = useOrchestratorStore((s) => s.setActiveArtifact);
  const clearArtifacts = useOrchestratorStore((s) => s.clearArtifacts);
  const projectGithubUrl = useOrchestratorStore((s) => s.projectGithubUrl);
  const projectRepoName = useOrchestratorStore((s) => s.projectRepoName);

  const [isPlaying, setIsPlaying] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("code");

  const activeArtifact = artifacts.find((a) => a.id === activeArtifactId) ?? null;

  // Auto-switch to preview tab when a component finishes streaming
  useEffect(() => {
    if (activeArtifact?.type === "component" && activeArtifact.progress >= 100) {
      setActiveTab("preview");
    }
  }, [activeArtifact?.progress, activeArtifact?.type]);

  /** Download the active artifact code as a file. */
  function handleDownload() {
    if (!activeArtifact) return;
    const blob = new Blob([activeArtifact.code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = activeArtifact.filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <h2 className="font-semibold">Workstation</h2>
          <Badge variant="secondary" className="text-xs">
            {artifacts.length === 0
              ? "Awaiting code"
              : `${artifacts.length} artifact${artifacts.length > 1 ? "s" : ""}`}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsPlaying(!isPlaying)}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 mr-2" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            {isPlaying ? "Pause" : "Resume"}
          </Button>
          <Button variant="outline" size="icon" onClick={clearArtifacts} title="Clear all">
            <RotateCcw className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleDownload}
            disabled={!activeArtifact}
            title="Download"
          >
            <Download className="w-4 h-4" />
          </Button>
          {projectGithubUrl && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(projectGithubUrl, '_blank')}
              className="gap-2 text-emerald-400 border-emerald-400/30 hover:bg-emerald-400/10"
            >
              <GitBranch className="w-4 h-4" />
              <span className="hidden sm:inline">{projectRepoName ?? 'GitHub'}</span>
              <ExternalLink className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar: artifact list */}
        <div className="w-64 border-r border-border bg-card/50 flex flex-col">
          <div className="p-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Generated Files
            </h3>
          </div>
          {artifacts.length === 0 ? (
            <div className="flex-1 flex items-center justify-center px-4 text-center text-xs text-muted-foreground/60">
              Send a message in Chat to start generating code artifacts.
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto px-2 space-y-1">
              {artifacts.map((art) => {
                const Icon = typeIcons[art.type] ?? FileCode;
                const color = typeColors[art.type] ?? "text-gray-400";
                const isActive = activeArtifactId === art.id;

                return (
                  <button
                    key={art.id}
                    onClick={() => setActiveArtifact(art.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    )}
                  >
                    <Icon className={cn("w-4 h-4 shrink-0", color)} />
                    <span className="flex-1 text-left truncate">{art.filename}</span>
                    {art.status === "streaming" && (
                      <motion.span
                        animate={{ opacity: [1, 0.5] }}
                        transition={{ duration: 1, repeat: Infinity }}
                        className="w-2 h-2 rounded-full bg-emerald-400 shrink-0"
                      />
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Main editor / preview area */}
        <div className="flex-1 p-4">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
            <TabsList className="w-fit">
              <TabsTrigger value="code">Code</TabsTrigger>
              <TabsTrigger value="preview">Preview</TabsTrigger>
            </TabsList>

            <TabsContent value="code" className="flex-1 mt-4">
              {activeArtifact ? (
                <MonacoCodeView key={activeArtifact.id} artifact={activeArtifact} />
              ) : (
                <div className="h-full bg-muted/30 rounded-lg flex items-center justify-center text-muted-foreground">
                  Select an artifact to view its source code.
                </div>
              )}
            </TabsContent>

            <TabsContent value="preview" className="flex-1 mt-4">
              <LivePreview artifact={activeArtifact} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

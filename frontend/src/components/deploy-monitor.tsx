"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2, Minus, X, Circle, ExternalLink, Rocket } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useOrchestratorStore, type DeployStep } from "@/lib/orchestrator-store";

/**
 * The five deployment pipeline steps, in canonical display order. The `key`
 * matches the `step` field emitted by the backend `deploy_step` websocket event
 * (git_init | commit | push | build | deploy).
 */
const STEP_SEQUENCE: ReadonlyArray<{ key: string; label: string }> = [
  { key: "git_init", label: "Git Init" },
  { key: "commit", label: "Commit" },
  { key: "push", label: "Push" },
  { key: "build", label: "Build" },
  { key: "deploy", label: "Deploy" },
];

/** Human readable status used for tooltips and screen readers. */
function statusText(status?: string): string {
  switch (status) {
    case "start":
      return "in progress";
    case "ok":
      return "done";
    case "skipped":
      return "skipped";
    case "error":
      return "failed";
    default:
      return "pending";
  }
}

/**
 * Render the status glyph for a single step:
 * check for ok, spinner for start, dash for skipped, cross for error, and a
 * faint dot for steps that have not been reported yet.
 */
function StatusIcon({ status }: { status?: string }) {
  const base = "w-3.5 h-3.5 shrink-0";
  switch (status) {
    case "ok":
      return <Check className={cn(base, "text-emerald-400")} aria-hidden />;
    case "start":
      return <Loader2 className={cn(base, "text-amber-400 animate-spin")} aria-hidden />;
    case "skipped":
      return <Minus className={cn(base, "text-muted-foreground")} aria-hidden />;
    case "error":
      return <X className={cn(base, "text-red-400")} aria-hidden />;
    default:
      return <Circle className={cn(base, "text-muted-foreground/40")} aria-hidden />;
  }
}

/** Tint the step label to echo its status while staying theme consistent. */
function labelClass(status?: string): string {
  switch (status) {
    case "ok":
      return "text-foreground";
    case "start":
      return "text-amber-400";
    case "error":
      return "text-red-400";
    case "skipped":
      return "text-muted-foreground";
    default:
      return "text-muted-foreground/50";
  }
}

/**
 * Deployment Monitor widget (REQUIREMENTS.md 5.2).
 *
 * A compact, unobtrusive overlay pinned to the bottom right that mirrors the
 * live `deploy_step` events held in the orchestrator store. It renders the five
 * pipeline steps as a horizontal status strip and, once the deploy step reports
 * a URL, surfaces it as an external link. The widget stays hidden until at
 * least one deployment step has arrived.
 */
export function DeployMonitor() {
  const deploySteps = useOrchestratorStore((s) => s.deploySteps);

  /** Index the reported steps by their key for O(1) lookup during render. */
  const stepByKey = useMemo(() => {
    const map: Partial<Record<string, DeployStep>> = {};
    for (const step of deploySteps) {
      map[step.step] = step;
    }
    return map;
  }, [deploySteps]);

  const deployUrl = stepByKey["deploy"]?.url;
  const hasSteps = deploySteps.length > 0;

  return (
    <AnimatePresence>
      {hasSteps && (
        <motion.div
          key="deploy-monitor"
          className="fixed bottom-4 right-4 z-40 max-w-[min(420px,calc(100vw-2rem))]"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
        >
          <Card
            role="status"
            aria-live="polite"
            aria-label="Deployment progress"
            className="gap-2 rounded-lg border-border bg-card/95 p-3 shadow-lg backdrop-blur-sm"
          >
            {/* Header */}
            <div className="flex items-center gap-1.5">
              <Rocket className="w-3.5 h-3.5 text-primary" aria-hidden />
              <span className="text-xs font-semibold text-foreground">Deployment</span>
            </div>

            {/* Status strip */}
            <div className="flex items-center gap-3">
              {STEP_SEQUENCE.map(({ key, label }) => {
                const status = stepByKey[key]?.status;
                return (
                  <div
                    key={key}
                    className="flex items-center gap-1"
                    title={`${label}: ${statusText(status)}`}
                  >
                    <StatusIcon status={status} />
                    <span className={cn("text-xs whitespace-nowrap", labelClass(status))}>
                      {label}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Live deployment URL */}
            {deployUrl && (
              <a
                href={deployUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-emerald-400 transition-colors hover:text-emerald-300"
              >
                <span aria-hidden>&#8594;</span>
                <span className="truncate">{deployUrl.replace(/^https?:\/\//, "")}</span>
                <ExternalLink className="w-3 h-3 shrink-0" aria-hidden />
              </a>
            )}
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

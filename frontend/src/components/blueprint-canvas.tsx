"use client";

import { useEffect, useCallback, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Edge,
  type Node,
  Handle,
  Position,
} from "@xyflow/react";
import { motion } from "framer-motion";
import { Brain, Bot, Code, Database, Shield, Globe, DollarSign, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  useOrchestratorStore,
  type WrapperInfo,
  type WrapperStatus,
} from "@/lib/orchestrator-store";
import "@xyflow/react/dist/style.css";

type OfficeStatus = "idle" | "thinking" | "working" | "blocked";

interface DroneInfo {
  name: string;
  status: OfficeStatus;
}

interface OfficeNodeData {
  label: string;
  status: OfficeStatus;
  type: "head" | "worker";
  role: string;
  dataType?: string;
  drones: DroneInfo[];
  live?: boolean;
  [key: string]: unknown;
}

type StatusAnim = "none" | "pulse" | "flash";

const statusConfig: Record<OfficeStatus, { color: string; anim: StatusAnim }> = {
  idle: { color: "bg-zinc-400", anim: "none" },
  thinking: { color: "bg-amber-400", anim: "pulse" },
  working: { color: "bg-emerald-400", anim: "pulse" },
  blocked: { color: "bg-red-400", anim: "flash" },
};

/**
 * Edge and chip colours keyed by the office's meta.dataType.
 * requirements = blue, code = green, schema = gold, ops = red,
 * design = violet, doc = grey.
 */
const dataTypeColors: Record<string, string> = {
  requirements: "#3b82f6",
  design: "#8b5cf6",
  schema: "#eab308",
  code: "#10b981",
  ops: "#ef4444",
  doc: "#9ca3af",
};

/** Fallback edge colours keyed by live wrapper status. */
const statusColors: Record<WrapperStatus, string> = {
  IDLE: "#9ca3af",
  THINKING: "#f59e0b",
  WORKING: "#10b981",
  BLOCKED: "#ef4444",
};

/** Colour a hub-to-office edge by data type, falling back to status. */
function edgeColor(dataType: string | undefined, status: WrapperStatus): string {
  if (dataType && dataTypeColors[dataType]) return dataTypeColors[dataType];
  return statusColors[status] ?? "#9ca3af";
}

/**
 * A status pip. IDLE is a static grey dot, THINKING and WORKING pulse
 * (yellow and green), and BLOCKED flashes red with a faster, sharper blink
 * so it reads as distinct from the calmer pulse.
 */
function StatusDot({
  status,
  className,
}: {
  status: OfficeStatus;
  className?: string;
}) {
  const cfg = statusConfig[status];
  const base = cn("block rounded-full", cfg.color, className);

  if (cfg.anim === "flash") {
    return (
      <motion.span
        className={base}
        animate={{ opacity: [1, 0.15, 1] }}
        transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut" }}
      />
    );
  }

  if (cfg.anim === "pulse") {
    return (
      <motion.span
        className={base}
        animate={{ opacity: [1, 0.55, 1] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
      />
    );
  }

  return <span className={base} />;
}

const roleIcons = {
  Orchestrator: Brain,
  Architect: Brain,
  "Frontend Dev": Code,
  "Backend Dev": Database,
  Deployment: Globe,
  Security: Shield,
  DevOps: Globe,
  "Cost Optimizer": DollarSign,
  default: Bot,
} as const;

const roleColors = {
  Orchestrator: "from-purple-500 to-purple-700",
  Architect: "from-blue-500 to-blue-700",
  "Frontend Dev": "from-cyan-500 to-cyan-700",
  "Backend Dev": "from-green-500 to-green-700",
  Deployment: "from-orange-500 to-orange-700",
  Security: "from-red-500 to-red-700",
  DevOps: "from-orange-500 to-orange-700",
  "Cost Optimizer": "from-amber-500 to-amber-700",
  default: "from-gray-400 to-gray-600",
} as const;

type RoleIconKey = keyof typeof roleIcons;

/** Map backend WrapperInfo.type to a human-friendly role label. */
function wrapperTypeToRole(type: string): string {
  const map: Record<string, string> = {
    "frontend-design": "Frontend Dev",
    health: "DevOps",
    "backend-api": "Backend Dev",
    security: "Security",
    "cost-optimizer": "Cost Optimizer",
  };
  return map[type] ?? type;
}

/** Map backend WrapperStatus enum to lowercase OfficeStatus. */
function toOfficeStatus(ws: WrapperStatus): OfficeStatus {
  return ws.toLowerCase() as OfficeStatus;
}

/* ------------------------------------------------------------------ */
/*  OfficeNode component                                               */
/* ------------------------------------------------------------------ */

function OfficeNode({ data }: { data: OfficeNodeData }) {
  const IconComponent =
    roleIcons[data.role as RoleIconKey] ?? roleIcons.default;
  const roleColor = roleColors[data.role as RoleIconKey] ?? roleColors.default;

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={cn(
        "relative min-w-[220px] max-w-[280px] rounded-xl border-2 bg-card p-4 shadow-lg",
        data.status === "blocked" && "border-red-400/50 shadow-red-400/20",
        data.status === "working" &&
        "border-emerald-400/50 shadow-emerald-400/20",
        data.status === "thinking" && "border-amber-400/50 shadow-amber-400/20",
        data.status === "idle" && "border-border",
      )}
    >
      {/* Live indicator dot */}
      {data.live && (
        <div className="absolute -top-1 -left-1 w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
      )}

      {/* Status Indicator */}
      <StatusDot
        status={data.status}
        className="absolute -top-2 -right-2 h-4 w-4 border-2 border-card"
      />

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400"
      />

      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 bg-gradient-to-br",
            roleColor
          )}
        >
          <IconComponent className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">{data.label}</h3>
          <p className="text-xs text-muted-foreground">{data.role}</p>
        </div>
      </div>

      {/* Drones List */}
      {data.drones && data.drones.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {data.drones.map((drone, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 text-xs bg-muted/50 rounded px-2 py-1"
            >
              <StatusDot status={drone.status} className="h-2 w-2 shrink-0" />
              <span className="truncate text-muted-foreground">
                {drone.name}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Stats Badge */}
      <div className="mt-3 flex items-center gap-2">
        <Badge
          variant="outline"
          className={cn(
            "text-xs capitalize",
            data.status === "working" &&
            "border-emerald-400/30 text-emerald-400",
            data.status === "thinking" && "border-amber-400/30 text-amber-400",
            data.status === "blocked" && "border-red-400/30 text-red-400",
          )}
        >
          {data.status}
        </Badge>
      </div>

      {/* Output Handles */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="code"
        className="!w-3 !h-3 !bg-emerald-400"
        style={{ left: "30%" }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="data"
        className="!w-3 !h-3 !bg-blue-400"
        style={{ left: "50%" }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="error"
        className="!w-3 !h-3 !bg-red-400"
        style={{ left: "70%" }}
      />
    </motion.div>
  );
}

const nodeTypes = { office: OfficeNode };

/* ------------------------------------------------------------------ */
/*  Office Interior side panel (CANVAS-04)                             */
/* ------------------------------------------------------------------ */

function OfficeInteriorPanel({
  data,
  onClose,
}: {
  data: OfficeNodeData;
  onClose: () => void;
}) {
  const IconComponent =
    roleIcons[data.role as RoleIconKey] ?? roleIcons.default;
  const roleColor = roleColors[data.role as RoleIconKey] ?? roleColors.default;
  const dataType = data.dataType;
  const accent = dataType ? dataTypeColors[dataType] : undefined;

  return (
    <div
      className="absolute inset-0 z-20 flex justify-end bg-black/30"
      onClick={onClose}
      role="presentation"
    >
      <motion.aside
        initial={{ x: 48, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 320, damping: 32 }}
        className="relative h-full w-[320px] max-w-[85%] overflow-y-auto border-l border-border bg-card p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close office interior"
          className="absolute right-3 top-3 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header */}
        <div className="flex items-start gap-3 pr-8">
          <div
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br",
              roleColor,
            )}
          >
            <IconComponent className="h-5 w-5 text-white" />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold">{data.label}</h2>
            <p className="text-xs text-muted-foreground">{data.role}</p>
          </div>
        </div>

        <div className="mt-2 text-[11px] uppercase tracking-wide text-muted-foreground">
          Office Interior
        </div>

        {/* Meta rows */}
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              Status
            </span>
            <span className="flex items-center gap-2">
              <StatusDot status={data.status} className="h-2.5 w-2.5" />
              <span className="text-xs font-medium capitalize">
                {data.status}
              </span>
            </span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              Data type
            </span>
            {dataType ? (
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium capitalize text-white"
                style={{ backgroundColor: accent ?? "#9ca3af" }}
              >
                {dataType}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground">n/a</span>
            )}
          </div>
        </div>

        {/* Drones / task queue */}
        <div className="mt-6">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {data.drones.length > 0 ? "Worker Drones" : "Task Summary"}
          </h3>
          {data.drones.length > 0 ? (
            <ul className="space-y-1.5">
              {data.drones.map((drone, idx) => (
                <li
                  key={idx}
                  className="flex items-center gap-2 rounded-md bg-muted/50 px-2.5 py-1.5 text-xs"
                >
                  <StatusDot status={drone.status} className="h-2 w-2 shrink-0" />
                  <span className="truncate">{drone.name}</span>
                  <span className="ml-auto shrink-0 capitalize text-muted-foreground">
                    {drone.status}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-md bg-muted/50 px-2.5 py-2 text-xs text-muted-foreground">
              {data.label} is currently {data.status}
              {dataType ? ` on ${dataType}` : ""}.
            </p>
          )}
        </div>
      </motion.aside>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Convert live wrapper map -> React Flow nodes & edges               */
/* ------------------------------------------------------------------ */

const ORCHESTRATOR_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "ws://localhost:9100")
    : "ws://localhost:9100";

/** Layout helpers to auto-place wrappers in a grid. */
function buildLiveGraph(wrappers: Record<string, WrapperInfo>): {
  nodes: Node<OfficeNodeData>[];
  edges: Edge[];
} {
  const entries = Object.values(wrappers).filter(
    (w) => w.type !== "ui-observer",
  );

  if (entries.length === 0) return { nodes: DEMO_NODES, edges: DEMO_EDGES };

  // Place an "orchestrator hub" node at top centre
  const hubNode: Node<OfficeNodeData> = {
    id: "orchestrator-hub",
    type: "office",
    position: { x: 400, y: 80 },
    data: {
      label: "Orchestrator",
      status: "working",
      type: "head",
      role: "Head Agent",
      drones: Array.from({ length: Math.max(1, entries.length) }).map(
        (_, idx) => ({
          name: `Agent ${idx + 1}`,
          status: "working",
        }),
      ),
      live: true,
    },
  };

  const spacing = 280;
  const startX = 400 - ((entries.length - 1) * spacing) / 2;

  const nodes: Node<OfficeNodeData>[] = [hubNode];
  const edges: Edge[] = [];

  entries.forEach((w, i) => {
    const dataType =
      typeof w.meta.dataType === "string" ? w.meta.dataType : undefined;

    nodes.push({
      id: w.id,
      type: "office",
      position: { x: startX + i * spacing, y: 320 },
      data: {
        label: w.meta.name,
        status: toOfficeStatus(w.status),
        type: "worker",
        role: wrapperTypeToRole(w.type),
        dataType,
        drones: Array.isArray((w.meta as any).drones)
          ? ((w.meta as any).drones as DroneInfo[])
          : Array.from({ length: Math.max(1, Number(w.meta.drones ?? 1)) }).map(
            (_, dIdx) => ({
              name: `${wrapperTypeToRole(w.type)} Agent ${dIdx + 1}`,
              status: "idle",
            }),
          ),
        live: true,
      },
    });

    edges.push({
      id: `e-hub-${w.id}`,
      source: "orchestrator-hub",
      target: w.id,
      animated: w.status !== "IDLE",
      style: { stroke: edgeColor(dataType, w.status) },
    });
  });

  return { nodes, edges };
}

/* ------------------------------------------------------------------ */
/*  Demo fallback data (shown when orchestrator is offline)            */
/* ------------------------------------------------------------------ */

const DEMO_NODES: Node<OfficeNodeData>[] = [
  {
    id: "1",
    type: "office",
    position: { x: 400, y: 50 },
    data: {
      label: "CEO Office",
      status: "idle",
      type: "head",
      role: "Orchestrator",
      drones: [
        { name: "Project Planner", status: "idle" },
        { name: "File Manifest Generator", status: "idle" },
      ],
    },
  },
  {
    id: "2",
    type: "office",
    position: { x: 400, y: 250 },
    data: {
      label: "Product Office",
      status: "idle",
      type: "worker",
      role: "Architect",
      drones: [
        { name: "Tech Stack Selector", status: "idle" },
        { name: "Architecture Designer", status: "idle" },
      ],
    },
  },
  {
    id: "3",
    type: "office",
    position: { x: 150, y: 450 },
    data: {
      label: "Engineering - Frontend",
      status: "idle",
      type: "worker",
      role: "Frontend Dev",
      drones: [
        { name: "Component Builder", status: "idle" },
        { name: "UI Developer", status: "idle" },
      ],
    },
  },
  {
    id: "4",
    type: "office",
    position: { x: 650, y: 450 },
    data: {
      label: "Engineering - Backend",
      status: "idle",
      type: "worker",
      role: "Backend Dev",
      drones: [
        { name: "API Developer", status: "idle" },
        { name: "Logic Engineer", status: "idle" },
      ],
    },
  },
  {
    id: "5",
    type: "office",
    position: { x: 400, y: 650 },
    data: {
      label: "DevOps Office",
      status: "idle",
      type: "worker",
      role: "Deployment",
      drones: [
        { name: "Git Manager", status: "idle" },
        { name: "GitHub Publisher", status: "idle" },
      ],
    },
  },
  {
    id: "6",
    type: "office",
    position: { x: 750, y: 250 },
    data: {
      label: "Cost Optimizer",
      status: "idle",
      type: "worker",
      role: "Cost Optimizer",
      drones: [
        { name: "Token Tracker", status: "idle" },
        { name: "Path Optimizer", status: "idle" },
      ],
    },
  },
];

const DEMO_EDGES: Edge[] = [
  {
    id: "e1-2",
    source: "1",
    target: "2",
    animated: true,
    style: { stroke: "#3b82f6" },
  },
  {
    id: "e2-3",
    source: "2",
    target: "3",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e2-4",
    source: "2",
    target: "4",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e3-5",
    source: "3",
    target: "5",
    animated: true,
    style: { stroke: "#fbbf24" },
  },
  {
    id: "e4-5",
    source: "4",
    target: "5",
    animated: true,
    style: { stroke: "#fbbf24" },
  },
  {
    id: "e2-6",
    source: "2",
    target: "6",
    animated: true,
    style: { stroke: "#f59e0b" },
  },
  {
    id: "e6-5",
    source: "6",
    target: "5",
    animated: true,
    style: { stroke: "#f59e0b" },
  },
];

/* ------------------------------------------------------------------ */
/*  BlueprintCanvas component                                          */
/* ------------------------------------------------------------------ */

export function BlueprintCanvas() {
  const { wrappers, connected, connect, disconnect } = useOrchestratorStore();
  const [nodes, setNodes, onNodesChange] = useNodesState(DEMO_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(DEMO_EDGES);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Connect on mount, don't disconnect on unmount (shared WS connection)
  useEffect(() => {
    connect(ORCHESTRATOR_URL);
  }, [connect]);

  // Close the Office Interior panel on Escape.
  useEffect(() => {
    if (!selectedId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId]);

  // Track previous wrapper keys to detect actual changes
  const prevWrapperKeysRef = useRef<string>("");

  // Rebuild the graph whenever live wrappers actually change
  useEffect(() => {
    const wrapperKeys = Object.keys(wrappers).sort().join(",");
    const wrapperHash =
      wrapperKeys +
      JSON.stringify(
        Object.values(wrappers).map(
          (w) => `${w.id}-${w.status}-${String(w.meta.dataType ?? "")}`,
        ),
      );

    // Only rebuild if wrappers actually changed
    if (prevWrapperKeysRef.current === wrapperHash) return;
    prevWrapperKeysRef.current = wrapperHash;

    const { nodes: liveNodes, edges: liveEdges } = buildLiveGraph(wrappers);
    setNodes(liveNodes);
    setEdges(liveEdges);
  }, [wrappers]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges],
  );

  const selectedNode = selectedId
    ? nodes.find((n) => n.id === selectedId) ?? null
    : null;

  return (
    <div className="w-full h-full bg-background relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node) => setSelectedId(node.id)}
        onPaneClick={() => setSelectedId(null)}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        className="bg-dot-pattern"
      >
        <Background gap={20} size={1} className="bg-muted/20" />
      </ReactFlow>

      {selectedNode && (
        <OfficeInteriorPanel
          data={selectedNode.data}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}

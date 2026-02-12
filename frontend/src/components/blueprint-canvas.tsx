"use client";

import { useEffect, useCallback, useRef } from "react";
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
import { Brain, Bot, Code, Database, Shield, Globe } from "lucide-react";
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
  drones: DroneInfo[];
  live?: boolean;
  [key: string]: unknown;
}

const statusConfig: Record<OfficeStatus, { color: string; pulse: boolean }> = {
  idle: { color: "bg-zinc-400", pulse: false },
  thinking: { color: "bg-amber-400", pulse: true },
  working: { color: "bg-emerald-400", pulse: true },
  blocked: { color: "bg-red-400", pulse: true },
};

const roleIcons = {
  "Head Agent": Brain,
  "Frontend Dev": Code,
  "Backend Dev": Database,
  Security: Shield,
  DevOps: Globe,
  default: Bot,
} as const;

type RoleIconKey = keyof typeof roleIcons;

/** Map backend WrapperInfo.type to a human-friendly role label. */
function wrapperTypeToRole(type: string): string {
  const map: Record<string, string> = {
    "frontend-design": "Frontend Dev",
    health: "DevOps",
    "backend-api": "Backend Dev",
    security: "Security",
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
  const status = statusConfig[data.status];
  const IconComponent =
    roleIcons[data.role as RoleIconKey] ?? roleIcons.default;

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
      <div
        className={cn(
          "absolute -top-2 -right-2 w-4 h-4 rounded-full border-2 border-card",
          status.color,
          status.pulse && "animate-pulse",
        )}
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
            "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
            data.type === "head"
              ? "bg-gradient-to-br from-gray-200 to-gray-400"
              : "bg-gradient-to-br from-gray-400 to-gray-600",
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
          {data.drones.map((drone, idx) => {
            const droneStatus = statusConfig[drone.status];
            return (
              <div
                key={idx}
                className="flex items-center gap-2 text-xs bg-muted/50 rounded px-2 py-1"
              >
                <div
                  className={cn(
                    "w-2 h-2 rounded-full shrink-0",
                    droneStatus.color,
                    droneStatus.pulse && "animate-pulse",
                  )}
                />
                <span className="truncate text-muted-foreground">
                  {drone.name}
                </span>
              </div>
            );
          })}
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
    nodes.push({
      id: w.id,
      type: "office",
      position: { x: startX + i * spacing, y: 320 },
      data: {
        label: w.meta.name,
        status: toOfficeStatus(w.status),
        type: "worker",
        role: wrapperTypeToRole(w.type),
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

    const statusColor: Record<WrapperStatus, string> = {
      IDLE: "#9ca3af",
      THINKING: "#f59e0b",
      WORKING: "#10b981",
      BLOCKED: "#ef4444",
    };

    edges.push({
      id: `e-hub-${w.id}`,
      source: "orchestrator-hub",
      target: w.id,
      animated: w.status !== "IDLE",
      style: { stroke: statusColor[w.status] ?? "#9ca3af" },
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
      label: "Executive Management",
      status: "working",
      type: "head",
      role: "CPO",
      drones: [
        { name: "Requirements Analyst", status: "working" },
        { name: "Resource Allocator", status: "idle" },
      ],
    },
  },
  {
    id: "2",
    type: "office",
    position: { x: 50, y: 250 },
    data: {
      label: "Product Management",
      status: "thinking",
      type: "worker",
      role: "PM",
      drones: [
        { name: "User Story Writer", status: "thinking" },
        { name: "Feature Prioritizer", status: "idle" },
      ],
    },
  },
  {
    id: "3",
    type: "office",
    position: { x: 300, y: 250 },
    data: {
      label: "Database Systems",
      status: "working",
      type: "worker",
      role: "DBA Manager",
      drones: [
        { name: "Schema Architect", status: "working" },
        { name: "SQL Optimizer", status: "working" },
        { name: "Seeder", status: "idle" },
      ],
    },
  },
  {
    id: "4",
    type: "office",
    position: { x: 550, y: 250 },
    data: {
      label: "Web Frontend",
      status: "working",
      type: "worker",
      role: "Frontend Lead",
      drones: [
        { name: "Component Builder", status: "working" },
        { name: "State Manager", status: "thinking" },
      ],
    },
  },
  {
    id: "5",
    type: "office",
    position: { x: 800, y: 250 },
    data: {
      label: "Backend Engineering",
      status: "idle",
      type: "worker",
      role: "Backend Lead",
      drones: [
        { name: "API Developer", status: "idle" },
        { name: "Logic Engineer", status: "idle" },
      ],
    },
  },
  {
    id: "6",
    type: "office",
    position: { x: 400, y: 450 },
    data: {
      label: "DevOps & Deployment",
      status: "thinking",
      type: "worker",
      role: "SRE",
      drones: [
        { name: "CI/CD Architect", status: "thinking" },
        { name: "Release Manager", status: "idle" },
        { name: "Docker Specialist", status: "idle" },
      ],
    },
  },
  {
    id: "7",
    type: "office",
    position: { x: 100, y: 650 },
    data: {
      label: "QA & Testing",
      status: "blocked",
      type: "worker",
      role: "QA Lead",
      drones: [
        { name: "Unit Tester", status: "blocked" },
        { name: "E2E Scripter", status: "idle" },
      ],
    },
  },
  {
    id: "8",
    type: "office",
    position: { x: 700, y: 650 },
    data: {
      label: "Cybersecurity",
      status: "idle",
      type: "worker",
      role: "CISO",
      drones: [
        { name: "Red Teamer", status: "idle" },
        { name: "Blue Teamer", status: "idle" },
        { name: "Compliance Officer", status: "idle" },
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
    id: "e1-3",
    source: "1",
    target: "3",
    animated: true,
    style: { stroke: "#fbbf24" },
  },
  {
    id: "e1-4",
    source: "1",
    target: "4",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e1-5",
    source: "1",
    target: "5",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e3-4",
    source: "3",
    target: "4",
    animated: true,
    style: { stroke: "#fbbf24" },
  },
  {
    id: "e4-6",
    source: "4",
    target: "6",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e5-6",
    source: "5",
    target: "6",
    animated: true,
    style: { stroke: "#10b981" },
  },
  {
    id: "e6-7",
    source: "6",
    target: "7",
    animated: true,
    style: { stroke: "#ef4444" },
  },
  {
    id: "e6-8",
    source: "6",
    target: "8",
    animated: true,
    style: { stroke: "#3b82f6" },
  },
];

/* ------------------------------------------------------------------ */
/*  BlueprintCanvas component                                          */
/* ------------------------------------------------------------------ */

export function BlueprintCanvas() {
  const { wrappers, connected, connect, disconnect } = useOrchestratorStore();
  const [nodes, setNodes, onNodesChange] = useNodesState(DEMO_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(DEMO_EDGES);

  // Connect on mount — don't disconnect on unmount (shared WS connection)
  useEffect(() => {
    connect(ORCHESTRATOR_URL);
  }, [connect]);

  // Track previous wrapper keys to detect actual changes
  const prevWrapperKeysRef = useRef<string>("");

  // Rebuild the graph whenever live wrappers actually change
  useEffect(() => {
    const wrapperKeys = Object.keys(wrappers).sort().join(",");
    const wrapperHash =
      wrapperKeys +
      JSON.stringify(Object.values(wrappers).map((w) => `${w.id}-${w.status}`));

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

  return (
    <div className="w-full h-full bg-background relative">
      {/* Connection indicator */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        <div
          className={cn(
            "w-2 h-2 rounded-full",
            connected ? "bg-emerald-400 animate-pulse" : "bg-zinc-500",
          )}
        />
        <span className="text-xs text-muted-foreground">
          {connected ? "Live" : "Offline"}
        </span>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        className="bg-dot-pattern"
      >
        <Background gap={20} size={1} className="bg-muted/20" />
      </ReactFlow>
    </div>
  );
}

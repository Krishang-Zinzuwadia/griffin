"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Hash } from "lucide-react";
import { Navbar } from "@/components/navbar";
import { BlueprintCanvas } from "@/components/blueprint-canvas";
import { ChatPage } from "@/components/chat-page";
import { CommunicationHub } from "@/components/communication-hub";
import { GodModeTerminal } from "@/components/god-mode-terminal";
import { Workstation } from "@/components/workstation";
import { CostDashboard } from "@/components/cost-dashboard";
import { MultiverseScene, type UniverseData } from "@/components/multiverse";
import { SettingsDialog } from "@/components/settings-dialog";
import { cn } from "@/lib/utils";

type ViewType =
  | "canvas"
  | "chat"
  | "channels"
  | "terminal"
  | "workstation"
  | "cost"
  | "multiverse";

const viewComponents: Record<ViewType, React.ComponentType<any>> = {
  canvas: BlueprintCanvas,
  chat: ChatPage,
  channels: CommunicationHub,
  terminal: GodModeTerminal,
  workstation: Workstation,
  cost: CostDashboard,
  multiverse: () => (
    <MultiverseScene
      isOpen={true}
      onClose={() => {}}
      onSelectUniverse={(universe, index) => {
        console.log("Selected universe:", universe, "at index:", index);
      }}
    />
  ),
};

export default function Home() {
  const [activeView, setActiveView] = useState<ViewType>("canvas");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const ActiveComponent = viewComponents[activeView];

  /**
   * Handle view changes from navbar
   */
  const handleViewChange = (view: string) => {
    setActiveView(view as ViewType);
  };

  return (
    <div className="h-screen w-full bg-background overflow-hidden">
      <Navbar
        activeView={activeView}
        onViewChange={handleViewChange}
        onSettingsClick={() => setSettingsOpen(true)}
      />
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      {/*
        Channels entry point. The shared Navbar dock is a fixed component that
        this view does not own, so the Communication Hub gets its own dock pill.
      */}
      <div className="fixed bottom-3 right-4 z-50">
        <button
          onClick={() => setActiveView("channels")}
          aria-label="Channels"
          className={cn(
            "group relative flex h-11 items-center gap-2 rounded-xl border border-white/10 bg-black/40 px-3 text-foreground shadow-2xl backdrop-blur-xl transition-colors hover:bg-white/10",
            activeView === "channels" && "bg-white/20 ring-1 ring-white/30",
          )}
        >
          <Hash className="h-4 w-4" />
          <span className="text-xs font-medium">Channels</span>
          {activeView === "channels" && (
            <span className="absolute -bottom-1.5 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-foreground" />
          )}
        </button>
      </div>

      {/* Main Workspace Area. Bottom padding keeps content above the floating dock */}
      <div className="relative h-full w-full overflow-hidden pb-[68px]">
        {/* Multiverse - always mounted, hidden when inactive */}
        <div
          className="absolute inset-0 w-full h-full"
          style={{
            opacity: activeView === "multiverse" ? 1 : 0,
            pointerEvents: activeView === "multiverse" ? "auto" : "none",
            zIndex: activeView === "multiverse" ? 10 : 0,
          }}
        >
          <MultiverseScene
            isOpen={true}
            onClose={() => {}}
            onSelectUniverse={(universe, index) => {
              console.log("Selected universe:", universe, "at index:", index);
              // Switch to canvas view after selection
              setTimeout(() => setActiveView("canvas"), 100);
            }}
          />
        </div>

        {/* Other views with transitions */}
        {activeView !== "multiverse" && (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
              className="relative h-full w-full"
              style={{ zIndex: 20 }}
            >
              <ActiveComponent />
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

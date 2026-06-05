import DashboardShell from "@/components/DashboardShell";
import TabOrchestrator from "@/components/TabOrchestrator";

// Server component — composes the static shell with the client tab orchestrator.
export default function Home() {
  return (
    <DashboardShell>
      <TabOrchestrator />
    </DashboardShell>
  );
}

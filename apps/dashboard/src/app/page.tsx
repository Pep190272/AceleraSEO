import DashboardShell from "@/components/DashboardShell";
import TabOrchestrator from "@/components/TabOrchestrator";

interface HomeProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

// Server component — composes the static shell with the client tab orchestrator.
// The `?tab=<id>` deep link is read here so the requested tab renders on first paint.
export default async function Home({ searchParams }: HomeProps) {
  const { tab } = await searchParams;
  return (
    <DashboardShell>
      <TabOrchestrator requestedTab={typeof tab === "string" ? tab : undefined} />
    </DashboardShell>
  );
}

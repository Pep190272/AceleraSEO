// Server component — outer layout container.
// Contains no state, no hooks, and no client-only APIs.
// All translated/interactive content is passed in via children.

interface DashboardShellProps {
  children: React.ReactNode;
}

export default function DashboardShell({ children }: DashboardShellProps) {
  return <div className="container">{children}</div>;
}

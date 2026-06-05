// Presentational atom — renders a single tab button.
// Owns no state; active/click are passed as props by the orchestrator.

interface TabButtonProps {
  label: string;
  isActive: boolean;
  onClick: () => void;
}

export default function TabButton({ label, isActive, onClick }: TabButtonProps) {
  return (
    <button className={`tab${isActive ? " active" : ""}`} onClick={onClick} type="button">
      {label}
    </button>
  );
}

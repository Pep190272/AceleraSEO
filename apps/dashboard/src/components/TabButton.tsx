// Presentational atom — renders a single tab button.
// Owns no state; active/click/ARIA are passed as props by the orchestrator.
// Uses forwardRef so the orchestrator can programmatically focus this button
// for keyboard navigation (roving tabindex pattern).

import { forwardRef } from "react";

interface TabButtonProps {
  id: string;
  label: string;
  isActive: boolean;
  onClick: () => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLButtonElement>) => void;
}

const TabButton = forwardRef<HTMLButtonElement, TabButtonProps>(function TabButton(
  { id, label, isActive, onClick, onKeyDown },
  ref,
) {
  return (
    <button
      ref={ref}
      id={`tab-${id}`}
      role="tab"
      aria-selected={isActive}
      aria-controls={`panel-${id}`}
      tabIndex={isActive ? 0 : -1}
      className={`tab${isActive ? " active" : ""}`}
      onClick={onClick}
      onKeyDown={onKeyDown}
      type="button"
    >
      {label}
    </button>
  );
});

export default TabButton;

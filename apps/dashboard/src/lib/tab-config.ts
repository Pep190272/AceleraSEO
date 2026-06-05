import type { ComponentType } from "react";

import AuditTool from "@/components/AuditTool";
import CompetitorTool from "@/components/CompetitorTool";
import SettingsTool from "@/components/SettingsTool";
import StrategyTool from "@/components/StrategyTool";

export interface TabEntry {
  id: string;
  labelKey: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  component: ComponentType<any>;
}

// `satisfies` validates each entry against TabEntry while keeping literal types
// so that Tab below resolves to a narrow string union instead of plain `string`.
export const TAB_CONFIG = [
  { id: "strategy", labelKey: "nav.strategy", component: StrategyTool },
  { id: "competitors", labelKey: "nav.competitors", component: CompetitorTool },
  { id: "audit", labelKey: "nav.audit", component: AuditTool },
  { id: "settings", labelKey: "nav.settings", component: SettingsTool },
] as const satisfies ReadonlyArray<TabEntry>;

// Tab id union inferred from the config so it stays in sync automatically.
export type Tab = (typeof TAB_CONFIG)[number]["id"];

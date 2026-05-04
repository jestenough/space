import { text } from "@/ui/i18n";
import type { Lang } from "@/core/types";

export type PanelName = "home" | "articles" | "tags";

export const panelInfo = (lang: Lang, panel: PanelName, tag?: string): { title: string; lead: string; body: string } => {
  const ui = text(lang);
  if (panel === "home") return { title: ui.welcomeTitle, lead: ui.welcomeLead, body: ui.welcomeBody };
  if (panel === "articles") return { title: "articles", lead: ui.panelArticlesLead, body: ui.panelArticlesBody };
  if (panel === "tags" && tag) return { title: `tag: ${tag}`, lead: ui.panelTagLead, body: ui.panelTagBody };
  if (panel === "tags") return { title: "tags", lead: ui.panelTagsLead, body: ui.panelTagsBody };
  return { title: ui.welcomeTitle, lead: ui.welcomeLead, body: ui.welcomeBody };
};

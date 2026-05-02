import { dom } from "./dom";
import type { Theme } from "./types";

const THEMES: readonly Theme[] = ["reading", "light", "system", "dark"];

export function applyTheme(theme: string): void {
  const chosen: Theme = THEMES.includes(theme as Theme) ? (theme as Theme) : "system";
  localStorage.setItem("theme", chosen);
  dom.themeSwitcher.value = chosen;

  if (chosen === "system") {
    dom.html.dataset.theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    return;
  }

  dom.html.dataset.theme = chosen;
}

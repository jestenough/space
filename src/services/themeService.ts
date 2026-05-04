import type { Theme } from "@/core/types";
export const DEFAULT_THEME: Theme = "system";
export const THEMES: readonly Theme[] = ["reading", "light", "system", "dark"];
const systemMedia = (): MediaQueryList => window.matchMedia("(prefers-color-scheme: dark)");
export const isTheme = (value: string | null | undefined): value is Theme => value !== null && value !== undefined && THEMES.includes(value as Theme);
export const normalizeTheme = (value: string | null | undefined): Theme => isTheme(value) ? value : DEFAULT_THEME;
const resolveTheme = (theme: Theme): string => theme === "system" ? (systemMedia().matches ? "dark" : "light") : theme;
export const themeService = {
  initBeforeRender(): Theme { const choice = normalizeTheme(document.documentElement.dataset.themeChoice); document.documentElement.dataset.theme = resolveTheme(choice); document.documentElement.dataset.themeChoice = choice; return choice; },
  apply(value: string | null | undefined): Theme { const choice = normalizeTheme(value); document.documentElement.dataset.theme = resolveTheme(choice); document.documentElement.dataset.themeChoice = choice; return choice; },
  bindSystemTheme(listener: () => void): () => void { const media = systemMedia(); media.addEventListener("change", listener); return () => media.removeEventListener("change", listener); }
} as const;

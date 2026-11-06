/// <reference types="vite/client" />

interface AutophanyBoot {
  applyTheme(value: string): string;
  applyThemeFromStorage(): string;
  applyPanels(): void;
  panelOpen(key: string, desktop?: boolean): boolean;
  themeChoice(): string;
}

interface Window {
  autophanyBoot: AutophanyBoot;
}

declare module "*.md?raw" {
  const value: string;
  export default value;
}

declare module "*.txt?raw" {
  const value: string;
  export default value;
}

declare module "*.local?raw" {
  const value: string;
  export default value;
}

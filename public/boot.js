(() => {
  const themes = ["reading", "light", "system", "dark"];
  const desktopQuery = "(min-width: 761px)";
  const themeQuery = "(prefers-color-scheme: dark)";

  const normalizeTheme = (value) => themes.includes(value) ? value : "system";
  const resolveTheme = (choice) => choice === "system"
    ? (window.matchMedia(themeQuery).matches ? "dark" : "light")
    : choice;
  const panelKey = (key) => `panel:${key}:open`;
  const read = (key) => {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const applyTheme = (value) => {
    const choice = normalizeTheme(value);
    document.documentElement.dataset.theme = resolveTheme(choice);
    document.documentElement.dataset.themeChoice = choice;
    return choice;
  };

  const applyThemeFromStorage = () => {
    const choice = applyTheme(read("theme"));
    document.documentElement.dataset.panels = "pending";
    return choice;
  };

  const panel = (key) => document.querySelector(`details[data-panel-key="${CSS.escape(key)}"]`);
  const panelOpen = (key, desktop = window.matchMedia(desktopQuery).matches) => {
    if (!desktop) return panel(key)?.dataset.panelMobileOpen !== "false";
    const stored = read(panelKey(key));
    if (stored === "true" || stored === "false") return stored === "true";
    return panel(key)?.open ?? true;
  };

  const syncControls = () => {
    const themeSelect = document.getElementById("theme-switcher");
    if (themeSelect instanceof HTMLSelectElement) {
      themeSelect.value = document.documentElement.dataset.themeChoice || "system";
    }
    const langSelect = document.getElementById("lang-switcher");
    if (langSelect instanceof HTMLSelectElement) {
      langSelect.value = document.documentElement.lang || "en";
    }
  };

  const applyPanels = () => {
    const desktop = window.matchMedia(desktopQuery).matches;
    try {
      document.querySelectorAll("details[data-panel-key]").forEach((value) => {
        const key = value.dataset.panelKey;
        if (key) value.open = panelOpen(key, desktop);
      });
      syncControls();
    } finally {
      document.documentElement.dataset.panels = "ready";
    }
  };

  window.autophanyBoot = {
    applyTheme,
    applyThemeFromStorage,
    applyPanels,
    panelOpen,
    themeChoice: () => document.documentElement.dataset.themeChoice || "system",
  };

  applyThemeFromStorage();
})();

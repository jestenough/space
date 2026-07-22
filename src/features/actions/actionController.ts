export const initActions = (): void => {
  document.querySelectorAll<HTMLButtonElement>("button[data-action-href]").forEach((button) => {
    button.addEventListener("click", () => {
      const href = button.dataset.actionHref;
      if (!href) return;
      if (button.dataset.actionTarget === "_blank") {
        window.open(href, "_blank", "noopener,noreferrer");
      } else {
        window.location.assign(href);
      }
    });
  });
};

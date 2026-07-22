let toastTimer: number | null = null;

const hasTextSelection = (root: HTMLElement): boolean => {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed) return false;
  const anchor = selection.anchorNode;
  const focus = selection.focusNode;
  return Boolean((anchor && root.contains(anchor)) || (focus && root.contains(focus)));
};

const showToast = (message: string): void => {
  const toast = document.getElementById("copy-toast");
  if (!(toast instanceof HTMLElement)) return;
  toast.textContent = message;
  toast.dataset.visible = "true";
  if (toastTimer !== null) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.dataset.visible = "false";
    toastTimer = null;
  }, 1800);
};

const copyText = async (value: string): Promise<boolean> => {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);
  const copied = document.execCommand("copy");
  textarea.remove();
  return copied;
};

const copyReference = async (button: HTMLElement): Promise<void> => {
  const item = button.closest<HTMLElement>(".ref-item[data-ref]");
  const value = item?.textContent?.replace(/\s+/g, " ").trim();
  if (!item || !value) return;
  const copied = await copyText(value);
  const references = item.closest<HTMLElement>(".article-references");
  showToast(copied
    ? references?.dataset.copySuccess || "reference copied"
    : references?.dataset.copyFailure || "copy failed");
};

export const clipboardController = {
  init(): void {
    document.querySelectorAll<HTMLButtonElement>("button[data-copy-text]").forEach((button) => {
      button.addEventListener("click", async () => {
        const text = button.dataset.copyText;
        if (!text) return;
        const label = button.dataset.copyLabel || button.textContent || "copy";
        const success = button.dataset.copySuccess || label;
        const copied = await copyText(text);
        button.textContent = copied ? success : label;
        showToast(copied
          ? button.dataset.copyToastSuccess || "citation copied to clipboard"
          : button.dataset.copyToastFailure || "copy failed");
        window.setTimeout(() => {
          button.textContent = label;
        }, 1200);
      });
    });

    document.addEventListener("click", (event) => {
      const target = event.target as HTMLElement | null;
      const referenceButton = target?.closest<HTMLElement>("[data-reference-copy]");
      if (referenceButton) {
        void copyReference(referenceButton);
        return;
      }

      const control = target?.closest<HTMLElement>("[data-copy-value]");
      if (!control || target?.closest("a, button, img") || hasTextSelection(control)) return;
      const value = control.dataset.copyValue;
      if (!value) return;
      void copyText(value).then((copied) => {
        showToast(copied
          ? control.dataset.copyToastSuccess || "copied"
          : control.dataset.copyToastFailure || "copy failed");
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const target = event.target as HTMLElement | null;
      const control = target?.closest<HTMLElement>("[data-copy-value]");
      if (!control || target?.closest("a, button, img")) return;
      const value = control.dataset.copyValue;
      if (!value) return;
      event.preventDefault();
      void copyText(value).then((copied) => {
        showToast(copied
          ? control.dataset.copyToastSuccess || "copied"
          : control.dataset.copyToastFailure || "copy failed");
      });
    });
  },
} as const;

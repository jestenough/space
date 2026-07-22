const OPEN_CLASS = "image-viewer-open";

const captionText = (image: HTMLImageElement): string => {
  const figure = image.closest("figure");
  const figcaption = figure?.querySelector("figcaption")?.textContent?.trim();
  return figcaption || image.alt || "";
};

export const imageViewerController = {
  bind(root: HTMLElement): void {
    const viewer = document.getElementById("image-viewer");
    const viewerImage = document.getElementById("image-viewer-img");
    const viewerCaption = document.getElementById("image-viewer-caption");
    if (!(viewer instanceof HTMLElement) || !(viewerImage instanceof HTMLImageElement) || !(viewerCaption instanceof HTMLElement)) return;

    let activeSrc = "";

    const onKeydown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") close();
    };

    const close = (): void => {
      viewer.classList.add("hidden");
      viewer.setAttribute("aria-hidden", "true");
      document.body.classList.remove(OPEN_CLASS);
      document.removeEventListener("keydown", onKeydown);
      activeSrc = "";
    };

    const open = (image: HTMLImageElement): void => {
      const src = image.dataset.fullImage || image.currentSrc || image.src;
      if (!src) return;
      if (activeSrc === src && !viewer.classList.contains("hidden")) {
        close();
        return;
      }
      activeSrc = src;
      viewerImage.src = src;
      viewerImage.alt = image.alt;
      viewerCaption.textContent = captionText(image);
      viewer.classList.remove("hidden");
      viewer.setAttribute("aria-hidden", "false");
      document.body.classList.add(OPEN_CLASS);
      document.addEventListener("keydown", onKeydown);
    };

    root.addEventListener("click", (event) => {
      const image = (event.target as HTMLElement | null)?.closest<HTMLImageElement>("img[data-zoomable-image]");
      if (image) open(image);
    });

    viewer.addEventListener("click", (event) => {
      if (event.target === viewer || event.target === viewerImage) close();
    });
  }
} as const;

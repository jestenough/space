import { safeDecodeURIComponent } from "@/core/url";

type TocElements = {
  articleContent: HTMLElement;
  tocPanel: HTMLElement;
  tocList: HTMLUListElement;
};

export class TocController {
  private observer: IntersectionObserver | null = null;
  private activeHeadingId: string | null = null;

  clear(elements: TocElements): void {
    this.observer?.disconnect();
    this.observer = null;
    this.activeHeadingId = null;
    elements.tocList.replaceChildren();
    elements.tocPanel.classList.add("hidden");
  }

  render(elements: TocElements): string | null {
    this.clear(elements);

    const headings = Array.from(elements.articleContent.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6"));
    if (headings.length === 0) return null;

    const usedIds = new Set<string>();
    const fragment = document.createDocumentFragment();

    for (const [index, heading] of headings.entries()) {
      const headingText = heading.textContent?.replace("#", "").trim() || `Section ${index + 1}`;
      const semanticId = slugifyHeading(headingText);
      heading.id = uniqueHeadingId(semanticId || slugifyHeading(`section-${index + 1}`), usedIds);
      heading.classList.add("anchored-heading", "is-clickable-anchor");
      ensureHeadingAnchor(heading, headingText);

      const level = Number.parseInt(heading.tagName.slice(1), 10);
      const item = document.createElement("li");
      item.className = `toc-item toc-level-${Math.min(Math.max(level, 1), 6)}`;
      const link = document.createElement("a");
      link.href = `#${encodeURIComponent(heading.id)}`;
      link.dataset.headingId = heading.id;
      link.textContent = headingText;
      item.append(link);
      fragment.append(item);
    }

    elements.tocList.append(fragment);
    elements.tocPanel.classList.remove("hidden");

    this.observer = new IntersectionObserver(
      (entries) => {
        const activeEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (activeEntry?.target.id) this.markActive(elements.tocList, activeEntry.target.id);
      },
      { rootMargin: "-18% 0px -68% 0px", threshold: [0, 1] }
    );

    headings.forEach((heading) => this.observer?.observe(heading));

    const hashId = safeDecodeURIComponent(window.location.hash.slice(1)) ?? "";
    const initialHeading = hashId && headings.some((heading) => heading.id === hashId) ? hashId : headings[0].id;
    this.markActive(elements.tocList, initialHeading);
    return hashId || null;
  }

  markActive(tocList: HTMLUListElement, id: string): void {
    if (this.activeHeadingId === id) return;
    if (this.activeHeadingId) {
      tocList.querySelector<HTMLAnchorElement>(`a[data-heading-id="${cssEscape(this.activeHeadingId)}"]`)?.classList.remove("is-active");
    }
    tocList.querySelector<HTMLAnchorElement>(`a[data-heading-id="${cssEscape(id)}"]`)?.classList.add("is-active");
    this.activeHeadingId = id;
  }
}

const ensureHeadingAnchor = (heading: HTMLElement, label: string): void => {
  if (heading.querySelector(".heading-anchor")) return;
  const anchor = document.createElement("a");
  anchor.className = "heading-anchor";
  anchor.href = `#${encodeURIComponent(heading.id)}`;
  anchor.dataset.headingId = heading.id;
  anchor.setAttribute("aria-label", `Open anchor for ${label}`);
  anchor.textContent = " #";
  heading.tabIndex = -1;
  heading.append(anchor);
};

const slugifyHeading = (value: string): string => {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
};

const uniqueHeadingId = (base: string, usedIds: Set<string>): string => {
  let candidate = base || "section";
  let counter = 2;
  while (usedIds.has(candidate)) {
    candidate = `${base}-${counter}`;
    counter += 1;
  }
  usedIds.add(candidate);
  return candidate;
};

const cssEscape = (value: string): string => {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") return CSS.escape(value);
  return value.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
};

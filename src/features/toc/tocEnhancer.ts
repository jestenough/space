import { safeDecodeURIComponent } from "@/core/url";

const headingSelector = "h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]";

const ensureHeadingAnchors = (root: HTMLElement): HTMLElement[] => {
  const headings = Array.from(root.querySelectorAll<HTMLElement>(headingSelector));
  headings.forEach((heading) => {
    if (heading.querySelector(".heading-anchor")) return;
    const label = heading.textContent?.replace(/#/g, "").trim() || heading.id;
    const anchor = document.createElement("a");
    anchor.className = "heading-anchor";
    anchor.href = `#${encodeURIComponent(heading.id)}`;
    anchor.dataset.headingId = heading.id;
    anchor.setAttribute("aria-label", `Open anchor for ${label}`);
    anchor.textContent = " #";
    heading.classList.add("anchored-heading", "is-clickable-anchor");
    heading.tabIndex = -1;
    heading.append(anchor);
  });
  return headings;
};

const cssEscape = (value: string): string => {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") return CSS.escape(value);
  return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
};

export const scrollToHeading = (id: string): void => {
  const target = document.getElementById(id);
  if (!target) return;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--header-height-offset").trim();
  const value = Number.parseFloat(raw);
  const headerOffset = Number.isFinite(value) ? value * (raw.endsWith("rem") ? (Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16) : 1) : 108;
  const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - headerOffset);
  window.scrollTo({ top, behavior: reducedMotion ? "auto" : "smooth" });
};

export const initTocEnhancer = (): void => {
  const root = document.querySelector<HTMLElement>("[data-file-content]");
  const tocPanel = document.getElementById("toc-panel");
  const tocList = document.getElementById("toc-list");
  if (!root || !tocPanel || !(tocList instanceof HTMLUListElement)) return;

  const headings = ensureHeadingAnchors(root);
  if (headings.length === 0 || tocList.children.length === 0) {
    tocPanel.classList.add("hidden");
    return;
  }

  let activeId = "";
  let scrollLockUntil = 0;

  const markActive = (id: string): void => {
    if (id === activeId) return;
    activeId = id;
    tocList.querySelectorAll<HTMLAnchorElement>("a[data-heading-id]").forEach((link) => {
      link.classList.toggle("is-active", link.dataset.headingId === id);
    });
  };

  const observer = new IntersectionObserver((entries) => {
    if (performance.now() < scrollLockUntil) return;
    const activeEntry = entries
      .filter((entry) => entry.isIntersecting)
      .sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top)[0];
    if (activeEntry?.target.id) markActive(activeEntry.target.id);
  }, { rootMargin: "-18% 0px -68% 0px", threshold: [0, 1] });

  headings.forEach((heading) => observer.observe(heading));

  const hashId = safeDecodeURIComponent(window.location.hash.slice(1)) ?? "";
  const initialId = hashId && headings.some((heading) => heading.id === hashId) ? hashId : headings[0]?.id;
  if (initialId) markActive(initialId);

  tocList.addEventListener("click", (event) => {
    const link = (event.target as HTMLElement | null)?.closest<HTMLAnchorElement>("a[data-heading-id]");
    if (!link?.dataset.headingId) return;
    event.preventDefault();
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}#${encodeURIComponent(link.dataset.headingId)}`);
    scrollLockUntil = performance.now() + 720;
    markActive(link.dataset.headingId);
    scrollToHeading(link.dataset.headingId);
  });
};

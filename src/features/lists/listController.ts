const DEFAULT_PAGE_SIZE = 4;
const PAGE_SIZE_OPTIONS = new Set([4, 8, 16, 32]);

type SortDirection = "asc" | "desc";
type Item = { element: HTMLElement; search: string };

const normalizeQuery = (value: string): string => value.trim().toLowerCase();
const isVisibleRoot = (root: HTMLElement): boolean => !root.classList.contains("hidden");
const positiveInt = (value: string | null): number => {
  const parsed = value ? Number.parseInt(value, 10) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
};
const pageSize = (value: string | null): number => {
  const parsed = value ? Number.parseInt(value, 10) : Number.NaN;
  return PAGE_SIZE_OPTIONS.has(parsed) ? parsed : DEFAULT_PAGE_SIZE;
};
const sortDataKey = (value: string): { key: string; direction: SortDirection } => {
  const [key = "date", direction = "desc"] = value.split("-");
  return { key, direction: direction === "asc" ? "asc" : "desc" };
};
const datasetKey = (key: string): string => `sort${key.charAt(0).toUpperCase()}${key.slice(1)}`;

export class ListController {
  private readonly list: HTMLElement | null;
  private readonly searchInput: HTMLInputElement | null;
  private readonly sortSelect: HTMLSelectElement | null;
  private readonly sizeSelect: HTMLSelectElement | null;
  private readonly prevButton: HTMLButtonElement | null;
  private readonly nextButton: HTMLButtonElement | null;
  private readonly pageInfo: HTMLElement | null;
  private readonly items: Item[];
  private readonly defaultSortValue: string;
  private currentPage = 1;

  constructor(private readonly root: HTMLElement) {
    this.list = root.querySelector<HTMLElement>("[data-list-items]");
    this.searchInput = root.querySelector<HTMLInputElement>("[data-list-search]");
    this.sortSelect = root.querySelector<HTMLSelectElement>("[data-list-sort]");
    this.sizeSelect = root.querySelector<HTMLSelectElement>("[data-list-size]");
    this.prevButton = root.querySelector<HTMLButtonElement>("[data-list-prev]");
    this.nextButton = root.querySelector<HTMLButtonElement>("[data-list-next]");
    this.pageInfo = root.querySelector<HTMLElement>("[data-list-page-info]");
    const elements = this.list ? Array.from(this.list.querySelectorAll<HTMLElement>("[data-list-item]")) : [];
    this.items = elements.map((element) => ({
      element,
      search: normalizeQuery(element.dataset.search || element.textContent || "")
    }));
    this.defaultSortValue = this.sortSelect?.value || "";
  }

  init(): void {
    if (!this.list || this.items.length === 0) return;

    const params = new URLSearchParams(window.location.search);
    if (this.searchInput) this.searchInput.value = params.get("q") ?? this.searchInput.value;
    if (this.sortSelect && params.get("sort")) this.sortSelect.value = params.get("sort") || this.sortSelect.value;
    if (this.sizeSelect && params.get("size")) this.sizeSelect.value = String(pageSize(params.get("size")));
    this.currentPage = positiveInt(params.get("page"));

    this.searchInput?.addEventListener("input", () => {
      this.currentPage = 1;
      this.render();
    });
    this.sortSelect?.addEventListener("change", () => {
      this.currentPage = 1;
      this.render();
    });
    this.sizeSelect?.addEventListener("change", () => {
      this.currentPage = 1;
      this.render();
    });
    this.prevButton?.addEventListener("click", () => {
      this.currentPage = Math.max(1, this.currentPage - 1);
      this.render();
    });
    this.nextButton?.addEventListener("click", () => {
      this.currentPage += 1;
      this.render();
    });

    this.render();
  }

  render(): void {
    if (!this.list || !isVisibleRoot(this.root)) return;

    const query = normalizeQuery(this.searchInput?.value || "");
    const sortValue = this.sortSelect?.value || "date-desc";
    const pageSizeValue = pageSize(this.sizeSelect?.value || null);
    const filtered = this.items.filter((item) => !query || item.search.includes(query));
    const filteredSet = new Set(filtered);
    const ordered = filtered.slice().sort((left, right) => this.compare(left.element, right.element, sortValue));
    const hidden = this.items.filter((item) => !filteredSet.has(item));

    this.list.replaceChildren(...ordered.map((item) => item.element), ...hidden.map((item) => item.element));

    const totalPages = Math.max(1, Math.ceil(ordered.length / pageSizeValue));
    this.currentPage = Math.min(this.currentPage, totalPages);
    const start = (this.currentPage - 1) * pageSizeValue;
    const end = start + pageSizeValue;

    ordered.forEach((item, index) => {
      item.element.hidden = index < start || index >= end;
    });
    hidden.forEach((item) => {
      item.element.hidden = true;
    });

    if (this.pageInfo) this.pageInfo.textContent = `${this.currentPage}/${totalPages}`;
    if (this.prevButton) this.prevButton.disabled = this.currentPage <= 1;
    if (this.nextButton) this.nextButton.disabled = this.currentPage >= totalPages;

    this.setProcessField("shown", String(Math.max(0, Math.min(pageSizeValue, ordered.length - start))));
    this.setProcessField("total", String(ordered.length));
    this.setProcessField("page", String(this.currentPage));
    this.setProcessField("pages", String(totalPages));

    const params = new URLSearchParams(window.location.search);
    if (query) params.set("q", query); else params.delete("q");
    if (this.sortSelect && this.sortSelect.value && this.sortSelect.value !== this.defaultSortValue) params.set("sort", this.sortSelect.value); else params.delete("sort");
    if (pageSizeValue !== DEFAULT_PAGE_SIZE) params.set("size", String(pageSizeValue)); else params.delete("size");
    if (this.currentPage > 1) params.set("page", String(this.currentPage)); else params.delete("page");
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}${window.location.hash}`;
    window.history.replaceState({}, "", next);
  }

  private compare(left: HTMLElement, right: HTMLElement, sortValue: string): number {
    const { key, direction } = sortDataKey(sortValue);
    const field = datasetKey(key);
    const leftValue = left.dataset[field] || "";
    const rightValue = right.dataset[field] || "";
    const numeric = key === "count";
    const result = numeric
      ? Number(leftValue) - Number(rightValue)
      : leftValue.localeCompare(rightValue, undefined, { numeric: true, sensitivity: "base" });
    return direction === "asc" ? result : -result;
  }

  private setProcessField(name: string, value: string): void {
    document.querySelectorAll<HTMLElement>(`[data-process-field="${name}"]`).forEach((element) => {
      element.textContent = value;
    });
  }
}

import type { InfoFileMeta } from "@/core/types";
import { safeDecodeURIComponent } from "@/core/url";

const OWNER = "root";
const GROUP = "operators";
const READABLE_PUBLIC_FILE = "-rw-rw-r--";
const INFO_PUBLIC_BASE = "/info";

type InfoFileInput = Omit<InfoFileMeta, "routeSlug">;

export const toRouteSlug = (fileSlug: string): string => {
  return fileSlug.replace(/\.[^.]+$/, "").trim().toLowerCase();
};

const makeInfoFile = (file: InfoFileInput): InfoFileMeta => ({
  ...file,
  routeSlug: toRouteSlug(file.slug)
});

export const INFO_FILES: readonly InfoFileMeta[] = [
  makeInfoFile({
    slug: "README.md",
    publicPath: `${INFO_PUBLIC_BASE}/README.md`,
    sourcePath: "content/info/README.md",
    kind: "markdown",
    size: 509,
    modified: "2026-05-02",
    permissions: READABLE_PUBLIC_FILE,
    owner: OWNER,
    group: GROUP,
    title: { ru: "README.md", en: "README.md" },
    description: {
      ru: "Карта пространства autophany.space: запуск, сборка, контент и PDF pipeline.",
      en: "A map of autophany.space: setup, build, content, and the PDF pipeline."
    }
  }),
  makeInfoFile({
    slug: "ABOUT.md",
    publicPath: `${INFO_PUBLIC_BASE}/ABOUT.md`,
    sourcePath: "content/info/ABOUT.md",
    kind: "markdown",
    size: 423,
    modified: "2026-05-02",
    permissions: READABLE_PUBLIC_FILE,
    owner: OWNER,
    group: GROUP,
    title: { ru: "ABOUT.md", en: "ABOUT.md" },
    description: {
      ru: "Описание проекта autophany.space, его тона и внутренней логики.",
      en: "A description of autophany.space, its tone, and its internal logic."
    }
  }),
  makeInfoFile({
    slug: "CHANGELOG.txt",
    publicPath: `${INFO_PUBLIC_BASE}/CHANGELOG.txt`,
    sourcePath: "content/info/CHANGELOG.txt",
    kind: "text",
    size: 387,
    modified: "2026-05-02",
    permissions: READABLE_PUBLIC_FILE,
    owner: OWNER,
    group: GROUP,
    title: { ru: "CHANGELOG.txt", en: "CHANGELOG.txt" },
    description: {
      ru: "Журнал изменений интерфейса, структуры и сборочного pipeline.",
      en: "Change log for the interface, structure, and build pipeline."
    }
  }),
  makeInfoFile({
    slug: "MANIFEST.local",
    publicPath: `${INFO_PUBLIC_BASE}/MANIFEST.local`,
    sourcePath: "content/info/MANIFEST.local",
    kind: "text",
    size: 338,
    modified: "2026-05-02",
    permissions: READABLE_PUBLIC_FILE,
    owner: OWNER,
    group: GROUP,
    title: { ru: "MANIFEST.local", en: "MANIFEST.local" },
    description: {
      ru: "Локальные правила пространства: простота, единый источник истины, read-only доступ.",
      en: "Local rules: simplicity, one source of truth, and read-only public access."
    }
  })
];

const infoContentCache = new Map<string, Promise<string>>();

export const findInfoFile = (slug: string): InfoFileMeta | undefined => {
  const decoded = safeDecodeURIComponent(slug) ?? slug;
  const normalized = decoded.trim().toLowerCase();
  return INFO_FILES.find((file) => file.slug.toLowerCase() === normalized || file.routeSlug === normalized);
};

export const renderInfoFileHtml = async (file: InfoFileMeta, _lang: string): Promise<string> => {
  const content = await loadInfoFileContent(file);
  const body = file.kind === "markdown" ? renderMarkdown(content) : renderPlainText(content);
  return `<section class="file-document" data-source="${escapeHtml(file.sourcePath)}">${body}</section>`;
};

const loadInfoFileContent = async (file: InfoFileMeta): Promise<string> => {
  const cached = infoContentCache.get(file.publicPath);
  if (cached) return cached;

  const request = fetch(file.publicPath, { cache: "force-cache" })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Unable to load ${file.publicPath}: ${response.status}`);
      return response.text();
    })
    .catch((error: unknown) => {
      infoContentCache.delete(file.publicPath);
      throw error;
    });

  infoContentCache.set(file.publicPath, request);
  return request;
};

const renderMarkdown = (markdown: string): string => {
  const lines = stripLeadingMarkdownHeading(markdown).replace(/\r\n/g, "\n").split("\n");
  const html: string[] = [];
  let paragraph: string[] = [];
  let listItems: string[] = [];

  const flushParagraph = (): void => {
    if (paragraph.length === 0) return;
    html.push(`<p>${inlineMarkdown(escapeHtml(paragraph.join(" ")))}</p>`);
    paragraph = [];
  };

  const flushList = (): void => {
    if (listItems.length === 0) return;
    html.push(`<ul>${listItems.map((item) => `<li>${inlineMarkdown(escapeHtml(item))}</li>`).join("")}</ul>`);
    listItems = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      html.push(`<h${level}>${inlineMarkdown(escapeHtml(heading[2]))}</h${level}>`);
      continue;
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      listItems.push(bullet[1]);
      continue;
    }

    flushList();
    paragraph.push(trimmed);
  }

  flushParagraph();
  flushList();
  return html.join("");
};

const stripLeadingMarkdownHeading = (markdown: string): string => {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const firstContentIndex = lines.findIndex((line) => line.trim().length > 0);
  if (firstContentIndex === -1) return markdown;
  if (/^#{1,3}\s+/.test(lines[firstContentIndex].trim())) {
    lines.splice(firstContentIndex, 1);
    return lines.join("\n").replace(/^\n+/, "");
  }
  return markdown;
};

const renderPlainText = (value: string): string => `<pre class="info-file-pre">${escapeHtml(value.trimEnd())}</pre>`;

const inlineMarkdown = (value: string): string => value.replace(/`([^`]+)`/g, "<code>$1</code>");

const escapeHtml = (value: string): string => {
  return value.replace(/[&<>\"]/g, (char) => {
    if (char === "&") return "&amp;";
    if (char === "<") return "&lt;";
    if (char === ">") return "&gt;";
    return "&quot;";
  });
};

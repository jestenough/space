import { tagPath } from "@/router/routePaths";
import type { ArticleMeta, InfoFileMeta, Lang, SectionMeta } from "@/core/types";
import { escapeHtml } from "@/core/escape";

const PUBLIC_FILE_PERMISSIONS = "-rw-rw-r--";
const PUBLIC_FILE_OWNER = "root";
const PUBLIC_FILE_GROUP = "operators";
const SHELL_PROMPT = "guest@cray-1:~$";

export const shellCommandText = (command: string): string => `${SHELL_PROMPT} ${command}`;

export const shellCommandMarkup = (command: string): string => {
  const normalized = command.startsWith(`${SHELL_PROMPT} `) ? command.slice(SHELL_PROMPT.length + 1) : command;
  return `<span class="stat-command"><span class="shell-prompt">${SHELL_PROMPT}</span><span class="shell-gap"> </span><span class="shell-cmd">${escapeHtml(normalized)}</span></span>`;
};

export function homeCommand(): string {
  return shellCommandText("ls -p | grep -v /");
}

type PipelineOptions = { sortBy?: string; pageSize?: number; query?: string; maxColumns?: number };
type TagPipelineOptions = { sortBy?: string; pageSize?: number; query?: string; maxColumns?: number };

export function articlesCommand(options: PipelineOptions = {}): string {
  const base = shellCommandText("ls -p | grep -v /");
  const filtered = options.query ? `${base} | grep -i -- "${shellEscape(options.query)}"` : base;
  return withContinuation([filtered, sortPipeline(options.sortBy), `head -n ${options.pageSize ?? 4}`], options.maxColumns);
}

export function tagsCommand(options: TagPipelineOptions = {}): string {
  const base = shellCommandText('grep -R "tag:" . | cut -d: -f2 | cut -d" " -f1');
  const filtered = options.query ? `${base} | grep -i -- "${shellEscape(options.query)}"` : base;
  return withContinuation([filtered, tagSortPipeline(options.sortBy), `head -n ${options.pageSize ?? 4}`], options.maxColumns);
}

export function headerCommand(
  panel: string,
  tag?: string,
  options: PipelineOptions = {}
): string {
  if (panel === "articles") return articlesCommand(options);
  if (panel === "tags") return tag ? tagSearchCommand(tag, options) : tagsCommand(options);
  return homeCommand();
}

export function sidebarCommand(): string {
  return shellCommandText("ls -d */");
}

export function articleOpenCommand(slug: string): string {
  return shellCommandText(`cat ~/articles/${slug}.tex`);
}

export function infoFileOpenCommand(section: string, slug: string): string {
  return shellCommandText(`cat ${displayFilePath(section, slug)}`);
}

export function tagSearchCommand(tag: string, options: PipelineOptions = {}): string {
  const base = shellCommandText(`grep -R "tag:${shellEscape(tag)}" .`);
  const filtered = options.query ? `${base} | grep -i -- "${shellEscape(options.query)}"` : base;
  return withContinuation([filtered, sortPipeline(options.sortBy), `head -n ${options.pageSize ?? 4}`], options.maxColumns);
}

type SnapshotArgs = {
  lang: Lang;
  panel: string;
  tag?: string;
  query?: string;
  article?: ArticleMeta;
  infoFile?: InfoFileMeta;
  section?: SectionMeta;
  files?: readonly InfoFileMeta[];
  matches?: number;
  words?: number;
  chars?: number;
};

export function processSnapshot(args: SnapshotArgs): string {
  if (args.article) return articleMetadataSnapshot(args);
  if (args.infoFile) return infoFileMetadataSnapshot(args.infoFile, args.lang);

  const lines: string[] = [
    shellCommandText(`statfs ${displaySectionPath(args.section?.slug ?? args.panel)}`),
    "File system : autophanyfs",
    `Mounted on  : ${mountedPath(args)}`,
    `Type        : ${args.section?.system ? "system-section" : "section"}`,
    "Flags       : ro, localized, indexed",
    "──────────────────────────────",
    ...sectionStats(args).map(([key, value]) => `${key.padEnd(11, " ")}: ${value}`)
  ];

  if (args.panel === "articles") {
    lines.push(
      "scope   : ./",
      `filter  : ${args.query ? `grep ${args.query}` : "none"}`,
      `matches : ${args.matches ?? 0}`
    );
  }
  if (args.panel === "tags") {
    lines.push(args.tag ? `scope   : tag:${args.tag}` : "scope   : tags-index");
    if (args.tag) lines.push(`matches : ${args.matches ?? 0}`);
  }

  return lines.join("\n");
}

export function processSnapshotHtml(args: SnapshotArgs): string {
  if (args.article) return articleMetadataSnapshotHtml(args);
  if (args.infoFile) return infoFileMetadataSnapshotHtml(args.infoFile, args.lang);
  return processSnapshotStatusHtml(args);
}

const processSnapshotStatusHtml = (args: SnapshotArgs): string => {
  const rows = processStatusRows(args);
  return [
    shellCommandHtml(`statfs ${displaySectionPath(args.section?.slug ?? args.panel)}`),
    statRow("File system", "autophanyfs"),
    statRow("Mounted on", mountedPath(args)),
    statRow("Type", args.section?.system ? "system-section" : "section"),
    statRow("Flags", "ro, localized, indexed"),
    '<span class="meta-rule" aria-hidden="true"></span>',
    ...rows.map(([key, value]) => statRow(key, value))
  ].join("");
};

const processStatusRows = (args: SnapshotArgs): Array<[string, string]> => {
  if (args.panel !== "articles" && args.panel !== "tags") return sectionStats(args);
  const rows: Array<[string, string]> = [["mode", args.panel], ["lang", args.lang]];
  if (args.panel === "articles") {
    rows.push(["scope", "./"], ["filter", args.query ? "grep " + args.query : "none"], ["matches", String(args.matches ?? 0)]);
  }
  if (args.panel === "tags") {
    rows.push(["scope", args.tag ? "tag:" + args.tag : "tags-index"]);
    if (args.query) rows.push(["filter", "grep " + args.query]);
    rows.push(["matches", String(args.matches ?? 0)]);
  }
  return rows;
};

const sectionStats = (args: SnapshotArgs): Array<[string, string]> => {
  const files = args.files ?? [];
  const languages = [...new Set(files.flatMap((file) => file.languages))].sort();
  const translated = files.filter((file) => file.languages.includes(args.lang)).length;
  const rawFiles = files.filter((file) => file.format !== "tex").length;
  const texFiles = files.filter((file) => file.format === "tex").length;
  const articles = files.filter((file) => file.type === "article").length;
  const downloads = files.filter((file) => file.downloadPath).length;
  return [
    ["files", String(files.length)],
    ["sources", String(files.reduce((total, file) => total + file.languages.length, 0))],
    ["languages", languages.join(", ") || args.lang],
    ["translated", `${translated}/${files.length}`],
    ["raw files", String(rawFiles)],
    ["tex files", String(texFiles)],
    ["articles", String(articles)],
    ["downloads", String(downloads)],
    ["index", `generated/sections/${args.section?.slug ?? args.panel}.json`]
  ];
};

const mountedPath = (args: SnapshotArgs): string => {
  const section = args.section?.slug ?? args.panel;
  return args.section?.system || section === "site" ? `/${args.lang}` : `/${args.lang}/${section}`;
};

const articleMetadataSnapshot = (args: SnapshotArgs): string => {
  const article = args.article;
  if (!article) return "";
  const filePath = `~/articles/${article.slug}.tex`;
  const stamp = `${article.date} 00:00:00 +0000`;
  return [
    shellCommandText(`stat ${filePath}`),
    `File   : ${filePath}`,
    `Size   : ${estimatedSize(article)}`,
    "Blocks : 8",
    "IO     : 4096 regular file",
    "Device : autophanyfs",
    "Inode  : 042",
    "Links  : 1",
    "Access : (0664/" + PUBLIC_FILE_PERMISSIONS + ")",
    "Uid    : (0/" + PUBLIC_FILE_OWNER + ")",
    "Gid    : (42/" + PUBLIC_FILE_GROUP + ")",
    `Birth  : ${stamp}`,
    `Mtime  : ${stamp}`,
    "──────────────────────────────",
    `slug   : ${article.slug}`,
    `lang   : ${args.lang}`,
    `langs  : ${article.languages.join(", ")}`,
    `tags   : ${article.tags.map((tag) => `#${tag}`).join(" ")}`,
    `words  : ${args.words ?? 0}`,
    `chars  : ${args.chars ?? 0}`,
    `pdf    : ~/articles/${article.slug}.pdf`
  ].join("\n");
};

const articleMetadataSnapshotHtml = (args: SnapshotArgs): string => {
  const article = args.article;
  if (!article) return "";
  const filePath = `~/articles/${article.slug}.tex`;
  const stamp = `${article.date} 00:00:00 +0000`;
  const tags = article.tags
    .map((tag) => `<a class="meta-tag-link" href="${tagPath(args.lang, tag)}" data-internal="true">#${escapeHtml(tag)}</a>`)
    .join(" ");

  return [
    shellCommandHtml(`stat ${filePath}`),
    statRow("File", filePath),
    statRow("Size", String(estimatedSize(article))),
    statRow("Blocks", "8"),
    statRow("IO", "4096 regular file"),
    statRow("Device", "autophanyfs"),
    statRow("Inode", "042"),
    statRow("Links", "1"),
    statRow("Access", `(0664/${PUBLIC_FILE_PERMISSIONS})`),
    statRow("Uid", `(0/${PUBLIC_FILE_OWNER})`),
    statRow("Gid", `(42/${PUBLIC_FILE_GROUP})`),
    statRow("Birth", stamp),
    statRow("Mtime", stamp),
    `<span class="meta-rule" aria-hidden="true"></span>`,
    statRow("slug", article.slug),
    statRow("lang", args.lang),
    statRow("langs", article.languages.join(", ")),
    statRowHtml("tags", tags),
    statRow("words", String(args.words ?? 0)),
    statRow("chars", String(args.chars ?? 0)),
    statRow("pdf", `~/articles/${article.slug}.pdf`)
  ].join("");
};

const infoFileMetadataSnapshot = (file: InfoFileMeta, lang: Lang): string => {
  const filePath = displayFilePath(file.section, file.slug);
  const stamp = `${file.date || "1970-01-01"} 00:00:00 +0000`;

  return [
    shellCommandText(`stat ${filePath}`),
    `File   : ${filePath}`,
    `Size   : 0`,
    "Blocks : 8",
    "IO     : 4096 regular file",
    "Device : autophanyfs",
    "Inode  : 021",
    "Links  : 1",
    "Access : (0664/" + PUBLIC_FILE_PERMISSIONS + ")",
    "Uid    : (0/" + PUBLIC_FILE_OWNER + ")",
    "Gid    : (42/" + PUBLIC_FILE_GROUP + ")",
    `Birth  : ${stamp}`,
    `Mtime  : ${stamp}`,
    "──────────────────────────────",
    `name   : ${file.slug}`,
    `lang   : ${lang}`,
    `type   : service-file`
  ].join("\n");
};

const infoFileMetadataSnapshotHtml = (file: InfoFileMeta, lang: Lang): string => {
  const filePath = displayFilePath(file.section, file.slug);
  const stamp = `${file.date || "1970-01-01"} 00:00:00 +0000`;
  return [
    shellCommandHtml(`stat ${filePath}`),
    statRow("File", filePath),
    statRow("Size", "0"),
    statRow("Blocks", "8"),
    statRow("IO", "4096 regular file"),
    statRow("Device", "autophanyfs"),
    statRow("Inode", "021"),
    statRow("Links", "1"),
    statRow("Access", `(0664/${PUBLIC_FILE_PERMISSIONS})`),
    statRow("Uid", `(0/${PUBLIC_FILE_OWNER})`),
    statRow("Gid", `(42/${PUBLIC_FILE_GROUP})`),
    statRow("Birth", stamp),
    statRow("Mtime", stamp),
    `<span class="meta-rule" aria-hidden="true"></span>`,
    statRow("name", file.slug),
    statRow("lang", lang),
    statRow("type", "service-file")
  ].join("");
};

const shellCommandHtml = shellCommandMarkup;

const displaySectionPath = (section: string): string => section === "site" ? "~" : `~/${section}`;

const displayFilePath = (section: string, slug: string): string => section === "site" ? `~/${slug}` : `~/${section}/${slug}`;

const statRow = (key: string, value: string): string => statRowHtml(key, escapeHtml(value));

const statRowHtml = (key: string, valueHtml: string): string => `<span class="stat-row"><span class="stat-key">${escapeHtml(key)}</span><span class="stat-sep">:</span><span class="stat-value">${valueHtml}</span></span>`;

const sortPipeline = (sortBy?: string): string => {
  if (sortBy === "date-asc") return "sort -k 6,7";
  if (sortBy === "title-asc") return "sort -f";
  if (sortBy === "title-desc") return "sort -fr";
  return "sort -k 6,7 -r";
};

const tagSortPipeline = (sortBy?: string): string => {
  if (sortBy === "name-desc") return "sort -fr";
  if (sortBy === "count-desc") return "sort -k 2,2nr";
  if (sortBy === "count-asc") return "sort -k 2,2n";
  return "sort -f";
};

const withContinuation = (commands: string[], maxColumns = Number.POSITIVE_INFINITY): string => {
  const [head, ...tail] = commands.filter(Boolean);
  if (!head || tail.length === 0) return head ?? "";
  const joined = [head, ...tail.map((part) => `| ${part}`)].join(" ");
  if (joined.length <= maxColumns) return joined;

  const lines: string[] = [head];
  let currentLength = head.length;
  for (const part of tail) {
    const pipe = `| ${part}`;
    const nextLength = currentLength + 1 + pipe.length;
    if (nextLength <= maxColumns) {
      lines[lines.length - 1] += ` ${pipe}`;
      currentLength = nextLength;
      continue;
    }
    lines[lines.length - 1] += " \\";
    const next = `  ${pipe}`;
    lines.push(next);
    currentLength = next.length;
  }
  return lines.join("\n");
};

const shellEscape = (value: string): string => value.replace(/["`\\$]/g, "\\$&");

const estimatedSize = (article: ArticleMeta): number => 640 + article.slug.length * 12 + article.tags.join(" ").length * 8;

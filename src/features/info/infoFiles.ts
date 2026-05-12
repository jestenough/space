import { SYSTEM_SECTION } from "@/core/config";
import type { InfoFileMeta, Lang, SectionMeta } from "@/core/types";
import { safeDecodeURIComponent } from "@/core/url";
import { fetchGeneratedJson, fetchGeneratedText, PromiseLruCache } from "@/services/generatedAssets";
import { generatedInfoFileHtmlPath, generatedSectionIndexPath, generatedSectionsIndexPath } from "@/services/generatedPaths";
import { missingTranslationHtml } from "@/ui/missingTranslation";

const MAX_HTML_CACHE_ITEMS = 40;
const MAX_SECTION_CACHE_ITEMS = 64;
const sectionCache = new PromiseLruCache<InfoFileMeta[]>(MAX_SECTION_CACHE_ITEMS);
let sectionsPromise: Promise<SectionMeta[]> | null = null;
const htmlCache = new PromiseLruCache<string>(MAX_HTML_CACHE_ITEMS);

export const toRouteSlug = (fileSlug: string): string => fileSlug.replace(/\.[^.]+$/, "").trim().toLowerCase();

export const loadSections = (): Promise<SectionMeta[]> => {
  sectionsPromise ??= fetchGeneratedJson(generatedSectionsIndexPath()).then((value) => {
    if (!Array.isArray(value)) throw new Error("Invalid sections index");
    return value.map(normalizeSection);
  });
  return sectionsPromise;
};

export const loadSectionIndex = (section: string): Promise<InfoFileMeta[]> => {
  const key = section.trim().toLowerCase() || SYSTEM_SECTION;
  const cached = sectionCache.get(key);
  if (cached) return cached;
  const request = fetchGeneratedJson(generatedSectionIndexPath(key)).then((value) => {
    if (!Array.isArray(value)) throw new Error("Invalid section index");
    return value.map(normalizeFile);
  });
  sectionCache.set(key, request);
  return request;
};

export const findInfoFile = async (section: string, slug: string): Promise<InfoFileMeta | undefined> => {
  const decoded = safeDecodeURIComponent(slug) ?? slug;
  const normalized = decoded.trim().toLowerCase();
  const files = await loadSectionIndex(section);
  return files.find((file) => file.slug.toLowerCase() === normalized || toRouteSlug(file.slug) === normalized);
};

export const renderInfoFileHtml = async (file: InfoFileMeta, lang: Lang): Promise<string> => {
  if (!file.languages.includes(lang)) return missingTranslationHtml(lang, file.languages);
  return loadFileHtml(file, lang);
};

export const fileHtmlPath = generatedInfoFileHtmlPath;

const loadFileHtml = (file: InfoFileMeta, lang: Lang): Promise<string> => {
  const path = fileHtmlPath(file, lang);
  const cached = htmlCache.get(path);
  if (cached) return cached;
  const request = fetchGeneratedText(path);
  htmlCache.set(path, request);
  return request;
};

const normalizeSection = (value: unknown): SectionMeta => {
  if (!isRecord(value)) throw new Error("Invalid section metadata");
  return {
    slug: string(value.slug),
    label: langRecord(value.label),
    title: langRecord(value.title),
    description: langRecord(value.description),
    system: Boolean(value.system),
    count: typeof value.count === "number" ? value.count : 0
  };
};

const normalizeFile = (value: unknown): InfoFileMeta => {
  if (!isRecord(value)) throw new Error("Invalid file metadata");
  const section = string(value.section);
  const slug = string(value.slug);
  return {
    section,
    slug,
    label: langRecord(value.label),
    type: string(value.type || "text"),
    format: string(value.format || "text"),
    date: string(value.date || ""),
    title: langRecord(value.title),
    description: langRecord(value.description),
    languages: stringArray(value.languages),
    translations: isRecord(value.translations) ? Object.fromEntries(Object.entries(value.translations).filter(([, path]) => typeof path === "string")) as Partial<Record<Lang, string>> : undefined,
    canonicalPath: typeof value.canonicalPath === "string" ? value.canonicalPath : undefined,
    downloadPath: typeof value.downloadPath === "string" ? value.downloadPath : null
  };
};

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const string = (value: unknown): string => typeof value === "string" ? value : "";
const stringArray = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.length > 0) : [];
const langRecord = (value: unknown): Record<string, string> => isRecord(value) ? Object.fromEntries(Object.entries(value).filter(([, text]) => typeof text === "string" && text.length > 0)) as Record<string, string> : {};

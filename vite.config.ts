import { defineConfig, type Plugin } from "vite";
import viteCompression from "vite-plugin-compression";
import { resolve, extname } from "node:path";
import { fileURLToPath, URL } from "node:url";
import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import { mkdir, readdir, rm, copyFile } from "node:fs/promises";

type SectionRecord = {
  slug: string;
  system?: boolean;
};

type FileRecord = {
  slug: string;
  type?: string;
  tags?: string[];
  languages?: string[];
  downloadPath?: string | null;
};

type RouteData = {
  articleSlugs: Set<string>;
  articleLangs: Map<string, Set<string>>;
  tagNames: Set<string>;
  sections: Set<string>;
  systemSection: string;
  filesBySection: Map<string, Set<string>>;
  fileBySectionSlug: Map<string, FileRecord>;
  downloads: Map<string, string>;
};

type ViteMiddlewareServer = {
  middlewares: {
    use: (
      fn: (
        req: { url?: string },
        res: {
          statusCode: number;
          setHeader?: (key: string, value: string) => void;
        },
        next: () => void,
      ) => void,
    ) => void;
  };
};

const rootDir = fileURLToPath(new URL(".", import.meta.url));
const generatedDir = resolve(rootDir, "generated");
const contentDir = resolve(rootDir, "content");

const distGeneratedDir = resolve(rootDir, "dist", "generated");
const distMediaDir = resolve(rootDir, "dist", "media");

const LANGUAGE_TAG_PATTERN = /^[a-z]{2,3}(?:-[A-Z]{2})?$/;
const SYSTEM_SECTION = "site";

const safeDecodeURIComponent = (value: string): string | null => {
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
};

const normalizeLang = (value: string): string => {
  const [base = "", region] = value.trim().split("-");
  return region ? `${base.toLowerCase()}-${region.toUpperCase()}` : base.toLowerCase();
};

const isValidLang = (value: string | undefined): boolean => {
  return Boolean(value && LANGUAGE_TAG_PATTERN.test(normalizeLang(value)));
};

const loadRouteData = (): RouteData => {
  const articleSlugs = new Set<string>();
  const articleLangs = new Map<string, Set<string>>();
  const tagNames = new Set<string>();
  const sections = new Set<string>([SYSTEM_SECTION, "about", "projects", "notes", "articles", "tags"]);
  const filesBySection = new Map<string, Set<string>>();
  const fileBySectionSlug = new Map<string, FileRecord>();
  const downloads = new Map<string, string>();
  let systemSection = SYSTEM_SECTION;

  const sectionsPath = [
    resolve(generatedDir, "sections-index.json"),
    resolve(distGeneratedDir, "sections-index.json"),
  ].find((path) => existsSync(path));

  if (sectionsPath) {
    const items = JSON.parse(readFileSync(sectionsPath, "utf8")) as SectionRecord[];
    for (const section of items) {
      sections.add(section.slug);
      if (section.system) systemSection = section.slug;
    }

    for (const section of sections) {
      const indexPath = [
        resolve(generatedDir, "sections", `${section}.json`),
        resolve(distGeneratedDir, "sections", `${section}.json`),
      ].find((path) => existsSync(path));
      if (!indexPath) continue;
      const files = JSON.parse(readFileSync(indexPath, "utf8")) as FileRecord[];
      const slugs = new Set<string>();
      for (const file of files) {
        slugs.add(file.slug);
        fileBySectionSlug.set(`${section}/${file.slug}`, file);
        if (file.downloadPath) downloads.set(file.downloadPath, resolve(contentDir, section, file.slug, sourceName(file.slug, file.downloadPath)));
        if (file.type === "article") {
          articleSlugs.add(file.slug);
          articleLangs.set(file.slug, new Set((file.languages ?? []).map(normalizeLang)));
          for (const tag of file.tags ?? []) tagNames.add(tag);
        }
      }
      filesBySection.set(section, slugs);
    }
  }

  return {
    articleSlugs,
    articleLangs,
    tagNames,
    sections,
    systemSection,
    filesBySection,
    fileBySectionSlug,
    downloads,
  };
};

const sourceName = (slug: string, downloadPath: string): string => {
  const [, lang = "en"] = downloadPath.split("/");
  const name = downloadPath.split("/").pop() ?? slug;
  const suffix = name.startsWith(`${slug}.`) ? name.slice(slug.length + 1) : name.replace(/^[^.]+\./, "");
  return `${slug}.${normalizeLang(lang)}.${suffix}`;
};

const hasFileExtension = (path: string): boolean => {
  return /\.[a-zA-Z0-9]+$/.test(path);
};

const localizedRouteRewrite = (): Plugin => {
  const rewrite = (url: string, preferPrerender: boolean): { url: string; status?: number } => {
    const { articleSlugs, articleLangs, tagNames, sections, systemSection, filesBySection, fileBySectionSlug, downloads } = loadRouteData();
    const [rawPath = "/"] = url.split("?");
    const path = rawPath.length > 1 ? rawPath.replace(/\/+$/g, "") : rawPath;

    if (path === "/") {
      return { url: "/index.html" };
    }

    if (
      path.startsWith("/@") ||
      path.startsWith("/src/") ||
      path.startsWith("/node_modules/") ||
      path.startsWith("/generated/") ||
      path.startsWith("/media/")
    ) {
      return { url: rawPath };
    }

    if (downloads.has(path)) return { url: rawPath };

    if (hasFileExtension(path)) {
      return { url: rawPath };
    }

    const [langCandidate, section, encodedSlug, ...extra] = path.split("/").filter(Boolean);

    if (!isValidLang(langCandidate) || extra.length > 0) {
      return { url: "/404.html", status: 404 };
    }

    if (!section) {
      return { url: preferPrerender ? `/${langCandidate}/index.html` : "/index.html" };
    }

    if (section === "articles" && !encodedSlug) {
      return { url: preferPrerender ? `/${langCandidate}/articles/index.html` : "/index.html" };
    }

    if (section === "tags" && !encodedSlug) {
      return { url: preferPrerender ? `/${langCandidate}/tags/index.html` : "/index.html" };
    }

    if (section === "articles" && encodedSlug) {
      const slug = safeDecodeURIComponent(encodedSlug);
      if (!slug) return { url: "/404.html", status: 404 };
      if (!articleSlugs.has(slug)) return { url: "/404.html", status: 404 };
      if (!articleLangs.get(slug)?.has(normalizeLang(langCandidate))) return { url: "/index.html", status: 404 };
      return { url: preferPrerender ? `/${langCandidate}/articles/${encodedSlug}/index.html` : "/index.html" };
    }

    if (section === "tags" && encodedSlug) {
      const tag = safeDecodeURIComponent(encodedSlug);
      if (!tag) return { url: "/404.html", status: 404 };
      if (preferPrerender) return { url: `/${langCandidate}/tags/${encodedSlug}/index.html` };
      return tagNames.has(tag) ? { url: "/index.html" } : { url: "/404.html", status: 404 };
    }

    if (sections.has(section) && !encodedSlug) return { url: preferPrerender ? `/${langCandidate}/${section}/index.html` : "/index.html" };

    if (sections.has(section) && encodedSlug) {
      const slug = safeDecodeURIComponent(encodedSlug)?.trim().toLowerCase();
      const sectionFiles = filesBySection.get(section);
      if (!slug || !sectionFiles?.has(slug)) return { url: "/404.html", status: 404 };
      const file = fileBySectionSlug.get(`${section}/${slug}`);
      if (file?.languages && !file.languages.map(normalizeLang).includes(normalizeLang(langCandidate))) return { url: "/index.html", status: 404 };
      return { url: "/index.html" };
    }

    const systemSlug = safeDecodeURIComponent(section)?.trim().toLowerCase();
    const systemFiles = filesBySection.get(systemSection);
    if (!systemSlug || !systemFiles?.has(systemSlug)) return { url: "/404.html", status: 404 };
    const file = fileBySectionSlug.get(`${systemSection}/${systemSlug}`);
    if (file?.languages && !file.languages.map(normalizeLang).includes(normalizeLang(langCandidate))) return { url: "/index.html", status: 404 };
    return { url: "/index.html" };
  };

  const applyRewrite = (
    server: ViteMiddlewareServer,
    preferPrerender: boolean,
  ): void => {
    server.middlewares.use((req, res, next) => {
      if (req.url) {
        const target = rewrite(req.url, preferPrerender);
        req.url = target.url;

        if (target.status) res.statusCode = target.status;
      }

      next();
    });
  };

  return {
    name: "localized-route-rewrite",
    configureServer: (server) => {
      applyRewrite(server as ViteMiddlewareServer, false);
    },
    configurePreviewServer: (server) => {
      applyRewrite(server as ViteMiddlewareServer, true);
    },
  };
};

const serveStaticDirectory = (
  basePath: string,
  directory: string,
  req: { url?: string },
  res: {
    statusCode: number;
    setHeader?: (key: string, value: string) => void;
  },
  next: () => void,
): void => {
  const rawPath = req.url?.split("?")[0] ?? "";

  if (!rawPath.startsWith(basePath)) {
    next();
    return;
  }

  const relative = safeDecodeURIComponent(rawPath.slice(basePath.length));

  if (!relative || relative.includes("..")) {
    res.statusCode = 404;
    next();
    return;
  }

  const root = resolve(directory);
  const filePath = resolve(root, relative);

  if (!filePath.startsWith(root) || !existsSync(filePath) || !statSync(filePath).isFile()) {
    res.statusCode = 404;
    next();
    return;
  }

  res.setHeader?.("Content-Type", contentType(extname(filePath)));
  createReadStream(filePath).pipe(res as never);
};

const generatedAssetsPlugin = (): Plugin => ({
  name: "generated-assets",

  configureServer: (server) => {
    server.middlewares.use((req, res, next) => {
      serveStaticDirectory("/generated/", generatedDir, req, res, next);
    });
  },

  closeBundle: async () => {
    if (!existsSync(generatedDir)) {
      return;
    }

    await rm(distGeneratedDir, { recursive: true, force: true });
    await copyDir(generatedDir, distGeneratedDir);
  },
});

const contentFilesPlugin = (): Plugin => ({
  name: "content-files",

  configureServer: (server) => {
    server.middlewares.use((req, res, next) => {
      const rawPath = req.url?.split("?")[0] ?? "";
      const filePath = loadRouteData().downloads.get(rawPath);
      if (!filePath || !existsSync(filePath) || !statSync(filePath).isFile()) {
        next();
        return;
      }
      res.setHeader?.("Content-Type", contentType(extname(filePath)));
      createReadStream(filePath).pipe(res as never);
    });
  },

  closeBundle: async () => {
    for (const [publicPath, filePath] of loadRouteData().downloads) {
      if (!existsSync(filePath)) continue;
      const target = resolve(rootDir, "dist", publicPath.replace(/^\/+/, ""));
      await mkdir(resolve(target, ".."), { recursive: true });
      await copyFile(filePath, target);
    }
  },
});

const contentMediaPlugin = (): Plugin => ({
  name: "content-media",

  configureServer: (server) => {
    server.middlewares.use((req, res, next) => {
      serveStaticDirectory("/media/", contentDir, req, res, next);
    });
  },

  closeBundle: async () => {
    if (!existsSync(contentDir)) {
      return;
    }

    await rm(distMediaDir, { recursive: true, force: true });

    for (const section of await readdir(contentDir, { withFileTypes: true })) {
      if (!section.isDirectory()) continue;
      const sectionDir = resolve(contentDir, section.name);
      for (const entry of await readdir(sectionDir, { withFileTypes: true })) {
      if (!entry.isDirectory()) {
        continue;
      }

      const source = resolve(sectionDir, entry.name, "assets");

      if (!existsSync(source)) {
        continue;
      }

      await copyDir(source, resolve(distMediaDir, section.name, entry.name, "assets"));
      }
    }
  },
});

const copyDir = async (from: string, to: string): Promise<void> => {
  await mkdir(to, { recursive: true });

  for (const entry of await readdir(from, { withFileTypes: true })) {
    const source = resolve(from, entry.name);
    const target = resolve(to, entry.name);

    if (entry.isDirectory()) {
      await copyDir(source, target);
    } else if (entry.isFile()) {
      await copyFile(source, target);
    }
  }
};

const contentType = (ext: string): string => {
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".xml") return "application/xml; charset=utf-8";
  if (ext === ".md") return "text/markdown; charset=utf-8";
  if (ext === ".txt" || ext === ".local") return "text/plain; charset=utf-8";
  if (ext === ".pdf") return "application/pdf";
  if (ext === ".svg") return "image/svg+xml";
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".gif") return "image/gif";
  if (ext === ".webp") return "image/webp";
  if (ext === ".avif") return "image/avif";
  if (ext === ".ico") return "image/x-icon";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".js" || ext === ".mjs") return "text/javascript; charset=utf-8";

  return "application/octet-stream";
};

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },

  plugins: [
    localizedRouteRewrite(),
    generatedAssetsPlugin(),
    contentFilesPlugin(),
    contentMediaPlugin(),
    viteCompression({
      algorithm: "brotliCompress",
      ext: ".br",
      threshold: 1024,
      deleteOriginFile: false,
      filter: /\.(js|css|svg|json|xml)$/i,
    }),
  ],

  build: {
    sourcemap: false,
    rollupOptions: {
      input: {
        home: resolve(rootDir, "index.html"),
      },
    },
  },
});

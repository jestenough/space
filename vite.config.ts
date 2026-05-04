import { defineConfig, type Plugin } from "vite";
import viteCompression from "vite-plugin-compression";
import { resolve, extname } from "node:path";
import { fileURLToPath, URL } from "node:url";
import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import { mkdir, readdir, rm, copyFile } from "node:fs/promises";

type ArticleRecord = {
  slug: string;
  tags?: string[];
};

type RouteData = {
  articleSlugs: Set<string>;
  tagNames: Set<string>;
  infoFileSlugs: Set<string>;
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
const infoDir = resolve(rootDir, "content", "info");

const distGeneratedDir = resolve(rootDir, "dist", "generated");
const distInfoDir = resolve(rootDir, "dist", "info");

const LANGUAGE_TAG_PATTERN = /^[a-z]{2,3}(?:-[A-Z]{2})?$/;
const INFO_FILE_SLUGS = new Set(["readme", "about", "changelog", "manifest"]);

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
  const metadataPath = [
    resolve(generatedDir, "articles-index.json"),
    resolve(distGeneratedDir, "articles-index.json"),
  ].find((path) => existsSync(path));
  const articleSlugs = new Set<string>();
  const tagNames = new Set<string>();

  if (!metadataPath) {
    return {
      articleSlugs,
      tagNames,
      infoFileSlugs: INFO_FILE_SLUGS,
    };
  }

  const articles = JSON.parse(readFileSync(metadataPath, "utf8")) as ArticleRecord[];

  for (const article of articles) {
    articleSlugs.add(article.slug);

    for (const tag of article.tags ?? []) {
      tagNames.add(tag);
    }
  }

  return {
    articleSlugs,
    tagNames,
    infoFileSlugs: INFO_FILE_SLUGS,
  };
};

const hasFileExtension = (path: string): boolean => {
  return /\.[a-zA-Z0-9]+$/.test(path);
};

const localizedRouteFallback = (): Plugin => {
  const rewrite = (url: string, preferPrerender: boolean): string => {
    const { articleSlugs, tagNames, infoFileSlugs } = loadRouteData();
    const [rawPath = "/"] = url.split("?");
    const path = rawPath.length > 1 ? rawPath.replace(/\/+$/g, "") : rawPath;

    if (path === "/") {
      return "/index.html";
    }

    if (
      path.startsWith("/@") ||
      path.startsWith("/src/") ||
      path.startsWith("/node_modules/") ||
      path.startsWith("/info/") ||
      path.startsWith("/generated/") ||
      path.startsWith("/media/")
    ) {
      return rawPath;
    }

    if (hasFileExtension(path)) {
      return rawPath;
    }

    const [langCandidate, section, encodedSlug, ...extra] = path.split("/").filter(Boolean);

    if (!isValidLang(langCandidate) || extra.length > 0) {
      return "/404.html";
    }

    if (!section) {
      return preferPrerender ? `/${langCandidate}/index.html` : "/index.html";
    }

    if (section === "articles" && !encodedSlug) {
      return preferPrerender ? `/${langCandidate}/articles/index.html` : "/index.html";
    }

    if (section === "tags" && !encodedSlug) {
      return preferPrerender ? `/${langCandidate}/tags/index.html` : "/index.html";
    }

    if (section === "articles" && encodedSlug) {
      const slug = safeDecodeURIComponent(encodedSlug);
      if (!slug) return "/404.html";
      if (preferPrerender) return `/${langCandidate}/articles/${encodedSlug}/index.html`;
      return articleSlugs.has(slug) ? "/index.html" : "/404.html";
    }

    if (section === "tags" && encodedSlug) {
      const tag = safeDecodeURIComponent(encodedSlug);
      if (!tag) return "/404.html";
      if (preferPrerender) return `/${langCandidate}/tags/${encodedSlug}/index.html`;
      return tagNames.has(tag) ? "/index.html" : "/404.html";
    }

    const infoSlug = safeDecodeURIComponent(section)?.trim().toLowerCase();
    return infoSlug && infoFileSlugs.has(infoSlug) ? "/index.html" : "/404.html";
  };

  const applyFallback = (
    server: ViteMiddlewareServer,
    preferPrerender: boolean,
  ): void => {
    server.middlewares.use((req, res, next) => {
      if (req.url) {
        const target = rewrite(req.url, preferPrerender);
        req.url = target;

        if (target === "/404.html") {
          res.statusCode = 404;
        }
      }

      next();
    });
  };

  return {
    name: "localized-route-fallback",
    configureServer: (server) => {
      applyFallback(server as ViteMiddlewareServer, false);
    },
    configurePreviewServer: (server) => {
      applyFallback(server as ViteMiddlewareServer, true);
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

const infoAssetsPlugin = (): Plugin => ({
  name: "info-assets",

  configureServer: (server) => {
    server.middlewares.use((req, res, next) => {
      serveStaticDirectory("/info/", infoDir, req, res, next);
    });
  },

  closeBundle: async () => {
    if (!existsSync(infoDir)) {
      return;
    }

    await rm(distInfoDir, { recursive: true, force: true });
    await copyDir(infoDir, distInfoDir);
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

  return "application/octet-stream";
};

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },

  plugins: [
    localizedRouteFallback(),
    generatedAssetsPlugin(),
    infoAssetsPlugin(),
    viteCompression({
      algorithm: "brotliCompress",
      ext: ".br",
      threshold: 1024,
      deleteOriginFile: false,
      filter: /\.(js|css|svg|json|xml)$/i,
    }),
  ],

  build: {
    target: "es2022",
    cssTarget: "es2022",
    sourcemap: false,
    rollupOptions: {
      input: {
        home: resolve(rootDir, "index.html"),
      },
    },
  },
});
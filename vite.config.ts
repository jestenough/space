import { defineConfig, type Plugin, type ViteDevServer } from "vite";
import viteCompression from "vite-plugin-compression";
import type { IncomingMessage, ServerResponse } from "node:http";
import { resolve, extname } from "node:path";
import { fileURLToPath, URL } from "node:url";
import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import { copyFile, mkdir, readdir, rm } from "node:fs/promises";

type FileRecord = {
  section?: string;
  slug: string;
  downloadPath?: string | null;
};

const rootDir = fileURLToPath(new URL(".", import.meta.url));
const generatedDir = resolve(rootDir, "generated");
const contentDir = resolve(rootDir, "content");
const distDir = resolve(rootDir, "dist");
const distGeneratedDir = resolve(distDir, "generated");
const distMediaDir = resolve(distDir, "media");
const DEFAULT_LANG = "en";
const LANGUAGE_TAG_PATTERN = /^[a-z]{2,3}(?:-[A-Z]{2})?$/;

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

const isLang = (value: string | undefined): boolean => Boolean(value && LANGUAGE_TAG_PATTERN.test(normalizeLang(value)));
const hasFileExtension = (path: string): boolean => /\.[a-zA-Z0-9]+$/.test(path);
const readJson = <T>(path: string): T | null => existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) as T : null;

const sourceName = (slug: string, downloadPath: string): string => {
  const [, lang = DEFAULT_LANG] = downloadPath.split("/");
  const name = downloadPath.split("/").pop() ?? slug;
  const suffix = name.startsWith(`${slug}.`) ? name.slice(slug.length + 1) : name.replace(/^[^.]+\./, "");
  return `${slug}.${normalizeLang(lang)}.${suffix}`;
};

const loadDownloadRoutes = (): Map<string, string> => {
  const sections = readJson<Array<{ slug: string }>>(resolve(generatedDir, "sections-index.json")) ?? [];
  const routes = new Map<string, string>();
  for (const section of sections) {
    const files = readJson<FileRecord[]>(resolve(generatedDir, "sections", `${section.slug}.json`)) ?? [];
    for (const file of files) {
      if (!file.downloadPath) continue;
      routes.set(file.downloadPath, resolve(contentDir, section.slug, file.slug, sourceName(file.slug, file.downloadPath)));
    }
  }
  return routes;
};

const prerenderTarget = (url: string): { url: string; status?: number; redirect?: string } => {
  const [rawPath = "/"] = url.split("?");
  const path = rawPath.length > 1 ? rawPath.replace(/\/+$/g, "") : rawPath;

  if (path === "/") return { url: rawPath, status: 302, redirect: `/${DEFAULT_LANG}` };
  if (
    path.startsWith("/@") ||
    path.startsWith("/src/") ||
    path.startsWith("/node_modules/") ||
    path.startsWith("/generated/") ||
    path.startsWith("/media/")
  ) return { url: rawPath };
  if (hasFileExtension(path)) return { url: rawPath };

  const [lang] = path.split("/").filter(Boolean);
  if (!isLang(lang)) return { url: "/404.html", status: 404 };

  const candidate = resolve(distDir, path.replace(/^\/+/, ""), "index.html");
  return existsSync(candidate)
    ? { url: `${path}/index.html`.replace(/\/+/g, "/") }
    : { url: "/404.html", status: 404 };
};

const serveStaticDirectory = (
  basePath: string,
  directory: string,
  req: IncomingMessage,
  res: ServerResponse<IncomingMessage>,
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

const previewRouteRewrite = (): Plugin => ({
  name: "preview-route-rewrite",
  configurePreviewServer: (server) => {
    server.middlewares.use((req, res, next) => {
      if (!req.url) {
        next();
        return;
      }

      const target = prerenderTarget(req.url);
      if (target.redirect) {
        res.statusCode = target.status ?? 302;
        res.setHeader?.("Location", target.redirect);
        res.end?.();
        return;
      }

      req.url = target.url;
      if (target.status) res.statusCode = target.status;
      next();
    });
  }
});

const generatedAssetsPlugin = (): Plugin => ({
  name: "generated-assets",
  configureServer: (server) => {
    server.middlewares.use((req, res, next) => {
      serveStaticDirectory("/generated/", generatedDir, req, res, next);
    });
  },
  closeBundle: async () => {
    if (!existsSync(generatedDir)) return;
    await rm(distGeneratedDir, { recursive: true, force: true });
    await copyDirectory(generatedDir, distGeneratedDir, { skip: new Set(["files-meta"]) });
  }
});

const contentFilesPlugin = (): Plugin => ({
  name: "content-files",
  configureServer: (server) => {
    server.middlewares.use((req, res, next) => {
      const rawPath = req.url?.split("?")[0] ?? "";
      const filePath = loadDownloadRoutes().get(rawPath);
      if (!filePath || !existsSync(filePath) || !statSync(filePath).isFile()) {
        next();
        return;
      }
      res.setHeader?.("Content-Type", contentType(extname(filePath)));
      createReadStream(filePath).pipe(res as never);
    });
  },
  closeBundle: async () => {
    for (const [publicPath, filePath] of loadDownloadRoutes()) {
      if (!existsSync(filePath)) continue;
      const target = resolve(distDir, publicPath.replace(/^\/+/, ""));
      await mkdir(resolve(target, ".."), { recursive: true });
      await copyFile(filePath, target);
    }
  }
});

const contentMediaPlugin = (): Plugin => ({
  name: "content-media",
  configureServer: (server) => {
    server.middlewares.use((req, res, next) => {
      serveStaticDirectory("/media/", contentDir, req, res, next);
    });
  },
  closeBundle: async () => {
    if (!existsSync(contentDir)) return;
    await rm(distMediaDir, { recursive: true, force: true });
    for (const section of await readdir(contentDir, { withFileTypes: true })) {
      if (!section.isDirectory()) continue;
      const sectionDir = resolve(contentDir, section.name);
      for (const entry of await readdir(sectionDir, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const source = resolve(sectionDir, entry.name, "assets");
        if (!existsSync(source)) continue;
        await copyDirectory(source, resolve(distMediaDir, section.name, entry.name, "assets"));
      }
    }
  }
});

const copyDirectory = async (from: string, to: string, options?: { skip?: Set<string> }): Promise<void> => {
  await mkdir(to, { recursive: true });
  for (const entry of await readdir(from, { withFileTypes: true })) {
    if (options?.skip?.has(entry.name)) continue;
    const source = resolve(from, entry.name);
    const target = resolve(to, entry.name);
    if (entry.isDirectory()) await copyDirectory(source, target, options);
    else if (entry.isFile()) await copyFile(source, target);
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
    previewRouteRewrite(),
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

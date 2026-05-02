import { defineConfig, type Plugin } from "vite";
import viteCompression from "vite-plugin-compression";
import { resolve, extname } from "node:path";
import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import { mkdir, readdir, rm, copyFile } from "node:fs/promises";

type ArticleRecord = { slug: string; tags?: string[] };
type ViteMiddlewareServer = { middlewares: { use: (fn: (req: { url?: string }, res: { statusCode: number; setHeader?: (key: string, value: string) => void }, next: () => void) => void) => void } };

const rootDir = __dirname;
const generatedDir = resolve(rootDir, "generated");
const infoDir = resolve(rootDir, "content", "info");
const distGeneratedDir = resolve(rootDir, "dist", "generated");
const distInfoDir = resolve(rootDir, "dist", "info");

function safeDecodeURIComponent(value: string): string | null { try { return decodeURIComponent(value); } catch { return null; } }

function loadRouteData(): { articleSlugs: Set<string>; tagNames: Set<string>; infoFileSlugs: Set<string> } {
  const metadataPath = existsSync(resolve(rootDir, "generated", "articles-index.json"))
    ? resolve(rootDir, "generated", "articles-index.json")
    : resolve(rootDir, "content", "articles-index.json");
  const articles = JSON.parse(readFileSync(metadataPath, "utf8")) as ArticleRecord[];
  const articleSlugs = new Set<string>(), tagNames = new Set<string>();
  for (const article of articles) { articleSlugs.add(article.slug); for (const tag of article.tags ?? []) tagNames.add(tag); }
  return { articleSlugs, tagNames, infoFileSlugs: new Set(["readme", "about", "changelog", "manifest"]) };
}

function localizedRouteFallback(): Plugin {
  const { articleSlugs, tagNames, infoFileSlugs } = loadRouteData();
  const rewrite = (url: string, preferPrerender: boolean): string => {
    const [path] = url.split("?");
    if (!path || path === "/") return "/index.html";
    if (path.startsWith("/generated/")) return path;
    if (path === "/root" || path === "/root/") return "/index.html";
    if (!/^\/(en|ru)(\/|$)/.test(path)) {
      if (path.startsWith("/@") || path.startsWith("/src/") || path.startsWith("/node_modules/") || path.startsWith("/info/")) return path;
      if (/\.[a-zA-Z0-9]+$/.test(path)) return path;
      return "/404.html";
    }
    if (/\.[a-zA-Z0-9]+$/.test(path)) return path;
    if (/^\/(en|ru)\/?$/.test(path)) return preferPrerender ? `${path.replace(/\/$/, "")}/index.html` : "/index.html";
    if (/^\/(en|ru)\/articles\/?$/.test(path)) return preferPrerender ? `${path.replace(/\/$/, "")}/index.html` : "/index.html";
    if (/^\/(en|ru)\/tags\/?$/.test(path)) return preferPrerender ? `${path.replace(/\/$/, "")}/index.html` : "/index.html";
    const articleMatch = path.match(/^\/(en|ru)\/articles\/([^/?#]+)$/);
    if (articleMatch) { const slug = safeDecodeURIComponent(articleMatch[2]); if (!slug) return "/404.html"; return articleSlugs.has(slug) ? (preferPrerender ? `${path}/index.html` : "/index.html") : "/404.html"; }
    const tagMatch = path.match(/^\/(en|ru)\/tags\/([^/?#]+)$/);
    if (tagMatch) { const tag = safeDecodeURIComponent(tagMatch[2]); if (!tag) return "/404.html"; return tagNames.has(tag) ? (preferPrerender ? `${path}/index.html` : "/index.html") : "/404.html"; }
    const shortRouteMatch = path.match(/^\/(en|ru)\/([^/?#]+)$/);
    if (shortRouteMatch) { const slug = safeDecodeURIComponent(shortRouteMatch[2]); if (!slug) return "/404.html"; if (infoFileSlugs.has(slug.toLowerCase())) return "/index.html"; }
    return "/404.html";
  };
  const applyFallback = (server: ViteMiddlewareServer, preferPrerender: boolean): void => {
    server.middlewares.use((req, res, next) => { if (req.url) { const target = rewrite(req.url, preferPrerender); req.url = target; if (target === "/404.html") res.statusCode = 404; } next(); });
  };
  return { name: "localized-route-fallback", configureServer(server) { applyFallback(server as ViteMiddlewareServer, false); }, configurePreviewServer(server) { applyFallback(server as ViteMiddlewareServer, true); } };
}


function infoAssetsPlugin(): Plugin {
  return {
    name: "info-assets",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const rawPath = req.url?.split("?")[0] ?? "";
        if (!rawPath.startsWith("/info/")) { next(); return; }
        const relative = safeDecodeURIComponent(rawPath.slice("/info/".length));
        if (!relative || relative.includes("..") || relative.includes("/")) { res.statusCode = 404; next(); return; }
        const filePath = resolve(infoDir, relative);
        if (!filePath.startsWith(infoDir) || !existsSync(filePath) || !statSync(filePath).isFile()) { res.statusCode = 404; next(); return; }
        const type = contentType(extname(filePath));
        res.setHeader?.("Content-Type", type);
        createReadStream(filePath).pipe(res as never);
      });
    },
    async closeBundle() {
      if (!existsSync(infoDir)) return;
      await rm(distInfoDir, { recursive: true, force: true });
      await copyDir(infoDir, distInfoDir);
    }
  };
}

function generatedAssetsPlugin(): Plugin {
  return {
    name: "generated-assets",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const rawPath = req.url?.split("?")[0] ?? "";
        if (!rawPath.startsWith("/generated/")) { next(); return; }
        const relative = safeDecodeURIComponent(rawPath.slice("/generated/".length));
        if (!relative || relative.includes("..")) { res.statusCode = 404; next(); return; }
        const filePath = resolve(generatedDir, relative);
        if (!filePath.startsWith(generatedDir) || !existsSync(filePath) || !statSync(filePath).isFile()) { res.statusCode = 404; next(); return; }
        const type = contentType(extname(filePath));
        res.setHeader?.("Content-Type", type);
        createReadStream(filePath).pipe(res as never);
      });
    },
    async closeBundle() {
      if (!existsSync(generatedDir)) return;
      await rm(distGeneratedDir, { recursive: true, force: true });
      await copyDir(generatedDir, distGeneratedDir);
    }
  };
}

async function copyDir(from: string, to: string): Promise<void> {
  await mkdir(to, { recursive: true });
  for (const entry of await readdir(from, { withFileTypes: true })) {
    const source = resolve(from, entry.name);
    const target = resolve(to, entry.name);
    if (entry.isDirectory()) await copyDir(source, target);
    else if (entry.isFile()) await copyFile(source, target);
  }
}

function contentType(ext: string): string {
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  if (ext === ".xml") return "application/xml; charset=utf-8";
  if (ext === ".md") return "text/markdown; charset=utf-8";
  if (ext === ".txt" || ext === ".local") return "text/plain; charset=utf-8";
  return "application/octet-stream";
}

export default defineConfig({
  plugins: [localizedRouteFallback(), generatedAssetsPlugin(), infoAssetsPlugin(), viteCompression({ algorithm: "brotliCompress", ext: ".br", threshold: 1024, deleteOriginFile: false })],
  build: { rollupOptions: { input: { home: resolve(rootDir, "index.html") } } }
});

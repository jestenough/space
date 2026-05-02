import { defineConfig, type Plugin } from "vite";
import viteCompression from "vite-plugin-compression";
import { resolve, extname } from "node:path";
import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import { mkdir, readdir, rm, copyFile } from "node:fs/promises";

type ArticleRecord = { slug: string; tags?: string[] };
type RouteData = { articleSlugs: Set<string>; tagNames: Set<string>; infoFileSlugs: Set<string> };
type ViteMiddlewareServer = { middlewares: { use: (fn: (req: { url?: string }, res: { statusCode: number; setHeader?: (key: string, value: string) => void }, next: () => void) => void) => void } };

const rootDir = __dirname;
const generatedDir = resolve(rootDir, "generated");
const infoDir = resolve(rootDir, "content", "info");
const distGeneratedDir = resolve(rootDir, "dist", "generated");
const distInfoDir = resolve(rootDir, "dist", "info");
const LANGUAGE_TAG_PATTERN = /^[a-z]{2,3}(?:-[A-Z]{2})?$/;
const INFO_FILE_SLUGS = new Set(["readme", "about", "changelog", "manifest"]);
const safeDecodeURIComponent = (value: string): string | null => { try { return decodeURIComponent(value); } catch { return null; } };
const normalizeLang = (value: string): string => { const [base = "", region] = value.trim().split("-"); return region ? `${base.toLowerCase()}-${region.toUpperCase()}` : base.toLowerCase(); };
const isValidLang = (value: string | undefined): boolean => Boolean(value && LANGUAGE_TAG_PATTERN.test(normalizeLang(value)));
const loadRouteData = (): RouteData => { const metadataPath = existsSync(resolve(rootDir, "generated", "articles-index.json")) ? resolve(rootDir, "generated", "articles-index.json") : resolve(rootDir, "content", "articles-index.json"); const articles = JSON.parse(readFileSync(metadataPath, "utf8")) as ArticleRecord[]; const articleSlugs = new Set<string>(), tagNames = new Set<string>(); for (const article of articles) { articleSlugs.add(article.slug); for (const tag of article.tags ?? []) tagNames.add(tag); } return { articleSlugs, tagNames, infoFileSlugs: INFO_FILE_SLUGS }; };
const hasFileExtension = (path: string): boolean => /\.[a-zA-Z0-9]+$/.test(path);
const localizedRouteFallback = (): Plugin => { const { articleSlugs, tagNames, infoFileSlugs } = loadRouteData(); const rewrite = (url: string, preferPrerender: boolean): string => { const [path = "/"] = url.split("?"); if (path === "/") return "/index.html"; if (path.startsWith("/@") || path.startsWith("/src/") || path.startsWith("/node_modules/") || path.startsWith("/info/") || path.startsWith("/generated/")) return path; if (hasFileExtension(path)) return path; const [, langCandidate, section, encodedSlug, extra] = path.match(/^\/([^/]+)(?:\/([^/]+))?(?:\/([^/]+))?(?:\/(.+))?$/) ?? []; if (!isValidLang(langCandidate) || extra) return "/404.html"; const basePath = path.replace(/\/$/, ""); if (!section) return preferPrerender ? `${basePath}/index.html` : "/index.html"; if (section === "articles" && !encodedSlug) return preferPrerender ? `${basePath}/index.html` : "/index.html"; if (section === "tags" && !encodedSlug) return preferPrerender ? `${basePath}/index.html` : "/index.html"; if (section === "articles" && encodedSlug) { const slug = safeDecodeURIComponent(encodedSlug); return slug && articleSlugs.has(slug) ? (preferPrerender ? `${basePath}/index.html` : "/index.html") : "/404.html"; } if (section === "tags" && encodedSlug) { const tag = safeDecodeURIComponent(encodedSlug); return tag && tagNames.has(tag) ? (preferPrerender ? `${basePath}/index.html` : "/index.html") : "/404.html"; } if (section && !encodedSlug) { const infoSlug = safeDecodeURIComponent(section)?.trim().toLowerCase(); return infoSlug && infoFileSlugs.has(infoSlug) ? "/index.html" : "/404.html"; } return "/404.html"; }; const applyFallback = (server: ViteMiddlewareServer, preferPrerender: boolean): void => { server.middlewares.use((req, res, next) => { if (req.url) { const target = rewrite(req.url, preferPrerender); req.url = target; if (target === "/404.html") res.statusCode = 404; } next(); }); }; return { name: "localized-route-fallback", configureServer: (server) => applyFallback(server as ViteMiddlewareServer, false), configurePreviewServer: (server) => applyFallback(server as ViteMiddlewareServer, true) }; };
const serveStaticDirectory = (basePath: string, directory: string, req: { url?: string }, res: { statusCode: number; setHeader?: (key: string, value: string) => void }, next: () => void): void => { const rawPath = req.url?.split("?")[0] ?? ""; if (!rawPath.startsWith(basePath)) { next(); return; } const relative = safeDecodeURIComponent(rawPath.slice(basePath.length)); if (!relative || relative.includes("..")) { res.statusCode = 404; next(); return; } const filePath = resolve(directory, relative); if (!filePath.startsWith(directory) || !existsSync(filePath) || !statSync(filePath).isFile()) { res.statusCode = 404; next(); return; } res.setHeader?.("Content-Type", contentType(extname(filePath))); createReadStream(filePath).pipe(res as never); };
const infoAssetsPlugin = (): Plugin => ({ name: "info-assets", configureServer: (server) => { server.middlewares.use((req, res, next) => serveStaticDirectory("/info/", infoDir, req, res, next)); }, closeBundle: async () => { if (!existsSync(infoDir)) return; await rm(distInfoDir, { recursive: true, force: true }); await copyDir(infoDir, distInfoDir); } });
const generatedAssetsPlugin = (): Plugin => ({ name: "generated-assets", configureServer: (server) => { server.middlewares.use((req, res, next) => serveStaticDirectory("/generated/", generatedDir, req, res, next)); }, closeBundle: async () => { if (!existsSync(generatedDir)) return; await rm(distGeneratedDir, { recursive: true, force: true }); await copyDir(generatedDir, distGeneratedDir); } });
const copyDir = async (from: string, to: string): Promise<void> => { await mkdir(to, { recursive: true }); for (const entry of await readdir(from, { withFileTypes: true })) { const source = resolve(from, entry.name); const target = resolve(to, entry.name); if (entry.isDirectory()) await copyDir(source, target); else if (entry.isFile()) await copyFile(source, target); } };
const contentType = (ext: string): string => { if (ext === ".html") return "text/html; charset=utf-8"; if (ext === ".json") return "application/json; charset=utf-8"; if (ext === ".xml") return "application/xml; charset=utf-8"; if (ext === ".md") return "text/markdown; charset=utf-8"; if (ext === ".txt" || ext === ".local") return "text/plain; charset=utf-8"; return "application/octet-stream"; };
export default defineConfig({
  plugins: [localizedRouteFallback(), generatedAssetsPlugin(), infoAssetsPlugin(), viteCompression({ algorithm: "brotliCompress", ext: ".br", threshold: 1024, deleteOriginFile: false })],
  build: {
    target: "es2022",
    cssTarget: "es2022",
    sourcemap: false,
    rollupOptions: { input: { home: resolve(rootDir, "index.html") } }
  }
});

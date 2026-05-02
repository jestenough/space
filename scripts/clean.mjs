import { rm } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd());
const targets = [
  resolve(root, "dist"),
  resolve(root, "generated"),
  resolve(root, ".cache"),
  resolve(root, ".vite")
];

for (const target of targets) await rm(target, { recursive: true, force: true });
for (const lang of ["en", "ru"]) await rm(resolve(root, "public", lang, "articles"), { recursive: true, force: true });
console.log("clean_ok: removed dist, generated, caches, and generated public PDFs");

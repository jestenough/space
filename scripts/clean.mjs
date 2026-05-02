import { readdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(process.cwd());
const publicDir = resolve(root, "public");
const targets = [resolve(root, "dist"), resolve(root, "generated"), resolve(root, ".cache"), resolve(root, ".vite")];
const removeTarget = async (target) => rm(target, { recursive: true, force: true });
const removeGeneratedPublicPdfs = async () => {
  let entries = [];
  try { entries = await readdir(publicDir, { withFileTypes: true }); } catch { return; }
  await Promise.all(entries.filter((entry) => entry.isDirectory()).map((entry) => removeTarget(resolve(publicDir, entry.name, "articles"))));
};
await Promise.all(targets.map(removeTarget));
await removeGeneratedPublicPdfs();
console.log("clean_ok: removed dist, generated, caches, and generated public PDFs");

import { mkdtemp, mkdir, readdir, readFile, rm, copyFile, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { spawn } from "node:child_process";

const root = resolve(process.cwd());
const sourceDir = resolve(root, "content", "articles");
const publicDir = resolve(root, "public");
const force = process.env.FORCE_PDF === "1";
const strictPdf = process.env.STRICT_PDF === "1";
const dockerImage = process.env.PDF_DOCKER_IMAGE || "autophany-space";

async function main() {
  const compiler = await resolveCompiler();
  const sources = await listSources();
  if (sources.length === 0) throw new Error("No article sources found in content/articles/*.tex");

  let built = 0;
  let skipped = 0;
  for (const source of sources) {
    if (process.env.PDF_DEBUG === "1") console.log(`pdf_start: ${source.fileName}`);
    const pdfPath = resolve(publicDir, source.lang, "articles", `${source.slug}.pdf`);
    await mkdir(resolve(publicDir, source.lang, "articles"), { recursive: true });
    if (!force && await isFresh(source.path, pdfPath)) {
      skipped += 1;
      continue;
    }
    await buildPdf(source, pdfPath, compiler);
    built += 1;
    if (process.env.PDF_DEBUG === "1") console.log(`pdf_done: ${source.fileName}`);
  }
  console.log(`pdf_ok: ${built} built, ${skipped} skipped, ${sources.length} total`);
}

const listSources = async () => {
  const entries = await readdir(sourceDir, { withFileTypes: true });
  const result = [];
  const seen = new Set();
  for (const entry of entries) {
    if (entry.isDirectory()) throw new Error(`Language subdirectories are not allowed in content/articles/: ${entry.name}`);
    if (!entry.isFile() || !entry.name.endsWith(".tex")) continue;
    const parsed = parseArticleFilename(entry.name);
    if (!parsed) throw new Error(`Article source filename must be <slug>.<lang>.tex: ${entry.name}`);
    if (seen.has(parsed.key)) throw new Error(`Duplicate article source: ${entry.name}`);
    seen.add(parsed.key);
    result.push({ ...parsed, fileName: entry.name, path: resolve(sourceDir, entry.name) });
  }
  return result.sort((a, b) => a.key.localeCompare(b.key));
};

const parseArticleFilename = (fileName) => {
  const match = fileName.match(/^(.+)\.([a-z]{2,3}(?:-[A-Za-z]{2})?)\.tex$/);
  if (!match) return null;
  const [, slug, rawLang] = match;
  const lang = normalizeLang(rawLang);
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) throw new Error(`Invalid article slug in filename: ${fileName}`);
  return { slug, lang, key: `${slug}.${lang}` };
};

const isFresh = async (sourcePath, pdfPath) => {
  try {
    const [sourceStat, pdfStat] = await Promise.all([stat(sourcePath), stat(pdfPath)]);
    return pdfStat.mtimeMs >= sourceStat.mtimeMs;
  } catch {
    return false;
  }
};

const buildPdf = async (source, pdfPath, compiler) => {
  const workDir = await mkdtemp(join(tmpdir(), `autophany-space-${source.slug}-${source.lang}-`));
  try {
    const sourceText = await readFile(source.path, "utf8");
    const mainTex = resolve(workDir, "main.tex");
    const compileText = isStandaloneLatex(sourceText) ? sourceText : wrapLatexFragment(sourceText, source);
    await writeFile(mainTex, compileText, "utf8");
    await runXelatexUntilPdf(workDir, mainTex, compiler);
    await copyFile(resolve(workDir, "main.pdf"), pdfPath);
  } catch (error) {
    throw new Error(`Failed to build PDF for ${source.fileName}: ${error instanceof Error ? error.message : String(error)}`);
  } finally {
    await rm(workDir, { recursive: true, force: true });
  }
};

const isStandaloneLatex = (sourceText) => /\\documentclass\b/.test(sourceText) && /\\begin\{document\}/.test(sourceText);

const DEFAULT_POLYGLOSSIA_LANGUAGES = {
  en: "english",
  ru: "russian"
};

const polyglossiaLanguage = (lang) => DEFAULT_POLYGLOSSIA_LANGUAGES[lang.split("-")[0]] ?? "english";

const normalizeLang = (value) => {
  const match = String(value).match(/^([a-z]{2,3})(?:-([A-Za-z]{2}))?$/);
  if (!match) throw new Error(`Invalid language code: ${value}`);
  return match[2] ? `${match[1].toLowerCase()}-${match[2].toUpperCase()}` : match[1].toLowerCase();
};

const wrapLatexFragment = (sourceText, source) => {
  const language = polyglossiaLanguage(source.lang);
  return String.raw`\documentclass[11pt]{article}
\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{fontspec}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
\usepackage{polyglossia}
\setdefaultlanguage{${language}}
\setotherlanguage{english}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}
\usepackage{enumitem}
\setlist{itemsep=0.25em}
\title{${escapeLatex(source.slug)}}
\date{}
\begin{document}
${sourceText}
\end{document}
`;
};

const escapeLatex = (value) => String(value).replace(/[&%$#_{}]/g, (char) => `\\${char}`).replace(/~/g, "\\textasciitilde{}").replace(/\^/g, "\\textasciicircum{}");

const runXelatexUntilPdf = (workDir, mainTex, activeCompiler) => new Promise((resolvePromise, reject) => {
    const pdfPath = resolve(workDir, "main.pdf");
    const { command, args, cwd } = activeCompiler.createInvocation(workDir, mainTex);
    const child = spawn(command, args, { cwd, stdio: "ignore" });
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      clearInterval(poll);
      clearTimeout(timer);
      if (!child.killed) child.kill("SIGTERM");
      resolvePromise();
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      clearInterval(poll);
      clearTimeout(timer);
      if (!child.killed) child.kill("SIGKILL");
      reject(error);
    };
    const poll = setInterval(async () => {
      try {
        const info = await stat(pdfPath);
        if (info.size > 0) finish();
      } catch {
        // PDF not written yet.
      }
    }, 250);
    const timer = setTimeout(() => fail(new Error(`${activeCompiler.label} timed out before producing main.pdf`)), 60_000);
    child.on("error", fail);
    child.on("close", async (code) => {
      if (settled) return;
      try {
        const info = await stat(pdfPath);
        if (info.size > 0) finish();
        else fail(new Error(`${activeCompiler.label} exited with ${code} before creating main.pdf`));
      } catch {
        fail(new Error(`${activeCompiler.label} exited with ${code} before creating main.pdf`));
      }
    });
});

function hasCommand(command) {
  return new Promise((resolvePromise) => {
  const child = spawn(command, ["--version"], { stdio: "ignore" });
  child.on("error", () => resolvePromise(false));
  child.on("close", (code) => resolvePromise(code === 0));
  });
}

function commandSucceeds(command, args) {
  return new Promise((resolvePromise) => {
    const child = spawn(command, args, { stdio: "ignore" });
    child.on("error", () => resolvePromise(false));
    child.on("close", (code) => resolvePromise(code === 0));
  });
}

async function resolveCompiler() {
  if (await hasCommand("xelatex")) {
    return {
      label: "xelatex",
      createInvocation: (workDir, mainTex) => ({
        command: "xelatex",
        args: ["-interaction=nonstopmode", "-halt-on-error", `-output-directory=${workDir}`, mainTex],
        cwd: workDir
      })
    };
  }

  const dockerAvailable = await hasCommand("docker");
  if (dockerAvailable && await commandSucceeds("docker", ["image", "inspect", dockerImage])) {
    console.warn(`pdf_info: using Docker fallback (${dockerImage}) because local xelatex is unavailable`);
    return {
      label: `docker:${dockerImage}`,
      createInvocation: (workDir) => ({
        command: "docker",
        args: [
          "run", "--rm",
          "-v", `${workDir}:/work`,
          "-w", "/work",
          dockerImage,
          "xelatex",
          "-interaction=nonstopmode",
          "-halt-on-error",
          "-output-directory=/work",
          "/work/main.tex"
        ],
        cwd: root
      })
    };
  }

  const message = dockerAvailable
    ? `xelatex is not installed and Docker image '${dockerImage}' is unavailable; run 'make docker-build' or install texlive-xetex`
    : "xelatex is not installed and Docker is unavailable; install texlive-xetex or use Docker";
  if (strictPdf) throw new Error(message);
  console.warn(`pdf_skip: ${message}`);
  process.exit(0);
}

await main();

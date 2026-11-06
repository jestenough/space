import { spawnSync } from "node:child_process";

const python = process.env.PYTHON ?? (process.platform === "win32" ? "python" : "python3");
const shell = process.platform === "win32";

const run = (command, args) => {
  const result = spawnSync(command, args, { stdio: "inherit", shell });
  if (result.status !== 0) process.exit(result.status ?? 1);
};

run("npm", ["run", "build"]);
run(python, ["-m", "scripts.cli", "prerender"]);
run(python, ["-m", "scripts.cli", "seo"]);
run("npm", ["run", "preview"]);

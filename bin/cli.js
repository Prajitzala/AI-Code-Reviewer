#!/usr/bin/env node

import chalk from "chalk";
import fs from "fs";
import ora from "ora";
import path from "path";
import prompts from "prompts";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PACKAGE_ROOT = path.resolve(__dirname, "..");
const DOCS_REL_PATH = "docs/ai-code-reviewer.md";

const REQUIREMENTS = "python-dotenv>=1.0.0\n";

const MODEL_CHOICES = [
  { title: "GPT-4o (recommended)", value: "gpt-4o" },
  { title: "GPT-4o-mini (faster/cheaper)", value: "gpt-4o-mini" },
];

const DIFF_CHOICES = [
  { title: "8000", value: 8000 },
  { title: "12000 (recommended)", value: 12000 },
  { title: "20000", value: 20000 },
];

const MANAGED_FILES = [
  ".github/workflows/ai-review.yml",
  "scripts/review.py",
  "scripts/requirements.txt",
  DOCS_REL_PATH,
];

function cwdPath(...segments) {
  return path.join(process.cwd(), ...segments);
}

function templatePath(...segments) {
  return path.join(PACKAGE_ROOT, "templates", ...segments);
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function copyFile(src, dest) {
  ensureDir(dest);
  fs.copyFileSync(src, dest);
}

function printBanner() {
  console.log(chalk.blue.bold("\n🤖 AI Code Reviewer — Powered by GPT-4o\n"));
}

function printHelp() {
  console.log(`
${chalk.bold("AI Code Reviewer")} — AI-powered PR reviews on GitHub Actions

${chalk.bold("Usage:")}
  ai-code-reviewer <command>

${chalk.bold("Commands:")}
  init     Set up AI Code Reviewer in the current repository
  remove   Remove generated workflow and scripts
  help     Show this message

${chalk.gray("Docs:")} run ${chalk.cyan("init")} to add ${chalk.cyan(DOCS_REL_PATH)} to your repo
`);
}

function fail(message) {
  console.error(chalk.red(`\n✖ ${message}\n`));
  process.exit(1);
}

function assertGitRepo() {
  if (!fs.existsSync(cwdPath(".git"))) {
    fail("Not a git repository. Run this command from your project root.");
  }
}

function nonInteractiveDefaults() {
  if (process.env.AI_REVIEWER_NO_PROMPT === "1") {
    return { model: "gpt-4o", maxDiffChars: 12000 };
  }
  return null;
}

async function confirmOverwrite(workflowPath) {
  if (process.env.AI_REVIEWER_YES === "1") {
    return true;
  }

  if (!fs.existsSync(workflowPath)) {
    return true;
  }

  const { overwrite } = await prompts({
    type: "confirm",
    name: "overwrite",
    message: ".github/workflows/ai-review.yml already exists. Overwrite?",
    initial: false,
  });

  if (overwrite === undefined) {
    console.log(chalk.gray("\nCancelled.\n"));
    process.exit(0);
  }

  return overwrite;
}

async function askSetupOptions() {
  const defaults = nonInteractiveDefaults();
  if (defaults) {
    return defaults;
  }

  const answers = await prompts([
    {
      type: "select",
      name: "model",
      message: "Which model?",
      choices: MODEL_CHOICES,
      initial: 0,
    },
    {
      type: "select",
      name: "maxDiffChars",
      message: "Max diff size?",
      choices: DIFF_CHOICES,
      initial: 1,
    },
  ]);

  if (!answers.model || answers.maxDiffChars === undefined) {
    console.log(chalk.gray("\nCancelled.\n"));
    process.exit(0);
  }

  return answers;
}

function scaffoldReviewPy(model, maxDiffChars) {
  let source = fs.readFileSync(templatePath("review.py"), "utf8");
  source = source.replaceAll("__MODEL__", model);
  source = source.replaceAll("__MAX_DIFF_CHARS__", String(maxDiffChars));
  return source;
}

async function cmdInit() {
  printBanner();
  assertGitRepo();

  const workflowPath = cwdPath(".github/workflows/ai-review.yml");
  const shouldContinue = await confirmOverwrite(workflowPath);
  if (!shouldContinue) {
    console.log(chalk.gray("\nSetup skipped.\n"));
    process.exit(0);
  }

  const { model, maxDiffChars } = await askSetupOptions();

  const spinner = ora("Setting up @prajitzala/ai-code-reviewer...").start();

  try {
    copyFile(templatePath("ai-review.yml"), workflowPath);

    const reviewDest = cwdPath("scripts/review.py");
    ensureDir(reviewDest);
    fs.writeFileSync(reviewDest, scaffoldReviewPy(model, maxDiffChars));

    const requirementsPath = cwdPath("scripts/requirements.txt");
    if (!fs.existsSync(requirementsPath)) {
      ensureDir(requirementsPath);
      fs.writeFileSync(requirementsPath, REQUIREMENTS);
    }

    copyFile(path.join(PACKAGE_ROOT, "README.md"), cwdPath(DOCS_REL_PATH));

    spinner.succeed("Setup complete");
  } catch (err) {
    spinner.fail("Setup failed");
    fail(err.message);
  }

  console.log(chalk.green.bold("\n✓ AI Code Reviewer is ready!\n"));
  console.log(chalk.bold("Next steps — add your OpenAI API key:\n"));
  console.log("  1. Open GitHub → your repo → Settings → Secrets and variables → Actions");
  console.log("  2. Click \"New repository secret\"");
  console.log("  3. Name: OPENAI_API_KEY");
  console.log("  4. Value: your OpenAI API key from https://platform.openai.com/api-keys\n");
  console.log(
    chalk.gray("Open a pull request to trigger the workflow automatically.\n"),
  );
  const localDocs = path.relative(process.cwd(), cwdPath(DOCS_REL_PATH));
  console.log(chalk.gray(`Documentation: ${localDocs}\n`));
}

async function cmdRemove() {
  printBanner();

  const existing = MANAGED_FILES.filter((f) => fs.existsSync(cwdPath(f)));
  if (existing.length === 0) {
    console.log(chalk.gray("Nothing to remove — AI Code Reviewer is not set up here.\n"));
    process.exit(0);
  }

  let confirm = process.env.AI_REVIEWER_YES === "1";
  if (!confirm) {
    const answer = await prompts({
      type: "confirm",
      name: "confirm",
      message: "Remove AI Code Reviewer from this repository?",
      initial: false,
    });
    confirm = answer.confirm;
  }

  if (!confirm) {
    console.log(chalk.gray("\nCancelled.\n"));
    process.exit(0);
  }

  for (const rel of MANAGED_FILES) {
    const filePath = cwdPath(rel);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  }

  console.log(chalk.green.bold("\n✓ AI Code Reviewer removed.\n"));
  console.log(
    chalk.gray(
      "Deleted: .github/workflows/ai-review.yml, scripts/review.py, scripts/requirements.txt, docs/ai-code-reviewer.md\n",
    ),
  );
}

async function main() {
  const command = process.argv[2];

  switch (command) {
    case "init":
      await cmdInit();
      break;
    case "remove":
      await cmdRemove();
      break;
    case "help":
    case "-h":
    case "--help":
      printHelp();
      break;
    case undefined:
      printHelp();
      process.exit(1);
      break;
    default:
      console.error(chalk.red(`Unknown command: ${command}\n`));
      printHelp();
      process.exit(1);
  }
}

main().catch((err) => {
  fail(err.message);
});

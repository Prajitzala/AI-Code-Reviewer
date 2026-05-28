# AI Code Reviewer

[![npm version](https://img.shields.io/npm/v/@prajitzala/ai-code-reviewer)](https://www.npmjs.com/package/@prajitzala/ai-code-reviewer)
[![npm downloads](https://img.shields.io/npm/dm/@prajitzala/ai-code-reviewer)](https://www.npmjs.com/package/@prajitzala/ai-code-reviewer)
[![AI Code Review](https://github.com/Prajitzala/Prajitzala/actions/workflows/ai-review.yml/badge.svg)](https://github.com/Prajitzala/Prajitzala/actions/workflows/ai-review.yml)

AI-powered pull request reviews on GitHub Actions, powered by OpenAI GPT-4o.

## Demo

See a live review on [Prajitzala/Prajitzala#1](https://github.com/Prajitzala/Prajitzala/pull/1) — the Action posts a summary comment (verdict, summary, positives) on every pull request.

## Quick start

```bash
npx @prajitzala/ai-code-reviewer init
```

This adds a GitHub Actions workflow and review script to your repository.

## Setup

### 1. Install in your repo

From your project root (must be a git repository):

```bash
npx @prajitzala/ai-code-reviewer init
```

Choose your model and max diff size when prompted.

### 2. Add the OpenAI API key secret

1. Open your repo on GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `OPENAI_API_KEY`
4. Value: your key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

`GITHUB_TOKEN` is provided automatically by GitHub Actions.

### 3. Open a pull request

The workflow runs on `pull_request` events (`opened`, `synchronize`, `reopened`) and posts a review summary comment (and inline comments when possible).

## Commands

| Command | Description |
| --- | --- |
| `init` | Add workflow + scripts to the current repo |
| `remove` | Remove generated files |
| `help` | Show usage |

## Configuration

During `init` you can choose:

- **Model:** `gpt-4o` (recommended) or `gpt-4o-mini`
- **Max diff size:** `8000`, `12000` (recommended), or `20000` characters sent to the model

To change settings later, run `init` again and confirm overwrite, or edit `scripts/review.py` directly.

## Local testing

```bash
export OPENAI_API_KEY=sk-...
export GITHUB_TOKEN=ghp_...
export REPO=owner/repo
export PR_NUMBER=1
export BASE_SHA=...
export HEAD_SHA=...

python scripts/test_local.py
```

## Uninstall

```bash
npx @prajitzala/ai-code-reviewer remove
```

## License

ISC

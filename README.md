# 🤖 @prajitzala/ai-code-reviewer

> Add AI-powered PR code reviews to any GitHub repo in one command.

[![npm version](https://img.shields.io/npm/v/@prajitzala/ai-code-reviewer?style=for-the-badge&logo=npm&color=CB3837)](https://www.npmjs.com/package/@prajitzala/ai-code-reviewer)
[![npm downloads](https://img.shields.io/npm/dm/@prajitzala/ai-code-reviewer?style=for-the-badge&logo=npm)](https://www.npmjs.com/package/@prajitzala/ai-code-reviewer)
[![AI Code Review](https://github.com/Prajitzala/Prajitzala/actions/workflows/ai-review.yml/badge.svg)](https://github.com/Prajitzala/Prajitzala/actions/workflows/ai-review.yml)
![OpenAI](https://img.shields.io/badge/OpenAI_GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

---

## ⚡ Install in 60 Seconds

```bash
npx @prajitzala/ai-code-reviewer init
```

That's it. Run this from the root of any GitHub repo — it sets up everything automatically.

**Package:** [npm/@prajitzala/ai-code-reviewer](https://www.npmjs.com/package/@prajitzala/ai-code-reviewer) · **Source:** [github.com/Prajitzala/AI-Code-Reviewer](https://github.com/Prajitzala/AI-Code-Reviewer)

---

## 🎥 Demo

Live Action output on a real PR: [Prajitzala/Prajitzala#1](https://github.com/Prajitzala/Prajitzala/pull/1) (summary comment + inline comments on the diff).

---

## 🎬 What Happens

```
$ npx @prajitzala/ai-code-reviewer init

  ╔══════════════════════════════════╗
  ║     🤖  AI Code Reviewer         ║
  ║     Powered by GPT-4o            ║
  ╚══════════════════════════════════╝

? Which OpenAI model should the reviewer use?
  ❯ GPT-4o  (best quality, recommended)
    GPT-4o-mini  (faster, cheaper)

? Max diff size to review per PR?
  ❯ 12,000 chars  (recommended)

  ✔  .github/workflows/ai-review.yml
  ✔  scripts/review.py
  ✔  scripts/requirements.txt

  🚀 One step left:
  Add OPENAI_API_KEY to your repo secrets.
  Repo → Settings → Secrets → New secret
  Done! Open a PR and watch the magic 🎉
```

Then add your OpenAI API key as a GitHub secret and open any PR.

---

## 🔍 What the Review Looks Like

Every PR automatically gets a comment like this:

```
✅ AI Code Review — GPT-4o

Overall clean implementation. One security issue and two
suggestions were found.

Verdict: REQUEST_CHANGES

---
🔍 Issues Found

🔴 🔐 Hardcoded Secret Key
- Severity: critical   Category: security
- File: middleware/auth.js  line: 14
- JWT secret is hardcoded. Use process.env.JWT_SECRET instead.

🟡 🐛 Missing Error Handling
- Severity: warning   Category: bug
- File: routes/user.js  line: 42
- Async function has no try/catch — will crash in production.

---
👍 What's Good
- Clean separation of concerns
- Consistent use of async/await
```

Plus inline comments posted directly on the diff lines.

---

## 📋 What Gets Reviewed

| Category | What It Checks |
|---|---|
| 🐛 Bug | Logic errors, null refs, unhandled promises |
| 🔐 Security | Hardcoded secrets, injection risks, auth issues |
| ⚡ Performance | N+1 queries, unnecessary re-renders, blocking ops |
| ✨ Quality | Naming, duplication, complexity, missing tests |

Lock files and binary assets are automatically skipped.

---

## 🛠️ Commands

```bash
npx @prajitzala/ai-code-reviewer init     # Set up in current repo
npx @prajitzala/ai-code-reviewer remove   # Remove from current repo
npx @prajitzala/ai-code-reviewer help     # Show help
```

---

## 🗂️ Files Created in Your Repo

```
your-repo/
├── .github/
│   └── workflows/
│       └── ai-review.yml      # Triggers on every PR
└── scripts/
    ├── review.py              # GPT-4o review logic
    └── requirements.txt       # Python deps
```

---

## ⚙️ How It Works

```
PR opened / updated
       │
       ▼
GitHub Action triggers
       │
       ▼
Python fetches PR diff (GitHub API)
       │
       ▼
Diff sent to GPT-4o (JSON mode)
       │
       ├──▶ Summary comment posted on PR
       └──▶ Inline comments on diff lines
```

---

## 🔮 Roadmap

- [ ] Support Anthropic Claude as alternative LLM
- [ ] `.aireview` config file per repo
- [ ] Severity threshold flag — only post if critical issues found
- [ ] Auto-approve clean PRs
- [ ] Re-review on new commits (deduplication)

---

## 🧑‍💻 Author

**Prajit Zala** — [linkedin.com/in/prajitzala](https://linkedin.com/in/prajitzala) · [github.com/Prajitzala](https://github.com/Prajitzala)

---

## 📄 License

MIT — use it, fork it, improve it.

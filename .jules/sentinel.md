## 2024-05-15 - [Information Disclosure Prevention in .gitignore]
**Vulnerability:** The initial `.gitignore` file only ignored `.env` and left log files, databases (`agent_economy.db`), and compiled python files (`*.pyc`) vulnerable to accidental commit.
**Learning:** These files can inadvertently leak sensitive information, such as system logs, user activity, agent reputations, task queues, and potentially internal system errors if tracked in version control.
**Prevention:** Always comprehensively configure `.gitignore` early in a project to exclude files that might inadvertently leak state or system information.

## 2024-05-18 - [Fail Securely on Missing Secrets]
**Vulnerability:** Initial setup relied on implicit fallback or None for critical environment variables like API keys (`GEMINI_API_KEY`). This could lead to downstream security issues, unpredictable behavior, or silent failures where errors leak context.
**Learning:** Security requires defensive coding at boundaries. If an environment depends on a secret to function correctly, its absence should immediately trigger a clear and specific failure rather than deferring the error.
**Prevention:** Explicitly validate the presence of sensitive environment variables immediately after loading them, raising structured exceptions (like `ValueError`) to halt execution securely.

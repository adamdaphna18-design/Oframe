## 2024-05-15 - [Information Disclosure Prevention in .gitignore]
**Vulnerability:** The initial `.gitignore` file only ignored `.env` and left log files, databases (`agent_economy.db`), and compiled python files (`*.pyc`) vulnerable to accidental commit.
**Learning:** These files can inadvertently leak sensitive information, such as system logs, user activity, agent reputations, task queues, and potentially internal system errors if tracked in version control.
**Prevention:** Always comprehensively configure `.gitignore` early in a project to exclude files that might inadvertently leak state or system information.

## 2024-05-15 - [Secure Environment Variable Handling]
**Vulnerability:** Core services (like `multi_model_router`) were loading API keys (`GEMINI_API_KEY`) without validation, potentially leading to silent failures or obscure downstream errors if the keys were missing.
**Learning:** Failing to validate required secrets immediately upon load means the system might spin up in a degraded state and pass `None` to external APIs, making debugging harder and potentially leaking intent.
**Prevention:** Always validate critical environment variables explicitly after `os.getenv` and raise a clear exception (e.g., `ValueError`) to fail securely and fast during startup.

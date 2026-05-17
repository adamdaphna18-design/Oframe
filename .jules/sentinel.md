## 2024-05-15 - [Information Disclosure Prevention in .gitignore]
**Vulnerability:** The initial `.gitignore` file only ignored `.env` and left log files, databases (`agent_economy.db`), and compiled python files (`*.pyc`) vulnerable to accidental commit.
**Learning:** These files can inadvertently leak sensitive information, such as system logs, user activity, agent reputations, task queues, and potentially internal system errors if tracked in version control.
**Prevention:** Always comprehensively configure `.gitignore` early in a project to exclude files that might inadvertently leak state or system information.

## 2024-05-17 - [Secure Environment Variable Loading & Comprehensive .gitignore]
**Vulnerability:** Core configurations like `multi_model_router.py` failed silently or had downstream errors when critical environment variables (like API keys) were missing. Additionally, the `.gitignore` left `.env.*` permutations and private keys/certificates susceptible to accidental commit.
**Learning:** Silently failing on missing environment variables can leave the application in an unpredictable or insecure state. A weak `.gitignore` is a major vector for credential leakage.
**Prevention:** Follow the "fail fast" and secure-by-default principles: explicitly validate required environment variables at initialization (e.g., raise ValueError), and enforce a comprehensive `.gitignore` including `*.pem`, `*.key`, `*.cert`, and `.env.*`.

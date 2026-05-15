## 2024-05-15 - [Information Disclosure Prevention in .gitignore]
**Vulnerability:** The initial `.gitignore` file only ignored `.env` and left log files, databases (`agent_economy.db`), and compiled python files (`*.pyc`) vulnerable to accidental commit.
**Learning:** These files can inadvertently leak sensitive information, such as system logs, user activity, agent reputations, task queues, and potentially internal system errors if tracked in version control.
**Prevention:** Always comprehensively configure `.gitignore` early in a project to exclude files that might inadvertently leak state or system information.

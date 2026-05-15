## 2024-05-15 - Micro-optimizations
**Learning:** Evaluated providing explicit paths to `load_dotenv` to avoid the directory traversal of `find_dotenv()`. This is an extreme micro-optimization with zero measurable impact and violates the rule to avoid premature micro-optimizations without a tangible bottleneck.
**Action:** Do not create a PR for micro-optimizations. Always ensure there is a measurable bottleneck before optimizing.

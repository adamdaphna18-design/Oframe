class Skill:
    def __init__(self, name, data):
        self.name = name
        self.data = data
        self.dependencies = data.get("dependencies", [])
        self.payload = data.get("payload", {})

    def get(self, key, default=None):
        return self.data.get(key, default)

class SkillGraph:
    def __init__(self):
        self._skills = {}
        self._stats = {}

    def add_skill(self, name, data):
        self._skills[name] = Skill(name, data)
        self._stats[name] = {"success_count": 0, "total_runs": 0, "last_run": None}

    @property
    def skills(self):
        return self._skills.values()

    def get_skill(self, name):
        return self._skills.get(name)

    def stats(self, name):
        return self._stats.get(name, {})

    def is_satisfied(self, name):
        # A simple check: a dependency is satisfied if it has run successfully at least once recently.
        # This can be made more sophisticated (e.g. checking recent events)
        st = self.stats(name)
        if not st:
            return False
        return st.get("success_count", 0) > 0

    def record_outcome(self, name, success):
        from datetime import datetime
        if name not in self._stats:
            self._stats[name] = {"success_count": 0, "total_runs": 0, "last_run": None}
        self._stats[name]["total_runs"] += 1
        if success:
            self._stats[name]["success_count"] += 1
        self._stats[name]["last_run"] = datetime.now()

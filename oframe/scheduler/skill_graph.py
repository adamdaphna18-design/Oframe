from typing import Dict, List, Any, Optional
from collections import defaultdict

class SkillNode:
    def __init__(self, name: str, handler: str, dependencies: List[str] = None,
                 trigger: str = "interval", probability: float = 1.0,
                 event: Optional[str] = None, condition: str = ""):
        self.name = name
        self.handler = handler
        self.dependencies = dependencies or []
        self.trigger = trigger
        self.probability = probability
        self.event = event
        self.condition = condition
        self.stats = {"success": 0, "failure": 0, "last_run": None}

class SkillGraph:
    def __init__(self):
        self.skills: Dict[str, SkillNode] = {}
        self.dependency_graph = defaultdict(list)

    def add_skill(self, skill: SkillNode):
        self.skills[skill.name] = skill
        for dep in skill.dependencies:
            self.dependency_graph[dep].append(skill.name)

    def get_skill(self, name: str) -> Optional[SkillNode]:
        return self.skills.get(name)

    def is_satisfied(self, skill_name: str) -> bool:
        node = self.skills.get(skill_name)
        if not node:
            return True
        for dep in node.dependencies:
            if self.skills[dep].stats["last_run"] is None:
                return False
        return True

    def record_outcome(self, skill_name: str, success: bool):
        node = self.skills.get(skill_name)
        if node:
            if success:
                node.stats["success"] += 1
            else:
                node.stats["failure"] += 1
            node.stats["last_run"] = __import__("time").time()

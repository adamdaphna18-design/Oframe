from typing import List, Tuple, Any

class CooperativeSlotAllocator:
    def allocate(self, skill_name: str, requests: List[Tuple[Any, float, float]]) -> Any:
        if not requests:
            return None
        weighted = [(rep * bid, agent) for agent, bid, rep in requests]
        return max(weighted, key=lambda x: x[0])[1]

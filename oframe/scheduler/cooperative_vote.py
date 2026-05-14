# oframe/scheduler/cooperative_vote.py
from typing import List, Tuple, Any

class CooperativeSlotAllocator:
    """Allocate execution slots based on agent reputation and bid."""
    def allocate(self, skill_name: str, requests: List[Tuple[Any, float, float]]) -> Any:
        """
        requests: list of (agent, bid_cents, reputation)
        returns the winning agent
        """
        if not requests:
            return None
        # weighted by reputation * bid
        weighted = [(rep * bid, agent) for agent, bid, rep in requests]
        return max(weighted, key=lambda x: x[0])[1]

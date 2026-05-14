class CooperativeSlotAllocator:
    def allocate(self, skill, requested_slots):
        """
        requested_slots: list of (agent, (bid, reputation))
        """
        if not requested_slots:
            return None
        # each agent proposes a time slot and a reputation-weighted bid
        # winner is the one with highest (reputation * bid)
        # runner-ups get their bids refunded (mock payment)
        weighted = [(rep * bid, agent) for agent, (bid, rep) in requested_slots]
        winner = max(weighted)[1]
        return winner

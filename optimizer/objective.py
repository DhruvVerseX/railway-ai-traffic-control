class OptimizationObjective:

    def __init__(
        self,
        throughput_weight=100.0,
        waiting_weight=1.0,
        delay_weight=1.0,
        conflict_weight=50.0,
        priority_weight=5.0,
    ):
        self.throughput_weight = throughput_weight
        self.waiting_weight = waiting_weight
        self.delay_weight = delay_weight
        self.conflict_weight = conflict_weight
        self.priority_weight = priority_weight

    def calculate_score(self, metrics, action=None):

        throughput = metrics["throughput_trains_per_hour"]
        waiting = metrics["total_waiting_time_min"]
        delay = metrics["initial_delay_min"]
        conflicts = metrics["conflicts"]

        score = (
            self.throughput_weight * throughput
            - self.waiting_weight * waiting
            - self.delay_weight * delay
            - self.conflict_weight * conflicts
        )

        # -------------------------------------------------
        # PRIORITY BONUS
        # -------------------------------------------------
        #
        # Only RELEASE actions receive a priority bonus.
        # HOLD receives no bonus because it does not release
        # the train into the section.
        #
        # The actual railway priority comes from trains.csv.
        #

        priority_bonus = 0.0

        if action is not None:
            if action.get("action") == "RELEASE":
                priority = float(
                    action.get("priority", 0)
                )

                priority_bonus = (
                    self.priority_weight * priority
                )

        score += priority_bonus

        return round(score, 4)

    def explain_score(self, metrics, action=None):

        throughput = metrics["throughput_trains_per_hour"]
        waiting = metrics["total_waiting_time_min"]
        delay = metrics["initial_delay_min"]
        conflicts = metrics["conflicts"]

        priority = 0.0
        priority_bonus = 0.0

        if action is not None:
            if action.get("action") == "RELEASE":
                priority = float(
                    action.get("priority", 0)
                )

                priority_bonus = (
                    self.priority_weight * priority
                )

        score = (
            self.throughput_weight * throughput
            - self.waiting_weight * waiting
            - self.delay_weight * delay
            - self.conflict_weight * conflicts
            + priority_bonus
        )

        return {
            "throughput_contribution":
                self.throughput_weight * throughput,

            "waiting_penalty":
                self.waiting_weight * waiting,

            "delay_penalty":
                self.delay_weight * delay,

            "conflict_penalty":
                self.conflict_weight * conflicts,

            "priority":
                priority,

            "priority_bonus":
                priority_bonus,

            "final_score":
                round(score, 4),
        }
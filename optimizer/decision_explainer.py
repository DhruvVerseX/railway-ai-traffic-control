class DecisionExplainer:

    def explain(self, best_action, evaluations):

        if best_action is None:
            return "No valid action is available."

        train_id = best_action["train_id"]
        action = best_action["action"]
        section_id = best_action["section_id"]
        score = best_action["score"]

        priority = best_action.get(
            "priority",
            0
        )

        reason = best_action.get(
            "reason",
            ""
        )

        metrics = best_action.get(
            "metrics",
            {}
        )

        throughput = metrics.get(
            "throughput_trains_per_hour",
            0
        )

        waiting = metrics.get(
            "total_waiting_time_min",
            0
        )

        conflicts = metrics.get(
            "conflicts",
            0
        )

        lines = []

        lines.append(
            f"Recommended action: {action} {train_id}"
        )

        lines.append(
            f"Section: {section_id}"
        )

        lines.append(
            f"Train priority: {priority:g}"
        )

        lines.append(
            f"Safety: {reason}"
        )

        lines.append(
            f"Predicted throughput: "
            f"{throughput:.2f} trains/hour"
        )

        lines.append(
            f"Predicted total waiting time: "
            f"{waiting:.1f} minutes"
        )

        lines.append(
            f"Predicted conflicts: {conflicts}"
        )

        lines.append(
            f"Optimization score: {score:.2f}"
        )

        # -------------------------------------------------
        # COMPARE AGAINST OTHER SAFE ACTIONS
        # -------------------------------------------------

        alternatives = [
            evaluation
            for evaluation in evaluations
            if evaluation["train_id"] != train_id
            or evaluation["action"] != action
        ]

        if alternatives:

            best_alternative = max(
                alternatives,
                key=lambda x: x["score"]
            )

            score_difference = (
                score -
                best_alternative["score"]
            )

            lines.append("")

            lines.append(
                "Comparison with best alternative:"
            )

            lines.append(
                f"{best_alternative['action']} "
                f"{best_alternative['train_id']} "
                f"→ score "
                f"{best_alternative['score']:.2f}"
            )

            lines.append(
                f"Selected action improves the "
                f"optimization score by "
                f"{score_difference:.2f}."
            )

        return "\n".join(lines)
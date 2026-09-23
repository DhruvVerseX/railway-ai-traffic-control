import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from controller.ai_safety_controller import AISafetyController


class AITrainTrafficController:
    """
    Actual AI-based traffic controller.

    At each decision point:
    1. Finds eligible waiting trains.
    2. Gets an ML recommendation for each.
    3. Applies the safety layer.
    4. Selects one safe action.
    5. Executes RELEASE when appropriate.
    """

    def __init__(self, network, train_database):
        self.network = network
        self.train_database = train_database

        self.ai_safety_controller = AISafetyController(
            network,
            train_database
        )

    # ========================================================
    # ELIGIBLE TRAINS
    # ========================================================

    def get_eligible_trains(self, simulator):
        """
        Return waiting trains that have reached their entry time.
        """

        eligible = []

        for train_id, train in simulator.trains.items():

            if train.status != "WAITING":
                continue

            if simulator.current_time_min < train.entry_time_min:
                continue

            eligible.append(train_id)

        return eligible

    # ========================================================
    # GET RECOMMENDATIONS
    # ========================================================

    def get_recommendations(self, simulator):
        """
        Generate an AI + safety recommendation for every
        eligible train.
        """

        recommendations = []

        eligible_trains = self.get_eligible_trains(
            simulator
        )

        for train_id in eligible_trains:

            result = self.ai_safety_controller.decide(
                simulator,
                train_id
            )

            recommendations.append(result)

        return recommendations

    # ========================================================
    # SELECT ACTION
    # ========================================================

    def select_action(self, recommendations):
        """
        Select the best safe recommendation.

        RELEASE recommendations are preferred over HOLD.
        Among multiple RELEASE recommendations, choose the
        train with the highest RELEASE probability.
        """

        if not recommendations:
            return None

        safe_releases = [
            result
            for result in recommendations
            if (
                result["final_action"] == "RELEASE"
                and result["safe"]
            )
        ]

        if safe_releases:

            best = max(
                safe_releases,
                key=lambda result:
                    result["probabilities"].get(
                        "RELEASE",
                        0.0
                    )
            )

            return best

        # If nobody can safely be released, select the
        # strongest HOLD recommendation for reporting.
        best_hold = max(
            recommendations,
            key=lambda result:
                result["probabilities"].get(
                    "HOLD",
                    0.0
                )
        )

        return best_hold

    # ========================================================
    # EXECUTE ACTION
    # ========================================================

    def execute_action(self, simulator, recommendation):
        """
        Execute the selected AI recommendation.

        HOLD does not change simulator state.
        RELEASE attempts to start the train.
        """

        if recommendation is None:

            return {
                "executed": False,
                "reason": "No recommendation available."
            }

        train_id = recommendation["train_id"]

        if recommendation["final_action"] == "HOLD":

            return {
                "executed": False,
                "reason": (
                    f"Train {train_id} held by AI controller."
                )
            }

        if recommendation["final_action"] == "RELEASE":

            executed = simulator.start_train(
                train_id
            )

            if executed:

                return {
                    "executed": True,
                    "reason": (
                        f"Train {train_id} released by "
                        f"AI controller."
                    )
                }

            return {
                "executed": False,
                "reason": (
                    f"Train {train_id} could not be released "
                    f"by simulator."
                )
            }

        return {
            "executed": False,
            "reason": "Unknown AI action."
        }

    # ========================================================
    # MAKE DECISION
    # ========================================================

    def make_decision(self, simulator):
        """
        Generate recommendations, select the best action,
        and return the selected recommendation.
        """

        recommendations = self.get_recommendations(
            simulator
        )

        selected = self.select_action(
            recommendations
        )

        return {
            "time_min": simulator.current_time_min,
            "recommendations": recommendations,
            "selected_action": selected
        }

    # ========================================================
    # RUN ONE CONTROL STEP
    # ========================================================

    def control_step(self, simulator):
        """
        Perform one complete AI control step.
        """

        decision = self.make_decision(
            simulator
        )

        execution = self.execute_action(
            simulator,
            decision["selected_action"]
        )

        decision["execution"] = execution

        return decision
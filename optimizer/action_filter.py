import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector


class ActionFilter:

    def __init__(
        self,
        simulator: RailwaySimulator,
        conflict_detector: ConflictDetector,
    ):

        self.simulator = simulator
        self.conflict_detector = conflict_detector

    # ---------------------------------------------------------
    # CHECK SINGLE ACTION
    # ---------------------------------------------------------

    def check_action(self, action):

        train_id = action["train_id"]
        action_type = action["action"]
        section_id = action["section_id"]

        # -----------------------------------------------------
        # HOLD
        # -----------------------------------------------------

        if action_type == "HOLD":

            return {
                **action,
                "safe": True,
                "reason": "Holding the train is safe.",
                "required_wait_min": 0.0,
            }

        # -----------------------------------------------------
        # RELEASE
        # -----------------------------------------------------

        if action_type == "RELEASE":

            conflict_result = (
                self.conflict_detector.check_section_conflict(
                    train_id,
                    section_id,
                )
            )

            if conflict_result["conflict"]:

                return {
                    **action,
                    "safe": False,
                    "reason": conflict_result["reason"],
                    "required_wait_min": (
                        conflict_result[
                            "required_wait_min"
                        ]
                    ),
                }

            return {
                **action,
                "safe": True,
                "reason": "Release is safe.",
                "required_wait_min": 0.0,
            }

        # -----------------------------------------------------
        # UNKNOWN ACTION
        # -----------------------------------------------------

        return {
            **action,
            "safe": False,
            "reason": f"Unknown action: {action_type}",
            "required_wait_min": 0.0,
        }

    # ---------------------------------------------------------
    # FILTER ALL ACTIONS
    # ---------------------------------------------------------

    def filter_actions(self, actions):

        safe_actions = []
        unsafe_actions = []

        for action in actions:

            result = self.check_action(action)

            if result["safe"]:

                safe_actions.append(result)

            else:

                unsafe_actions.append(result)

        return safe_actions, unsafe_actions


# -------------------------------------------------------------
# TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    from simulation.network import RailwayNetwork
    from input.input_state import TrainDatabase
    from input.scenario_loader import load_scenario
    from optimizer.candidate_actions import (
        CandidateActionGenerator
    )

    print("=== Action Filter Test ===")

    # ---------------------------------------------------------
    # LOAD SYSTEM
    # ---------------------------------------------------------

    network = RailwayNetwork()

    database = TrainDatabase()

    scenario, traffic = load_scenario(
        "example_scenario.json",
        database
    )

    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic,
        database
    )

    conflict_detector = ConflictDetector(
        simulator
    )

    generator = CandidateActionGenerator(
        simulator,
        database
    )

    filter_engine = ActionFilter(
        simulator,
        conflict_detector
    )

    # ---------------------------------------------------------
    # MOVE TO t = 2
    # ---------------------------------------------------------

    simulator.advance_time(2)

    # ---------------------------------------------------------
    # GENERATE CANDIDATES
    # ---------------------------------------------------------

    actions = generator.generate_actions()

    print("\n=== CANDIDATE ACTIONS ===")

    for action in actions:

        print(action)

    # ---------------------------------------------------------
    # FILTER
    # ---------------------------------------------------------

    safe_actions, unsafe_actions = (
        filter_engine.filter_actions(actions)
    )

    print("\n=== SAFE ACTIONS ===")

    for action in safe_actions:

        print(action)

    print("\n=== UNSAFE ACTIONS ===")

    for action in unsafe_actions:

        print(action)
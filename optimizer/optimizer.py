import sys
from pathlib import Path
from copy import deepcopy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector
from metrics.metrics import SimulationMetrics
try:
    from optimizer.candidate_actions import CandidateActionGenerator
    from optimizer.action_filter import ActionFilter
    from optimizer.objective import OptimizationObjective
except ModuleNotFoundError:
    from candidate_actions import CandidateActionGenerator
    from action_filter import ActionFilter
    from objective import OptimizationObjective

class TrainTrafficOptimizer:

    def __init__(
        self,
        simulator: RailwaySimulator,
        train_database,
        evaluation_horizon_min=60.0,
    ):

        self.simulator = simulator
        self.train_database = train_database

        self.evaluation_horizon_min = (
            evaluation_horizon_min
        )

        # Centralized objective function
        self.objective = OptimizationObjective()
    def _create_candidate_generator(
        self,
        simulator,
    ):

        return CandidateActionGenerator(
            simulator,
            self.train_database,
        )

    # ---------------------------------------------------------
    # CREATE ACTION FILTER
    # ---------------------------------------------------------

    def _create_action_filter(
        self,
        simulator,
    ):

        conflict_detector = ConflictDetector(
            simulator
        )

        return ActionFilter(
            simulator,
            conflict_detector,
        )

    # ---------------------------------------------------------
    # APPLY ACTION
    # ---------------------------------------------------------

    def _apply_action(
        self,
        simulator,
        action,
    ):

        train_id = action["train_id"]
        action_type = action["action"]

        if action_type == "HOLD":

            # Train remains waiting.
            return {
                "executed": True,
                "reason": "Train remains on hold.",
            }

        if action_type == "RELEASE":

            success = simulator.start_train(
                train_id
            )

            if success:

                return {
                    "executed": True,
                    "reason": (
                        f"Train {train_id} released."
                    ),
                }

            return {
                "executed": False,
                "reason": (
                    f"Train {train_id} could not "
                    f"be released."
                ),
            }

        return {
            "executed": False,
            "reason": (
                f"Unknown action: {action_type}"
            ),
        }

    # ---------------------------------------------------------
    # EVALUATE ONE ACTION
    # ---------------------------------------------------------

    def evaluate_action(
        self,
        action,
    ):

        # Create an independent copy of the current
        # simulation state.
        test_simulator = deepcopy(
            self.simulator
        )

        # Apply the candidate action
        execution = self._apply_action(
            test_simulator,
            action,
        )

        # If release failed, this candidate is not useful.
        if not execution["executed"]:

            return {
                **action,
                "score": float("-inf"),
                "execution": execution,
                "metrics": None,
            }

        # Simulate the consequences of the action
        test_simulator.advance_time(
            self.evaluation_horizon_min
        )

        # Calculate resulting metrics
        metrics_engine = SimulationMetrics(
            test_simulator
        )

        metrics = metrics_engine.calculate_all()

        # -----------------------------------------------------
        # OBJECTIVE FUNCTION
        # -----------------------------------------------------

        score = self.objective.calculate_score(
            metrics,
            action
        )

        return {
            **action,
            "score": score,
            "execution": execution,
            "metrics": metrics,
        }
    # ---------------------------------------------------------
    # FIND BEST ACTION
    # ---------------------------------------------------------

    def find_best_action(self):

        # -----------------------------------------------------
        # STEP 1: GENERATE CANDIDATES
        # -----------------------------------------------------

        generator = self._create_candidate_generator(
            self.simulator
        )

        candidates = generator.generate_actions()

        if not candidates:

            return {
                "best_action": None,
                "evaluations": [],
                "reason": (
                    "No eligible candidate actions."
                ),
            }

        # -----------------------------------------------------
        # STEP 2: SAFETY FILTER
        # -----------------------------------------------------

        action_filter = self._create_action_filter(
            self.simulator
        )

        safe_actions, unsafe_actions = (
            action_filter.filter_actions(
                candidates
            )
        )

        if not safe_actions:

            return {
                "best_action": None,
                "evaluations": [],
                "unsafe_actions": unsafe_actions,
                "reason": (
                    "No safe candidate actions."
                ),
            }

        # -----------------------------------------------------
        # STEP 3: EVALUATE SAFE ACTIONS
        # -----------------------------------------------------

        evaluations = []

        for action in safe_actions:

            result = self.evaluate_action(
                action
            )

            evaluations.append(result)

        # -----------------------------------------------------
        # STEP 4: SELECT BEST
        # -----------------------------------------------------

        best = max(
            evaluations,
            key=lambda x: x["score"]
        )

        return {
            "best_action": best,
            "evaluations": evaluations,
            "unsafe_actions": unsafe_actions,
            "reason": (
                "Best safe action selected "
                "using simulation-based evaluation."
            ),
        }


# -------------------------------------------------------------
# TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    from simulation.network import RailwayNetwork
    from input.input_state import TrainDatabase
    from input.scenario_loader import load_scenario

    print("=== Train Traffic Optimizer Test ===")

    # ---------------------------------------------------------
    # LOAD SYSTEM
    # ---------------------------------------------------------

    network = RailwayNetwork()

    database = TrainDatabase()

    scenario, traffic = load_scenario(
        "example_scenario.json",
        database
    )

    simulator = RailwaySimulator(
        network
    )

    simulator.load_traffic(
        traffic,
        database
    )

    # ---------------------------------------------------------
    # MOVE TO t = 2
    # ---------------------------------------------------------

    simulator.advance_time(2)

    print(
        "\nCurrent simulation time:",
        simulator.current_time_min,
        "minutes"
    )

    # ---------------------------------------------------------
    # CREATE OPTIMIZER
    # ---------------------------------------------------------

    optimizer = TrainTrafficOptimizer(
        simulator=simulator,
        train_database=database,
        evaluation_horizon_min=240.0,
    )

    # ---------------------------------------------------------
    # FIND BEST ACTION
    # ---------------------------------------------------------

    result = optimizer.find_best_action()

    print("\n=== ACTION EVALUATIONS ===")

    for evaluation in result[
        "evaluations"
    ]:

        print(
            "\nAction:",
            evaluation["action"],
            "| Train:",
            evaluation["train_id"],
            "| Section:",
            evaluation["section_id"],
        )

        print(
            "Score:",
            evaluation["score"]
        )

        if evaluation["metrics"] is not None:

            print(
                "Throughput:",
                evaluation["metrics"][
                    "throughput_trains_per_hour"
                ]
            )

            print(
                "Waiting:",
                evaluation["metrics"][
                    "total_waiting_time_min"
                ]
            )

            print(
                "Conflicts:",
                evaluation["metrics"][
                    "conflicts"
                ]
            )

    # ---------------------------------------------------------
    # BEST ACTION
    # ---------------------------------------------------------

    print("\n=== BEST ACTION ===")

    print(
        result["best_action"]
    )
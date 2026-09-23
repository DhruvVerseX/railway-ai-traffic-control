import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.train_movement import TrainMovementModel
from simulation.conflict_detector import ConflictDetector
from input.input_state import TrainDatabase
from input.scenario_loader import load_scenario


class BaselineController:
    """
    Conventional rule-based traffic controller.

    The controller:
    1. Finds waiting trains.
    2. Prioritizes trains using their priority value.
    3. Checks the next section.
    4. Reserves a section when a train is released.
    5. Holds later trains if that section is already reserved.
    6. Executes RELEASE decisions through the simulator.
    """

    def __init__(
        self,
        network: RailwayNetwork,
        simulator: RailwaySimulator,
        conflict_detector: ConflictDetector,
        train_database: TrainDatabase,
    ):
        self.network = network
        self.simulator = simulator
        self.conflict_detector = conflict_detector
        self.train_database = train_database

        self.decision_history = []

        # section_id -> train_id
        self.reserved_sections = {}

    def get_waiting_trains(self):
        """Return trains currently waiting to be released."""

        waiting_trains = []

        for train in self.simulator.trains.values():

            if train.status in (
                "WAITING",
                "NOT_ENTERED",
            ):
                waiting_trains.append(train)

        return waiting_trains

    def get_next_section(self, train_id: str):
        """Return the next section a train wants to enter."""

        movement = (
            self.simulator.movement_model.build_movement(
                train_id
            )
        )

        train = self.simulator.get_train_state(
            train_id
        )

        if train.section_index >= len(
            movement.section_sequence
        ):
            return None

        return movement.section_sequence[
            train.section_index
        ]

    def get_train_priority(self, train_id: str):
        """Return the priority of a train."""

        train_data = self.train_database.get_train(
            train_id
        )

        return int(train_data["priority"])

    def make_decision(self, train_id: str):
        """
        Decide whether a waiting train should be released.

        A section reserved earlier in the same control cycle
        is treated as unavailable.
        """

        next_section = self.get_next_section(
            train_id
        )

        # -----------------------------------------------
        # NO REMAINING SECTION
        # -----------------------------------------------

        if next_section is None:

            decision = {
                "train_id": train_id,
                "action": "NO_ACTION",
                "section_id": None,
                "conflict": False,
                "reason": "No remaining section.",
                "required_wait_min": 0.0,
            }

            self.decision_history.append(
                decision
            )

            return decision

        # -----------------------------------------------
        # CHECK CONTROLLER RESERVATION
        # -----------------------------------------------

        reserved_by = self.reserved_sections.get(
            next_section
        )

        if (
            reserved_by is not None
            and reserved_by != train_id
        ):

            decision = {
                "train_id": train_id,
                "action": "HOLD",
                "section_id": next_section,
                "conflict": True,
                "reason": (
                    f"Section {next_section} is already "
                    f"reserved by train {reserved_by}."
                ),
                "required_wait_min": None,
            }

            self.decision_history.append(
                decision
            )

            return decision

        # -----------------------------------------------
        # CHECK ACTUAL SECTION CONFLICT
        # -----------------------------------------------

        conflict_result = (
            self.conflict_detector.check_section_conflict(
                train_id=train_id,
                section_id=next_section,
            )
        )

        if conflict_result["conflict"]:

            decision = {
                "train_id": train_id,
                "action": "HOLD",
                "section_id": next_section,
                "conflict": True,
                "reason": conflict_result["reason"],
                "required_wait_min": (
                    conflict_result.get(
                        "required_wait_min"
                    )
                ),
            }

        else:

            # Reserve the section for this train.
            self.reserved_sections[
                next_section
            ] = train_id

            decision = {
                "train_id": train_id,
                "action": "RELEASE",
                "section_id": next_section,
                "conflict": False,
                "reason": (
                    "Section available. "
                    "Train may be released."
                ),
                "required_wait_min": 0.0,
            }

        self.decision_history.append(
            decision
        )

        return decision

    def execute_decision(self, decision):
        """
        Execute a controller decision.

        RELEASE:
            Start the train in the simulator.

        HOLD:
            Keep the train waiting.

        NO_ACTION:
            Do nothing.
        """

        train_id = decision["train_id"]

        if decision["action"] == "RELEASE":

            train = self.simulator.get_train_state(
                train_id
            )

            # A train cannot be released before its
            # scheduled entry time.
            if (
                self.simulator.current_time_min
                < train.entry_time_min
            ):
                return {
                    "executed": False,
                    "reason": (
                        "Train entry time has not "
                        "been reached."
                    ),
                }

            self.simulator.start_train(
                train_id
            )

            # Verify whether the train actually entered.
            updated_train = (
                self.simulator.get_train_state(
                    train_id
                )
            )

            if updated_train.status == "RUNNING":

                return {
                    "executed": True,
                    "reason": (
                        f"Train {train_id} "
                        f"entered section "
                        f"{updated_train.current_section}."
                    ),
                }

            return {
                "executed": False,
                "reason": (
                    "Simulator did not release "
                    "the train."
                ),
            }

        if decision["action"] == "HOLD":

            return {
                "executed": False,
                "reason": "Train remains on hold.",
            }

        return {
            "executed": False,
            "reason": "No action required.",
        }

    def control_waiting_trains(
        self,
        execute=True,
    ):
        """
        Evaluate all waiting trains.

        Higher-priority trains are evaluated first.

        If execute=True, RELEASE decisions are
        immediately passed to the simulator.
        """

        # Start a fresh decision cycle.
        self.reserved_sections = {}

        waiting_trains = (
            self.get_waiting_trains()
        )

        waiting_trains.sort(
            key=lambda train: self.get_train_priority(
                train.train_id
            ),
            reverse=True,
        )

        results = []

        for train in waiting_trains:

            decision = self.make_decision(
                train.train_id
            )

            execution = None

            if execute:
                execution = self.execute_decision(
                    decision
                )

            results.append(
                {
                    "decision": decision,
                    "execution": execution,
                }
            )

        return results


if __name__ == "__main__":

    print("=== Baseline Controller Test ===")

    # -----------------------------------------------
    # Load project components
    # -----------------------------------------------

    network = RailwayNetwork()

    train_database = TrainDatabase()

    movement_model = TrainMovementModel(
        network,
        train_database,
    )

    simulator = RailwaySimulator(
        network,
        movement_model,
    )

    # -----------------------------------------------
    # Load scenario
    # -----------------------------------------------

    scenario, traffic = load_scenario(
        "example_scenario.json",
        train_database,
    )

    simulator.load_traffic(
        traffic
    )

    # -----------------------------------------------
    # Create conflict detector
    # -----------------------------------------------

    conflict_detector = ConflictDetector(
        network,
        simulator,
    )

    # -----------------------------------------------
    # Create baseline controller
    # -----------------------------------------------

    controller = BaselineController(
        network=network,
        simulator=simulator,
        conflict_detector=conflict_detector,
        train_database=train_database,
    )

    # -----------------------------------------------
    # Start T008 manually so that the controller
    # has an occupied section to evaluate against.
    # -----------------------------------------------

    simulator.start_train(
        "T008"
    )

    # -----------------------------------------------
    # Advance simulation until waiting trains are
    # eligible for release.
    # -----------------------------------------------
    simulator.advance_time(2.0)
    # -----------------------------------------------
    # Evaluate and execute controller decisions
    # -----------------------------------------------

    results = controller.control_waiting_trains(
        execute=True
    )

    print("\n=== Controller Decisions ===")

    for result in results:

        decision = result["decision"]
        execution = result["execution"]

        print(
            f"Train: {decision['train_id']} | "
            f"Action: {decision['action']} | "
            f"Section: {decision['section_id']} | "
            f"Reason: {decision['reason']}"
        )

        if execution is not None:

            print(
                f"    Execution: "
                f"{execution['reason']}"
            )

    # -----------------------------------------------
    # Show resulting train states
    # -----------------------------------------------

    print("\n=== Resulting Train States ===")

    for train in simulator.trains.values():

        print(
            f"{train.train_id}: "
            f"status={train.status}, "
            f"section={train.current_section}"
        )
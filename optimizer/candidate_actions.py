import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.simulator import RailwaySimulator
from simulation.train_movement import TrainMovementModel


class CandidateActionGenerator:

    def __init__(
        self,
        simulator: RailwaySimulator,
        train_database,
    ):

        self.simulator = simulator
        self.train_database = train_database

        self.movement_model = TrainMovementModel(
            simulator.network,
            train_database,
        )

    # ---------------------------------------------------------
    # GET ELIGIBLE TRAINS
    # ---------------------------------------------------------

    def get_eligible_trains(self):

        eligible = []

        for train in self.simulator.trains.values():

            # Only waiting trains can be considered
            if train.status != "WAITING":
                continue

            # Train must have reached its entry time
            if (
                self.simulator.current_time_min
                < train.entry_time_min
            ):
                continue

            eligible.append(train)

        return eligible

    # ---------------------------------------------------------
    # GET NEXT SECTION
    # ---------------------------------------------------------

    def get_next_section(self, train_id):

        train = self.simulator.get_train_state(
            train_id
        )

        movement = self.movement_model.build_movement(
            train_id
        )

        if train.section_index >= len(
            movement.section_sequence
        ):

            return None

        return movement.section_sequence[
            train.section_index
        ]

    # ---------------------------------------------------------
    # GENERATE ACTIONS
    # ---------------------------------------------------------

    def generate_actions(self):

        actions = []

        for train in self.simulator.trains.values():

            # Only waiting trains are candidates
            if train.status != "WAITING":
                continue

            # Train must be allowed to enter now
            if self.simulator.current_time_min < train.entry_time_min:
                continue

            train_id = train.train_id

            section_id = self.get_next_section(train_id)

            if section_id is None:
                continue

            train_data = self.train_database.get_train(train_id)

            priority = float(
                train_data["priority"]
            )

            # RELEASE action
            actions.append(
                {
                    "train_id": train_id,
                    "action": "RELEASE",
                    "section_id": section_id,
                    "priority": priority,
                }
            )

            # HOLD action
            actions.append(
                {
                    "train_id": train_id,
                    "action": "HOLD",
                    "section_id": section_id,
                    "priority": priority,
                }
            )

        return actions


# -------------------------------------------------------------
# TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    from simulation.network import RailwayNetwork
    from input.input_state import TrainDatabase
    from input.scenario_loader import load_scenario

    print("=== Candidate Action Generator Test ===")

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

    # ---------------------------------------------------------
    # ADVANCE TO t = 2
    # ---------------------------------------------------------

    print("\nCurrent time:", simulator.current_time_min)

    simulator.advance_time(2)

    print(
        "Current time after advance:",
        simulator.current_time_min
    )

    # ---------------------------------------------------------
    # GENERATE CANDIDATES
    # ---------------------------------------------------------

    generator = CandidateActionGenerator(
        simulator,
        database,
    )

    eligible = generator.get_eligible_trains()

    print("\n=== ELIGIBLE TRAINS ===")

    for train in eligible:

        print(
            train.train_id,
            "| entry =",
            train.entry_time_min,
            "| section =",
            generator.get_next_section(
                train.train_id
            )
        )

    actions = generator.generate_actions()

    print("\n=== CANDIDATE ACTIONS ===")

    for action in actions:

        print(action)
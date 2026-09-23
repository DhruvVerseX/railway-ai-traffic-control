import sys
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.train_movement import TrainMovementModel
from input.input_state import TrainDatabase


class ScenarioGenerator:
    """
    Generate simulated railway traffic scenarios.

    Scenarios are created using trains from the existing
    train database and their actual movement routes.
    """

    def __init__(
        self,
        train_database: TrainDatabase,
        network: RailwayNetwork,
    ):
        self.train_database = train_database
        self.network = network

        self.movement_model = TrainMovementModel(
            network,
            train_database,
        )

    def get_all_train_ids(self):
        """Return all train IDs available in the database."""

        return list(
            self.train_database.trains.keys()
        )

    def get_train_direction(
        self,
        train_id: str,
    ):
        """
        Determine train direction from its actual movement.

        The TrainMovementModel handles both:
        - normal route direction
        - reverse route direction
        """

        train = self.train_database.get_train(
            train_id
        )

        movement = self.movement_model.build_movement(
            train_id
        )

        entry_station = train["entry_station"]

        first_section_id = (
            movement.section_sequence[0]
        )

        first_section = self.network.get_section(
            first_section_id
        )

        # Train enters the first section from its
        # normal direction.
        if first_section.from_station == entry_station:
            return "UP"

        # Train enters the section from the opposite
        # direction.
        if first_section.to_station == entry_station:
            return "DOWN"

        raise ValueError(
            f"Unable to determine direction for "
            f"train {train_id}."
        )

    def generate_scenario(
        self,
        scenario_id: str,
        num_trains: int = 5,
        simulation_time_min: float = 120.0,
        seed: int | None = None,
    ):
        """
        Generate one traffic scenario.

        Parameters:
        scenario_id:
            Unique scenario identifier.

        num_trains:
            Number of trains included.

        simulation_time_min:
            Duration of the simulated scenario.

        seed:
            Random seed for reproducibility.
        """

        if num_trains <= 0:
            raise ValueError(
                "num_trains must be greater than zero."
            )

        if simulation_time_min <= 0:
            raise ValueError(
                "simulation_time_min must be greater "
                "than zero."
            )

        if seed is not None:
            random.seed(seed)

        all_train_ids = self.get_all_train_ids()

        if num_trains > len(all_train_ids):
            raise ValueError(
                "num_trains cannot exceed the number "
                "of trains in the database."
            )

        selected_train_ids = random.sample(
            all_train_ids,
            num_trains,
        )

        trains = []

        for train_id in selected_train_ids:

            train = self.train_database.get_train(
                train_id
            )

            entry_station = train["entry_station"]

            direction = self.get_train_direction(
                train_id
            )

            # Random initial delay.
            delay_min = round(
                random.uniform(0, 15),
                2,
            )

            trains.append(
                {
                    "train_id": train_id,
                    "location": entry_station,
                    "direction": direction,
                    "status": "WAITING",
                    "delay_min": delay_min,
                    "entry_time_min": delay_min,
                    "current_section": None,
                    "next_station": None,
                }
            )

        return {
            "scenario_id": scenario_id,
            "description": (
                f"Generated traffic scenario with "
                f"{num_trains} trains."
            ),
            "simulation_time_min": simulation_time_min,
            "trains": trains,
        }

    def save_scenario(
        self,
        scenario,
        filename: str,
    ):
        """Save a generated scenario as JSON."""

        scenario_dir = (
            PROJECT_ROOT / "scenarios"
        )

        scenario_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filepath = (
            scenario_dir / filename
        )

        with open(
            filepath,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                scenario,
                file,
                indent=4,
            )

        return filepath


if __name__ == "__main__":

    print("=== Scenario Generator Test ===")

    # -----------------------------------------------
    # Load project components
    # -----------------------------------------------

    network = RailwayNetwork()

    train_database = TrainDatabase()

    generator = ScenarioGenerator(
        train_database=train_database,
        network=network,
    )

    # -----------------------------------------------
    # Generate scenario
    # -----------------------------------------------

    scenario = generator.generate_scenario(
        scenario_id="GEN001",
        num_trains=5,
        simulation_time_min=120,
        seed=42,
    )

    # -----------------------------------------------
    # Save scenario
    # -----------------------------------------------

    filepath = generator.save_scenario(
        scenario,
        "generated_scenario.json",
    )

    # -----------------------------------------------
    # Display result
    # -----------------------------------------------

    print("\nGenerated scenario:")

    print(
        json.dumps(
            scenario,
            indent=4,
        )
    )

    print("\nSaved to:")
    print(filepath)
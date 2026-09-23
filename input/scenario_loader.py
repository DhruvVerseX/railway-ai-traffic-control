import json
import sys
from pathlib import Path


# Find the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


from input.input_state import (
    TrafficState,
    create_train_state,
    TrainDatabase,
)


# Find the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = PROJECT_ROOT / "scenarios"


def load_scenario(filename, database):
    """Load a JSON scenario and convert it into a TrafficState."""

    filepath = SCENARIO_DIR / filename

    with open(filepath, "r", encoding="utf-8") as file:
        scenario = json.load(file)

    traffic = TrafficState()

    for train_data in scenario["trains"]:

        train = create_train_state(
            train_id=train_data["train_id"],
            location=train_data["location"],
            direction=train_data["direction"],
            status=train_data["status"],
            delay_min=train_data["delay_min"],
            entry_time_min=train_data.get(
                "entry_time_min",
                train_data["delay_min"]
            ),
            current_section=train_data["current_section"],
            next_station=train_data["next_station"],
            database=database,
        )

        traffic.add_train(train)

    traffic.validate()

    return scenario, traffic


if __name__ == "__main__":

    print("=== Scenario Loader Test ===")

    database = TrainDatabase()

    scenario, traffic = load_scenario(
        "generated_scenario.json",
        database,
    )

    print(
        f"Scenario ID: "
        f"{scenario['scenario_id']}"
    )

    print(
        f"Description: "
        f"{scenario['description']}"
    )

    print(
        f"Simulation time: "
        f"{scenario['simulation_time_min']} min"
    )

    print(
        f"Active trains: "
        f"{len(traffic.trains)}"
    )

    print("\n--- Current Traffic ---")

    for train in traffic.trains:

        print(
            f"{train.train_id}: "
            f"{train.location} → "
            f"{train.next_station} | "
            f"{train.status} | "
            f"delay={train.delay_min} min | "
            f"entry_time={train.entry_time_min} min"
        )

    print("\nScenario: VALID")
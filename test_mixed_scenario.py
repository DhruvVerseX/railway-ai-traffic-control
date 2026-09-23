import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from input.scenario_loader import load_scenario


SCENARIO_PATH = (
    PROJECT_ROOT
    / "scenarios"
    / "generated_scenario.json"
)


print("=== MIXED TRAFFIC SCENARIO TEST ===")


# -------------------------------------------------
# LOAD PROJECT COMPONENTS
# -------------------------------------------------

network = RailwayNetwork()

train_database = TrainDatabase()

simulator = RailwaySimulator(
    network
)


# -------------------------------------------------
# LOAD EXISTING SCENARIO
# -------------------------------------------------

_, traffic_state = load_scenario(
    SCENARIO_PATH,
    train_database
)

simulator.load_traffic(
    traffic_state,
    train_database
)


print("\nInitial train states:")

for train in simulator.trains.values():

    print(
        train.train_id,
        "|",
        train.status,
        "|",
        train.current_station,
        "| entry:",
        train.entry_time_min
    )

# -------------------------------------------------
# MOVE TO DECISION TIME
# -------------------------------------------------

print(
    "\nAdvancing simulation to 5 minutes..."
)

simulator.advance_time(5.0)
# -------------------------------------------------
# START FIRST ELIGIBLE TRAIN
# -------------------------------------------------

eligible_train = None

for train in simulator.trains.values():

    if (
        train.status == "WAITING"
        and simulator.current_time_min
        >= train.entry_time_min
    ):

        eligible_train = train
        break


if eligible_train is None:

    print(
        "\nNo train is currently eligible to start."
    )

    sys.exit()


print(
    f"\nStarting train: "
    f"{eligible_train.train_id}"
)


started = simulator.start_train(
    eligible_train.train_id
)


print(
    "Start result:",
    started
)


# -------------------------------------------------
# ADVANCE SIMULATION
# -------------------------------------------------

print(
    "\nAdvancing simulation by 10 minutes..."
)

simulator.advance_time(
    10.0
)


# -------------------------------------------------
# DISPLAY SECTION OCCUPANCY
# -------------------------------------------------

print(
    "\n=== SECTION OCCUPANCY ==="
)

occupied_count = 0

for section_id in sorted(
    network.sections.keys()
):

    occupant = (
        simulator.get_section_occupant(
            section_id
        )
    )

    if occupant is not None:

        occupied_count += 1

        print(
            section_id,
            "→",
            occupant
        )


print(
    f"\nOccupied sections: "
    f"{occupied_count}"
)


# -------------------------------------------------
# DISPLAY TRAIN STATES
# -------------------------------------------------

print(
    "\n=== TRAIN STATES ==="
)

for train in simulator.trains.values():

    print(
        train.train_id,
        "|",
        train.status,
        "| section:",
        train.current_section,
        "| station:",
        train.current_station
    )
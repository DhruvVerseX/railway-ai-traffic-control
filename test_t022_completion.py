import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.train_movement import TrainMovementModel
from input.input_state import TrainDatabase
from input.scenario_loader import load_scenario


# -----------------------------
# Load system
# -----------------------------

network = RailwayNetwork()
database = TrainDatabase()

movement_model = TrainMovementModel(
    network,
    database
)

simulator = RailwaySimulator(
    network
)


# -----------------------------
# Load scenario
# -----------------------------

scenario_path = (
    PROJECT_ROOT /
    "scenarios" /
    "example_scenario.json"
)

_, traffic_state = load_scenario(
    scenario_path,
    database
)

simulator.load_traffic(
    traffic_state,
    database
)


# -----------------------------
# Release T022
# -----------------------------

simulator.advance_time(2)

print("=== BEFORE RELEASE ===")

train = simulator.get_train_state("T022")

print(
    "Time:",
    simulator.current_time_min
)

print(
    "Status:",
    train.status
)

print(
    "Station:",
    train.current_station
)

print(
    "Section:",
    train.current_section
)

print(
    "Next station:",
    train.next_station
)


print("\n=== RELEASING T022 ===")

result = simulator.start_train("T022")

print(
    "Release result:",
    result
)


# -----------------------------
# Track T022
# -----------------------------

print("\n=== T022 MOVEMENT ===")

for i in range(12):

    simulator.advance_time(20)

    train = simulator.get_train_state("T022")

    print(
        f"Time: {simulator.current_time_min:.1f} | "
        f"Status: {train.status} | "
        f"Station: {train.current_station} | "
        f"Section: {train.current_section} | "
        f"Next: {train.next_station} | "
        f"Section index: {train.section_index}"
    )

    if train.status == "ARRIVED":
        break


# -----------------------------
# Event history
# -----------------------------

print("\n=== T022 EVENTS ===")

for event in simulator.history:

    if event.get("train_id") == "T022":

        print(event)
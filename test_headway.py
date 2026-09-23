import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from input.input_state import TrainDatabase, TrainState, TrafficState
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector


# ============================================================
# SETUP
# ============================================================

network = RailwayNetwork()
database = TrainDatabase()

traffic_state = TrafficState(
    trains=[
        TrainState(
            train_id="T001",
            location="PWL",
            direction="UP",
            status="WAITING",
            delay_min=0.0,
            entry_time_min=0.0,
            current_section="S03",
            next_station="MTJ"
        ),
        TrainState(
            train_id="T004",
            location="MTJ",
            direction="DOWN",
            status="WAITING",
            delay_min=0.0,
            entry_time_min=0.0,
            current_section="S03",
            next_station="PWL"
        )
    ]
)

simulator = RailwaySimulator(network)

# Create ONE persistent conflict detector.
conflict_detector = ConflictDetector(simulator)

simulator.load_traffic(
    traffic_state,
    database
)


# ============================================================
# START T001 ON S03
# ============================================================

print("\n=== STARTING T001 ===")

started = simulator.start_train("T001")

print("T001 started:", started)
print("Current time:", simulator.current_time_min)

if not started:
    raise RuntimeError("T001 could not be started.")


# ============================================================
# ADVANCE UNTIL T001 LEAVES S03
# ============================================================

print("\n=== ADVANCING UNTIL T001 LEAVES S03 ===")

while simulator.get_train_state("T001").status == "RUNNING":
    simulator.advance_time(1.0)

print("Current time:", simulator.current_time_min)
print("T001 state:", simulator.get_train_state("T001"))


# ============================================================
# CHECK HEADWAY
# ============================================================

print("\n=== CHECKING T004 HEADWAY ===")

conflict = conflict_detector.check_section_conflict(
    "T004",
    "S03"
)

print("Conflict result:")
print(conflict)


# ============================================================
# FINAL CONFLICT EVENTS
# ============================================================

print("\n=== CONFLICT EVENTS ===")

for event in simulator.history:

    if event["event"] == "CONFLICT_DETECTED":
        print(event)
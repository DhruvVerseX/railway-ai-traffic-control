import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from input.input_state import TrafficState, TrainState
from simulation.conflict_detector import ConflictDetector
from optimizer.optimizer import TrainTrafficOptimizer


# ---------------------------------------------------------
# SETUP
# ---------------------------------------------------------

network = RailwayNetwork()
database = TrainDatabase()
simulator = RailwaySimulator(network)

traffic_state = TrafficState(
    trains=[
        TrainState(
            train_id="T001",
            location="PWL",
            direction="UP",
            status="WAITING",
            delay_min=0,
            entry_time_min=0,
            current_section="S03",
            next_station="MTJ",
        ),

        TrainState(
            train_id="T004",
            location="MTJ",
            direction="DOWN",
            status="WAITING",
            delay_min=0,
            entry_time_min=0,
            current_section="S03",
            next_station="PWL",
        ),
    ]
)

simulator.load_traffic(
    traffic_state,
    database
)


# ---------------------------------------------------------
# RELEASE T001
# ---------------------------------------------------------

simulator.start_train("T001")


# ---------------------------------------------------------
# CHECK CONFLICT ONCE
# ---------------------------------------------------------

conflict_detector = ConflictDetector(simulator)

conflict_detector.check_section_conflict(
    "T004",
    "S03"
)


# ---------------------------------------------------------
# RUN OPTIMIZER
# ---------------------------------------------------------

optimizer = TrainTrafficOptimizer(
    simulator=simulator,
    train_database=database,
    evaluation_horizon_min=240.0,
)

result = optimizer.find_best_action()


# ---------------------------------------------------------
# PRINT ALL CONFLICT EVENTS
# ---------------------------------------------------------

print("\n=== ALL CONFLICT EVENTS ===")

conflict_events = [
    event
    for event in simulator.history
    if event["event"] == "CONFLICT_DETECTED"
]

for event in conflict_events:
    print(event)


# ---------------------------------------------------------
# PRINT ALL EVENTS
# ---------------------------------------------------------

print("\n=== COMPLETE EVENT HISTORY ===")

for event in simulator.history:
    print(event)


# ---------------------------------------------------------
# PRINT METRICS
# ---------------------------------------------------------

print("\n=== FINAL METRICS ===")

metrics = result["best_action"]["metrics"]

print(
    "Conflicts:",
    metrics["conflicts"]
)

print(
    "Waiting:",
    metrics["total_waiting_time_min"]
)

print(
    "Completed:",
    metrics["completed_trains"]
)
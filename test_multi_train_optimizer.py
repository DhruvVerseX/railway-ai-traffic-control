import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from input.input_state import TrafficState, TrainState
from optimizer.optimizer import TrainTrafficOptimizer


# ---------------------------------------------------------
# LOAD SYSTEM
# ---------------------------------------------------------

network = RailwayNetwork()
database = TrainDatabase()

simulator = RailwaySimulator(
    network
)


# ---------------------------------------------------------
# CREATE MULTI-TRAIN SCENARIO
# ---------------------------------------------------------

traffic_state = TrafficState(
    trains=[

        # High-priority passenger train
        TrainState(
            train_id="T022",
            location="BTE",
            direction="DOWN",
            status="WAITING",
            delay_min=2,
            entry_time_min=2,
            current_section=None,
            next_station="BXN",
        ),

        # Freight train
        TrainState(
            train_id="T029",
            location="BTE",
            direction="DOWN",
            status="WAITING",
            delay_min=12,
            entry_time_min=12,
            current_section=None,
            next_station="BXN",
        ),
    ]
)


# ---------------------------------------------------------
# LOAD TRAFFIC
# ---------------------------------------------------------

simulator.load_traffic(
    traffic_state,
    database
)


# ---------------------------------------------------------
# MOVE TO TIME = 12
# ---------------------------------------------------------

simulator.advance_time(12)


print("=== MULTI-TRAIN OPTIMIZER TEST ===")

print(
    "\nCurrent simulation time:",
    simulator.current_time_min,
    "minutes"
)


# ---------------------------------------------------------
# SHOW CURRENT TRAINS
# ---------------------------------------------------------

print("\n=== CURRENT TRAINS ===")

for train_id, train in simulator.trains.items():

    print(
        f"Train: {train_id} | "
        f"Status: {train.status} | "
        f"Station: {train.current_station} | "
        f"Entry: {train.entry_time_min}"
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


# ---------------------------------------------------------
# SHOW EVALUATIONS
# ---------------------------------------------------------

print("\n=== ACTION EVALUATIONS ===")

for evaluation in result["evaluations"]:

    print(
        f"\nTrain: {evaluation['train_id']}"
    )

    print(
        f"Action: {evaluation['action']}"
    )

    print(
        f"Section: {evaluation['section_id']}"
    )

    print(
        f"Score: {evaluation['score']}"
    )

    print(
        f"Throughput: "
        f"{evaluation['metrics']['throughput_trains_per_hour']}"
    )

    print(
        f"Waiting: "
        f"{evaluation['metrics']['total_waiting_time_min']}"
    )

    print(
        f"Conflicts: "
        f"{evaluation['metrics']['conflicts']}"
    )


# ---------------------------------------------------------
# SHOW UNSAFE ACTIONS
# ---------------------------------------------------------

print("\n=== UNSAFE ACTIONS ===")

for action in result["unsafe_actions"]:

    print(
        action
    )


# ---------------------------------------------------------
# BEST ACTION
# ---------------------------------------------------------

print("\n=== BEST ACTION ===")

print(
    result["best_action"]
)

print(
    "\nBest score:",
    result.get("best_score")
)
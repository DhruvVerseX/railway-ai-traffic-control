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
# LOAD SYSTEM
# ---------------------------------------------------------

network = RailwayNetwork()
database = TrainDatabase()

simulator = RailwaySimulator(
    network
)


# ---------------------------------------------------------
# CREATE CONFLICT SCENARIO
# ---------------------------------------------------------

traffic_state = TrafficState(
    trains=[

        # Train approaching S04 from BTE toward MTJ
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

        # Another train also attempting the same section S04
        # from the opposite direction.
        TrainState(
            train_id="T004",
            location="MTJ",
            direction="UP",
            status="WAITING",
            delay_min=5,
            entry_time_min=5,
            current_section=None,
            next_station="BTE",
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
# MOVE TO TIME = 5
# ---------------------------------------------------------

simulator.advance_time(5)


print("=== CONFLICT OPTIMIZER TEST ===")

print(
    "\nCurrent simulation time:",
    simulator.current_time_min,
    "minutes"
)


# ---------------------------------------------------------
# CURRENT TRAIN STATES
# ---------------------------------------------------------

print("\n=== CURRENT TRAINS ===")

for train_id, train in simulator.trains.items():

    print(
        f"Train: {train_id} | "
        f"Status: {train.status} | "
        f"Station: {train.current_station} | "
        f"Direction: {train.direction} | "
        f"Entry: {train.entry_time_min}"
    )


# ---------------------------------------------------------
# CHECK THEIR NEXT SECTIONS
# ---------------------------------------------------------

print("\n=== NEXT SECTIONS ===")

for train_id in simulator.trains:

    train = simulator.get_train_state(
        train_id
    )

    movement = simulator.movement_model.build_movement(
        train_id
    )

    section_id = movement.section_sequence[
        train.section_index
    ]

    print(
        f"{train_id} → {section_id}"
    )


# ---------------------------------------------------------
# DIRECT CONFLICT CHECK
# ---------------------------------------------------------

conflict_detector = ConflictDetector(
    simulator
)

print("\n=== CONFLICT CHECK ===")

for train_id in simulator.trains:

    train = simulator.get_train_state(
        train_id
    )

    movement = simulator.movement_model.build_movement(
        train_id
    )

    section_id = movement.section_sequence[
        train.section_index
    ]

    result = conflict_detector.check_section_conflict(
        train_id,
        section_id
    )

    print(
        f"{train_id} → {section_id} | "
        f"Conflict: {result['conflict']} | "
        f"Reason: {result['reason']}"
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
# SHOW ACTIONS
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
# UNSAFE ACTIONS
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
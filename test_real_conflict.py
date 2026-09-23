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

simulator = RailwaySimulator(network)


# ---------------------------------------------------------
# CREATE TWO TRAINS AT OPPOSITE ENDS OF S03
# ---------------------------------------------------------

traffic_state = TrafficState(
    trains=[

        # T001 will wait at PWL and enter S03 toward MTJ
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

        # T004 will wait at MTJ and enter S03 toward PWL
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


# ---------------------------------------------------------
# LOAD TRAFFIC
# ---------------------------------------------------------

simulator.load_traffic(
    traffic_state,
    database
)

print("=== REAL S03 CONFLICT TEST ===")

print(
    "\nCurrent simulation time:",
    simulator.current_time_min,
    "minutes"
)


# ---------------------------------------------------------
# VERIFY BOTH TRAINS TARGET S03
# ---------------------------------------------------------

print("\n=== NEXT SECTIONS ===")

for train_id in simulator.trains:

    train = simulator.get_train_state(train_id)

    movement = simulator.movement_model.build_movement(
        train_id
    )

    section_id = movement.section_sequence[
        train.section_index
    ]

    print(
        f"{train_id} | "
        f"Location: {train.current_station} | "
        f"Direction: {train.direction} | "
        f"Next section: {section_id}"
    )


# ---------------------------------------------------------
# RELEASE T001 FIRST
# ---------------------------------------------------------

print("\n=== RELEASE T001 FIRST ===")

result = simulator.start_train("T001")

print(result)

print(
    "\nS03 occupant:",
    simulator.get_section_occupant("S03")
)


# ---------------------------------------------------------
# CHECK T004'S CONFLICT
# ---------------------------------------------------------

print("\n=== T004 CONFLICT CHECK ===")

from simulation.conflict_detector import ConflictDetector

conflict_detector = ConflictDetector(simulator)

conflict = conflict_detector.check_section_conflict(
    "T004",
    "S03"
)

print(conflict)


# ---------------------------------------------------------
# RUN OPTIMIZER
# ---------------------------------------------------------

print("\n=== OPTIMIZER ===")

optimizer = TrainTrafficOptimizer(
    simulator=simulator,
    train_database=database,
    evaluation_horizon_min=240.0,
)

result = optimizer.find_best_action()


# ---------------------------------------------------------
# PRINT SAFE ACTIONS
# ---------------------------------------------------------

print("\n=== SAFE ACTION EVALUATIONS ===")

for evaluation in result["evaluations"]:

    print(
        f"Train: {evaluation['train_id']} | "
        f"Action: {evaluation['action']} | "
        f"Section: {evaluation['section_id']} | "
        f"Score: {evaluation['score']}"
    )


# ---------------------------------------------------------
# PRINT UNSAFE ACTIONS
# ---------------------------------------------------------

print("\n=== UNSAFE ACTIONS ===")

for action in result["unsafe_actions"]:
    print(action)


# ---------------------------------------------------------
# BEST ACTION
# ---------------------------------------------------------

print("\n=== BEST ACTION ===")

print(result["best_action"])
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
# SETUP
# ---------------------------------------------------------

network = RailwayNetwork()
database = TrainDatabase()
simulator = RailwaySimulator(network)


# ---------------------------------------------------------
# TWO TRAINS WAITING FOR DIFFERENT SECTIONS
# ---------------------------------------------------------
#
# T001 = priority 5
# T029 = priority 1
#
# Both are available at time 0.
# Their actions are safe and operationally comparable.
#

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
            train_id="T029",
            location="NZM",
            direction="UP",
            status="WAITING",
            delay_min=0,
            entry_time_min=0,
            current_section="S02",
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


# ---------------------------------------------------------
# OPTIMIZER
# ---------------------------------------------------------

optimizer = TrainTrafficOptimizer(
    simulator=simulator,
    train_database=database,
    evaluation_horizon_min=240.0,
)


result = optimizer.find_best_action()


# ---------------------------------------------------------
# PRINT TRAIN PRIORITIES
# ---------------------------------------------------------

print("=== PRIORITY OPTIMIZER TEST ===")

print("\n=== TRAIN PRIORITIES ===")

for train_id in ["T001", "T029"]:

    train = database.get_train(train_id)

    print(
        f"{train_id} | "
        f"Priority: {train['priority']}"
    )


# ---------------------------------------------------------
# PRINT ALL EVALUATIONS
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
        f"Priority: {evaluation.get('priority', 'N/A')}"
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
# BEST ACTION
# ---------------------------------------------------------

print("\n=== BEST ACTION ===")

print(
    result["best_action"]
)
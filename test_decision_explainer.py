import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from input.input_state import TrafficState, TrainState
from optimizer.optimizer import TrainTrafficOptimizer
from optimizer.decision_explainer import DecisionExplainer


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


simulator.load_traffic(
    traffic_state,
    database
)


# ---------------------------------------------------------
# OPTIMIZE
# ---------------------------------------------------------

optimizer = TrainTrafficOptimizer(
    simulator=simulator,
    train_database=database,
    evaluation_horizon_min=240.0,
)

result = optimizer.find_best_action()


# ---------------------------------------------------------
# EXPLAIN
# ---------------------------------------------------------

explainer = DecisionExplainer()

explanation = explainer.explain(
    result["best_action"],
    result["evaluations"]
)


print("=== DECISION EXPLANATION ===")
print()
print(explanation)
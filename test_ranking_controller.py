from railway_ai.simulation.network import RailwayNetwork
from railway_ai.input.input_state import TrainDatabase
from railway_ai.simulation.simulator import RailwaySimulator

from railway_ai.scenarios.mixed_scenario_builder import (
    MixedScenarioBuilder
)

from railway_ai.controller.ranking_controller import (
    RankingTrainController
)


# ============================================================
# SETUP
# ============================================================

print("\n==========================================")
print("RANKING CONTROLLER INTEGRATION TEST")
print("==========================================")


# ============================================================
# LOAD NETWORK + DATABASE
# ============================================================

network = RailwayNetwork()

train_database = TrainDatabase()


print("\nNetwork loaded.")

print(
    "Train database loaded."
)


# ============================================================
# CREATE SCENARIO BUILDER
# ============================================================

builder = MixedScenarioBuilder(
    network,
    train_database
)


# ============================================================
# CREATE COMPETITION SCENARIO
# ============================================================

traffic_state = (
    builder.generate_mixed_scenario(
        scenario_id="RANK_TEST",
        num_trains=6,
        scenario_type="competition",
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=42
    )
)


print(
    "\nScenario created."
)


print(
    "Trains:",
    len(traffic_state.trains)
)


# ============================================================
# SHOW SCENARIO
# ============================================================

print(
    "\n=== SCENARIO TRAINS ==="
)


for train in traffic_state.trains:

    print(
        train.train_id,
        "|",
        train.status,
        "|",
        "station:",
        train.location,
        "|",
        "section:",
        train.current_section,
        "|",
        "next:",
        train.next_station,
        "|",
        "delay:",
        train.delay_min
    )


# ============================================================
# CREATE SIMULATOR
# ============================================================

simulator = RailwaySimulator(
    network
)


simulator.load_traffic(
    traffic_state,
    train_database
)

# Advance to a decision point where all scenario
# trains have reached their entry time.
simulator.advance_time(15.0)

print(
    f"Current simulation time: "
    f"{simulator.current_time_min} minutes"
)


print(
    "\nSimulator loaded."
)


print(
    "Current simulation time:",
    simulator.current_time_min,
    "minutes"
)


# ============================================================
# CREATE RANKING CONTROLLER
# ============================================================

controller = RankingTrainController(
    network,
    train_database
)


print(
    "Ranking controller loaded."
)


# ============================================================
# GET SAFE CANDIDATES
# ============================================================

candidates = (
    controller.get_safe_candidates(
        simulator
    )
)


print(
    "\n=== SAFE RELEASE CANDIDATES ==="
)


print(
    "Number of safe candidates:",
    len(candidates)
)


for candidate in candidates:

    print(
        candidate["train_id"],
        "|",
        "P(RELEASE):",
        round(
            candidate.get(
                "probability_release",
                0.0
            ),
            4
        ),
        "|",
        "Section:",
        candidate.get(
            "next_section"
        )
    )


# ============================================================
# RANK CANDIDATES
# ============================================================

ranked = (
    controller.rank_candidates(
        simulator,
        candidates
    )
)


print(
    "\n=== RANKED CANDIDATES ==="
)


for position, candidate in enumerate(
    ranked,
    start=1
):

    print(
        position,
        ".",
        candidate["train_id"],
        "|",
        "Ranking score:",
        round(
            candidate["ranking_score"],
            4
        ),
        "|",
        "P(RELEASE):",
        round(
            candidate.get(
                "probability_release",
                0.0
            ),
            4
        ),
        "|",
        "Section:",
        candidate.get(
            "next_section"
        )
    )


# ============================================================
# MAKE FINAL DECISION
# ============================================================

decision = (
    controller.make_decision(
        simulator
    )
)


print(
    "\n=== FINAL DECISION ==="
)


print(
    "Action:",
    decision["action"]
)


print(
    "Train:",
    decision["train_id"]
)


print(
    "Next section:",
    decision.get(
        "next_section"
    )
)


print(
    "Ranking score:",
    decision.get(
        "ranking_score"
    )
)


print(
    "Reason:",
    decision["reason"]
)


# ============================================================
# EXECUTE DECISION
# ============================================================

execution = (
    controller.execute_decision(
        simulator,
        decision
    )
)


print(
    "\n=== EXECUTION ==="
)


print(
    "Executed:",
    execution["executed"]
)


print(
    "Action:",
    execution["action"]
)


print(
    "Train:",
    execution["train_id"]
)


print(
    "Success:",
    execution.get(
        "success"
    )
)


print(
    "Reason:",
    execution["reason"]
)


# ============================================================
# FINAL TRAIN STATE
# ============================================================

if decision["train_id"] is not None:

    selected_train = simulator.trains[
        decision["train_id"]
    ]


    print(
        "\n=== SELECTED TRAIN STATE ==="
    )


    print(
        "Train:",
        selected_train.train_id
    )


    print(
        "Status:",
        selected_train.status
    )


    print(
        "Current section:",
        selected_train.current_section
    )


    print(
        "Next station:",
        selected_train.next_station
    )


# ============================================================
# COMPLETE
# ============================================================

print(
    "\n=========================================="
)


print(
    "RANKING CONTROLLER TEST COMPLETE"
)


print(
    "=========================================="
)
from pathlib import Path
import sys
import statistics

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from railway_ai.simulation.network import RailwayNetwork
from railway_ai.input.input_state import TrainDatabase
from railway_ai.simulation.simulator import RailwaySimulator

from railway_ai.scenarios.mixed_scenario_builder import (
    MixedScenarioBuilder
)

from railway_ai.controller.baseline_controller import (
    BaselineController
)

from railway_ai.controller.ai_controller import (
    AITrainTrafficController
)

from railway_ai.controller.ranking_controller import (
    RankingTrainController
)

from railway_ai.metrics.metrics import SimulationMetrics


SIMULATION_TIME = 240.0
NUM_SCENARIOS = 100


def run_baseline(
    network,
    train_database,
    traffic_state
):
    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    controller = BaselineController(
        network,
        simulator,
        None,
        train_database
    )

    # The baseline controller needs its own conflict detector.
    from railway_ai.simulation.conflict_detector import (
        ConflictDetector
    )

    conflict_detector = ConflictDetector(
        simulator
    )

    controller.conflict_detector = conflict_detector

    steps = int(SIMULATION_TIME / 5)

    for _ in range(steps):

        controller.control_waiting_trains(
            simulator
        )

        simulator.advance_time(5.0)

    return SimulationMetrics(
        simulator
    ).calculate_all()


def run_v2(
    network,
    train_database,
    traffic_state
):
    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    controller = AITrainTrafficController(
        network,
        train_database
    )

    steps = int(SIMULATION_TIME / 5)

    for _ in range(steps):

        controller.control_step(
            simulator
        )

        simulator.advance_time(5.0)

    return SimulationMetrics(
        simulator
    ).calculate_all()


def run_ranking(
    network,
    train_database,
    traffic_state
):
    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    controller = RankingTrainController(
        network,
        train_database
    )

    steps = int(SIMULATION_TIME / 5)

    for _ in range(steps):

        controller.control_step(
            simulator
        )

        simulator.advance_time(5.0)

    return SimulationMetrics(
        simulator
    ).calculate_all()


def print_controller_summary(
    name,
    results
):

    throughput = statistics.mean(
        r["throughput_trains_per_hour"]
        for r in results
    )

    completed = statistics.mean(
        r["completed_trains"]
        for r in results
    )

    waiting = statistics.mean(
        r["total_waiting_time_min"]
        for r in results
    )

    conflicts = statistics.mean(
        r["conflicts"]
        for r in results
    )

    print()
    print(name)
    print("-" * 40)
    print(
        f"Average throughput : "
        f"{throughput:.4f} trains/hour"
    )
    print(
        f"Average completed  : "
        f"{completed:.2f}"
    )
    print(
        f"Average waiting    : "
        f"{waiting:.2f} min"
    )
    print(
        f"Average conflicts  : "
        f"{conflicts:.2f}"
    )


def main():

    print("=" * 60)
    print("BASELINE vs V2 vs RANKING AI")
    print("=" * 60)

    network = RailwayNetwork()
    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        train_database
    )

    baseline_results = []
    v2_results = []
    ranking_results = []

    print(
        f"\nRunning {NUM_SCENARIOS} scenarios..."
    )

    for seed in range(NUM_SCENARIOS):

        traffic_state = (
            builder.generate_mixed_scenario(
                scenario_id=f"COMPARE_{seed}",
                num_trains=6,
                scenario_type="random",
                decision_time_min=5.0,
                running_advance_min=5.0,
                seed=seed
            )
        )

        # ----------------------------------------------------
        # Baseline
        # ----------------------------------------------------

        baseline = run_baseline(
            network,
            train_database,
            traffic_state
        )

        baseline_results.append(
            baseline
        )

        # ----------------------------------------------------
        # V2 AI
        # ----------------------------------------------------

        v2 = run_v2(
            network,
            train_database,
            traffic_state
        )

        v2_results.append(
            v2
        )

        # ----------------------------------------------------
        # Ranking AI
        # ----------------------------------------------------

        ranking = run_ranking(
            network,
            train_database,
            traffic_state
        )

        ranking_results.append(
            ranking
        )

        if (seed + 1) % 10 == 0:

            print(
                f"Completed "
                f"{seed + 1}/{NUM_SCENARIOS}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n")
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    print_controller_summary(
        "BASELINE CONTROLLER",
        baseline_results
    )

    print_controller_summary(
        "V2 AI CONTROLLER",
        v2_results
    )

    print_controller_summary(
        "RANKING AI CONTROLLER",
        ranking_results
    )

    # ========================================================
    # IMPROVEMENTS
    # ========================================================

    def avg(results, key):
        return statistics.mean(
            r[key] for r in results
        )

    b_tp = avg(
        baseline_results,
        "throughput_trains_per_hour"
    )

    v2_tp = avg(
        v2_results,
        "throughput_trains_per_hour"
    )

    rank_tp = avg(
        ranking_results,
        "throughput_trains_per_hour"
    )

    b_wait = avg(
        baseline_results,
        "total_waiting_time_min"
    )

    v2_wait = avg(
        v2_results,
        "total_waiting_time_min"
    )

    rank_wait = avg(
        ranking_results,
        "total_waiting_time_min"
    )

    b_conf = avg(
        baseline_results,
        "conflicts"
    )

    v2_conf = avg(
        v2_results,
        "conflicts"
    )

    rank_conf = avg(
        ranking_results,
        "conflicts"
    )

    print("\n")
    print("=" * 60)
    print("IMPROVEMENT OVER BASELINE")
    print("=" * 60)

    print(
        f"\nV2 AI throughput improvement: "
        f"{((v2_tp - b_tp) / b_tp) * 100:.2f}%"
    )

    print(
        f"Ranking AI throughput improvement: "
        f"{((rank_tp - b_tp) / b_tp) * 100:.2f}%"
    )

    print(
        f"\nV2 AI waiting reduction: "
        f"{((b_wait - v2_wait) / b_wait) * 100:.2f}%"
    )

    print(
        f"Ranking AI waiting reduction: "
        f"{((b_wait - rank_wait) / b_wait) * 100:.2f}%"
    )

    print(
        f"\nV2 AI conflict reduction: "
        f"{((b_conf - v2_conf) / b_conf) * 100:.2f}%"
    )

    print(
        f"Ranking AI conflict reduction: "
        f"{((b_conf - rank_conf) / b_conf) * 100:.2f}%"
    )

    # ========================================================
    # RANKING AI vs V2
    # ========================================================

    print("\n")
    print("=" * 60)
    print("RANKING AI vs V2 AI")
    print("=" * 60)

    print(
        f"\nThroughput change: "
        f"{((rank_tp - v2_tp) / v2_tp) * 100:.2f}%"
    )

    print(
        f"Waiting change: "
        f"{((rank_wait - v2_wait) / v2_wait) * 100:.2f}%"
    )

    print(
        f"Conflict change: "
        f"{((rank_conf - v2_conf) / v2_conf) * 100:.2f}%"
    )

    print("\n")
    print("=" * 60)
    print("THREE-WAY COMPARISON COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
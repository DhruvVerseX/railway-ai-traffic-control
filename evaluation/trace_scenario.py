import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from input.input_state import TrainDatabase
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector
from controller.baseline_controller import BaselineController
from controller.ai_controller import AITrainTrafficController


def print_traffic_state(traffic_state):
    print()
    print("=" * 90)
    print("SCENARIO TRAFFIC STATE")
    print("=" * 90)

    for train in traffic_state.trains:
        print(
            f"{train.train_id:5} | "
            f"location={train.location:5} | "
            f"direction={train.direction:4} | "
            f"status={train.status:10} | "
            f"delay={train.delay_min:6.2f} | "
            f"entry={train.entry_time_min:6.2f}"
        )


def trace_baseline(traffic_state):
    print()
    print("=" * 90)
    print("BASELINE CONTROLLER TRACE")
    print("=" * 90)

    network = RailwayNetwork()
    train_database = TrainDatabase()
    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    conflict_detector = ConflictDetector(simulator)

    controller = BaselineController(
        network=network,
        simulator=simulator,
        conflict_detector=conflict_detector,
        train_database=train_database
    )

    while simulator.current_time_min < 240.0:

        results = controller.control_waiting_trains(
            execute=True
        )

        for result in results:

            decision = result["decision"]
            execution = result["execution"]

            print(
                f"t={simulator.current_time_min:6.1f} | "
                f"train={decision['train_id']:5} | "
                f"action={decision['action']:7} | "
                f"section={str(decision.get('section_id')):4} | "
                f"priority={decision.get('priority')} | "
                f"executed="
                f"{execution.get('executed') if execution else None}"
            )

        remaining = 240.0 - simulator.current_time_min

        simulator.advance_time(
            min(5.0, remaining)
        )

    print()
    print("BASELINE FINAL STATES")

    for train_id, train in simulator.trains.items():

        print(
            f"{train_id:5} | "
            f"status={train.status:10} | "
            f"section={str(train.current_section):4} | "
            f"station={train.current_station:5} | "
            f"section_index={train.section_index}"
        )


def trace_ai(traffic_state):
    print()
    print("=" * 90)
    print("AI CONTROLLER TRACE")
    print("=" * 90)

    network = RailwayNetwork()
    train_database = TrainDatabase()
    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    controller = AITrainTrafficController(
        network=network,
        train_database=train_database
    )

    while simulator.current_time_min < 240.0:

        decision = controller.control_step(simulator)

        recommendations = decision["recommendations"]
        selected = decision["selected_action"]

        print()
        print(f"TIME = {simulator.current_time_min:.1f} min")

        print("-" * 90)
        print("ALL AI RECOMMENDATIONS")

        if not recommendations:
            print("No eligible trains.")

        for result in recommendations:

            probabilities = result.get(
                "probabilities",
                {}
            )

            print(
                f"train={result['train_id']:5} | "
                f"section={str(result.get('next_section')):4} | "
                f"ML={result.get('ml_action'):7} | "
                f"final={result.get('final_action'):7} | "
                f"safe={result.get('safe')} | "
                f"RELEASE_prob="
                f"{probabilities.get('RELEASE', 0.0):.4f} | "
                f"HOLD_prob="
                f"{probabilities.get('HOLD', 0.0):.4f} | "
                f"reason={result.get('reason')}"
            )

        print("-" * 90)

        if selected is None:

            print("SELECTED: None")

        else:

            probabilities = selected.get(
                "probabilities",
                {}
            )

            print(
                f"SELECTED → "
                f"train={selected['train_id']} | "
                f"section={selected.get('next_section')} | "
                f"ML={selected.get('ml_action')} | "
                f"FINAL={selected.get('final_action')} | "
                f"safe={selected.get('safe')} | "
                f"RELEASE_prob="
                f"{probabilities.get('RELEASE', 0.0):.4f}"
            )

            execution = decision.get("execution")

            print(
                f"EXECUTION → {execution}"
            )

        remaining = 240.0 - simulator.current_time_min

        simulator.advance_time(
            min(5.0, remaining)
        )

    print()
    print("AI FINAL STATES")

    for train_id, train in simulator.trains.items():

        print(
            f"{train_id:5} | "
            f"status={train.status:10} | "
            f"section={str(train.current_section):4} | "
            f"station={train.current_station:5} | "
            f"section_index={train.section_index}"
        )

def main():

    print("=" * 90)
    print("SCENARIO 66 TRACE")
    print("=" * 90)

    network = RailwayNetwork()
    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network=network,
        train_database=train_database
    )

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="TRACE66",
        num_trains=6,
        scenario_type="competition",
        seed=66
    )

    print_traffic_state(traffic_state)

    trace_baseline(traffic_state)
    trace_ai(traffic_state)

    print()
    print("=" * 90)
    print("TRACE COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
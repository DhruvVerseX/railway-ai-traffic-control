from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector
from controller.baseline_controller import BaselineController
from input.input_state import TrainDatabase
from input.scenario_loader import load_scenario


print("=== Event Tracking + Controller Test ===")


# ---------------------------------------------------------
# LOAD SYSTEM
# ---------------------------------------------------------

network = RailwayNetwork()
database = TrainDatabase()

scenario, traffic = load_scenario(
    "example_scenario.json",
    database
)

simulator = RailwaySimulator(network)

simulator.load_traffic(
    traffic,
    database
)

conflict_detector = ConflictDetector(simulator)

controller = BaselineController(
    network=network,
    simulator=simulator,
    conflict_detector=conflict_detector,
    train_database=database,
)


# ---------------------------------------------------------
# INITIAL STATE
# ---------------------------------------------------------

print("\nInitial state:")

for train in simulator.trains.values():

    print(
        train.train_id,
        "| status =", train.status,
        "| entry =", train.entry_time_min,
        "| section =", train.current_section
    )


# ---------------------------------------------------------
# MOVE TO t = 2
# ---------------------------------------------------------

print("\nAdvancing simulation to t = 2 minutes...")

simulator.advance_time(2)

print("\nState at t =", simulator.current_time_min)

for train in simulator.trains.values():

    print(
        train.train_id,
        "| status =", train.status
    )


# ---------------------------------------------------------
# BASELINE CONTROLLER
# ---------------------------------------------------------

print("\nRunning baseline controller...")

decisions = controller.control_waiting_trains(
    execute=True
)

for result in decisions:

    print(result)


# ---------------------------------------------------------
# ADVANCE SIMULATION
# ---------------------------------------------------------

print("\nAdvancing simulation by 20 minutes...")

simulator.advance_time(20)


# ---------------------------------------------------------
# EVENT HISTORY
# ---------------------------------------------------------

print("\n=== EVENT HISTORY ===")

for event in simulator.history:

    print(
        f"t={event['time_min']:6.2f} | "
        f"{event['event']:20s} | "
        f"train={event['train_id']} | "
        f"section={event['section_id']} | "
        f"{event}"
    )


# ---------------------------------------------------------
# FINAL STATES
# ---------------------------------------------------------

print("\n=== FINAL TRAIN STATES ===")

for train in simulator.trains.values():

    print(
        train.train_id,
        "| status =", train.status,
        "| section =", train.current_section,
        "| station =", train.current_station
    )
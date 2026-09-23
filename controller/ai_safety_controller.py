import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from controller.ml_controller import MLTrainController
from simulation.conflict_detector import ConflictDetector


class AISafetyController:
    """
    Combines the ML controller with the deterministic
    railway safety/conflict layer.

    ML recommends an action.
    Safety rules determine whether RELEASE is allowed.
    """

    def __init__(self, network, train_database):
        self.network = network
        self.train_database = train_database

        self.ml_controller = MLTrainController(
            network,
            train_database
        )

        # Persistent conflict detector.
        # It keeps track of section exit times so that
        # headway constraints are preserved between
        # consecutive AI decisions.
        self._conflict_detector = None
        self._simulator = None

    # ========================================================
    # GET CONFLICT DETECTOR
    # ========================================================

    def _get_conflict_detector(self, simulator):
        """
        Return a persistent ConflictDetector for the
        current simulator.

        A new detector is created only when the controller
        is connected to a different simulator instance.
        """

        if (
            self._conflict_detector is None
            or self._simulator is not simulator
        ):

            self._conflict_detector = ConflictDetector(
                simulator
            )

            self._simulator = simulator

        return self._conflict_detector

    # ========================================================
    # DECIDE
    # ========================================================

    def decide(self, simulator, train_id):
        """
        Generate an ML recommendation and then validate it
        using the railway safety/conflict rules.
        """

        # ----------------------------------------------------
        # Get ML recommendation
        # ----------------------------------------------------

        ml_result = self.ml_controller.predict_train(
            simulator,
            train_id
        )

        ml_action = ml_result["action"]
        next_section = ml_result["next_section"]

        # ----------------------------------------------------
        # HOLD is always safe
        # ----------------------------------------------------

        if ml_action == "HOLD":

            return {
                "train_id": train_id,
                "ml_action": ml_action,
                "final_action": "HOLD",
                "next_section": next_section,
                "safe": True,
                "reason": "ML recommended HOLD.",
                "probabilities": ml_result["probabilities"]
            }

        # ----------------------------------------------------
        # RELEASE must pass safety checks
        # ----------------------------------------------------

        conflict_detector = self._get_conflict_detector(
            simulator
        )

        conflict = conflict_detector.check_section_conflict(
            train_id,
            next_section
        )

        if conflict["conflict"]:

            return {
                "train_id": train_id,
                "ml_action": ml_action,
                "final_action": "HOLD",
                "next_section": next_section,
                "safe": False,
                "reason": (
                    "ML recommended RELEASE, but the safety "
                    "layer detected a conflict."
                ),
                "conflict_reason": conflict["reason"],
                "conflicting_train_id": (
                    conflict.get("conflicting_train_id")
                ),
                "required_wait_min": (
                    conflict.get("required_wait_min", 0.0)
                ),
                "probabilities": ml_result["probabilities"]
            }

        # ----------------------------------------------------
        # RELEASE is safe
        # ----------------------------------------------------

        return {
            "train_id": train_id,
            "ml_action": ml_action,
            "final_action": "RELEASE",
            "next_section": next_section,
            "safe": True,
            "reason": (
                "ML recommended RELEASE and the safety "
                "layer found no conflict."
            ),
            "required_wait_min": 0.0,
            "probabilities": ml_result["probabilities"]
        }
import pickle
from pathlib import Path

import pandas as pd

from .ml_controller import MLTrainController
from .ai_controller import AISafetyController


class RankingTrainController:
    """
    Final AI candidate-selection controller.

    Pipeline:

        V2 ML classifier
                ↓
        Safety controller
                ↓
        Ranking Model
                ↓
        Best safe RELEASE
                ↓
        Simulator

    The optimizer is NOT used at runtime.
    It was used offline to create the training labels.
    """

    def __init__(
        self,
        network,
        train_database,
        model_path=None
    ):

        self.network = network
        self.train_database = train_database

        # ====================================================
        # V2 ML CLASSIFIER
        # ====================================================

        self.ml_controller = MLTrainController(
            network,
            train_database
        )

        # ====================================================
        # SAFETY CONTROLLER
        # ====================================================

        self.safety_controller = AISafetyController(
            network,
            train_database
        )

        # ====================================================
        # RANKING MODEL PATH
        # ====================================================

        if model_path is None:

            project_root = (
                Path(__file__)
                .resolve()
                .parent
                .parent
            )

            model_path = (
                project_root
                / "ml"
                / "models"
                / "action_ranking_model_v2.pkl"
            )

        self.model_path = Path(model_path)

        if not self.model_path.exists():

            raise FileNotFoundError(
                "Ranking model not found:\n"
                f"{self.model_path}"
            )

        # ====================================================
        # LOAD RANKING MODEL
        # ====================================================

        with open(self.model_path, "rb") as file:

            package = pickle.load(file)

        self.ranking_model = package["model"]
        self.preprocessor = package["preprocessor"]
        self.feature_columns = package["feature_columns"]
        self.categorical_features = package[
            "categorical_features"
        ]
        self.numeric_features = package[
            "numeric_features"
        ]

        self.target_type = package.get(
            "target_type",
            "unknown"
        )

    # ========================================================
    # GET ELIGIBLE TRAINS
    # ========================================================

    def get_eligible_trains(
        self,
        simulator
    ):

        eligible = []

        for train_id, train in simulator.trains.items():

            if train.status not in {
                "WAITING",
                "NOT_ENTERED"
            }:
                continue

            if (
                simulator.current_time_min
                <
                train.entry_time_min
            ):
                continue

            eligible.append(train_id)

        return eligible

    # ========================================================
    # GET SAFE RELEASE CANDIDATES
    # ========================================================

    def get_safe_candidates(
        self,
        simulator
    ):

        candidates = []

        eligible_trains = self.get_eligible_trains(
            simulator
        )

        for train_id in eligible_trains:

            # ------------------------------------------------
            # STEP 1: V2 ML prediction
            # ------------------------------------------------

            ml_result = self.ml_controller.predict_train(
                simulator,
                train_id
            )

            probabilities = ml_result.get(
                "probabilities",
                {}
            )

            probability_release = float(
                probabilities.get(
                    "RELEASE",
                    0.0
                )
            )

            # Only V2 RELEASE predictions enter
            # the ranking stage.

            if ml_result.get("action") != "RELEASE":
                continue

            # ------------------------------------------------
            # STEP 2: Safety validation
            # ------------------------------------------------

            safety_result = self.safety_controller.decide(
                simulator,
                train_id
            )

            if not safety_result.get("safe", False):
                continue

            # AISafetyController uses "final_action",
            # not "action".

            if (
                safety_result.get("final_action")
                != "RELEASE"
            ):
                continue

            # ------------------------------------------------
            # Safe RELEASE candidate
            # ------------------------------------------------

            candidate = dict(ml_result)

            candidate["safe"] = True

            candidate["probability_release"] = (
                probability_release
            )

            candidate["safety_reason"] = (
                safety_result.get(
                    "reason",
                    "Safe"
                )
            )

            candidates.append(candidate)

        return candidates

    # ========================================================
    # BUILD RANKING FEATURES
    # ========================================================

    def _build_feature_dataframe(
        self,
        simulator,
        candidates
    ):

        rows = []

        for candidate in candidates:

            train_id = candidate["train_id"]

            features = (
                self.ml_controller.extract_features(
                    simulator,
                    train_id
                )
            )

            rows.append(features)

        if not rows:

            return pd.DataFrame(
                columns=self.feature_columns
            )

        dataframe = pd.DataFrame(rows)

        # Exact training feature order

        dataframe = dataframe[
            self.feature_columns
        ].copy()

        # Numeric conversion

        for feature in self.numeric_features:

            dataframe[feature] = pd.to_numeric(
                dataframe[feature],
                errors="raise"
            )

        # Categorical conversion

        for feature in self.categorical_features:

            dataframe[feature] = (
                dataframe[feature].astype(str)
            )

        return dataframe

    # ========================================================
    # RANK SAFE CANDIDATES
    # ========================================================

    def rank_candidates(
        self,
        simulator,
        candidates
    ):

        if not candidates:
            return []

        X = self._build_feature_dataframe(
            simulator,
            candidates
        )

        X_transformed = self.preprocessor.transform(X)

        predicted_scores = (
            self.ranking_model.predict(
                X_transformed
            )
        )

        ranked = []

        for candidate, score in zip(
            candidates,
            predicted_scores
        ):

            result = dict(candidate)

            result["ranking_score"] = float(score)

            ranked.append(result)

        # Higher score = better action

        ranked.sort(
            key=lambda candidate:
                candidate["ranking_score"],
            reverse=True
        )

        return ranked

    # ========================================================
    # MAKE DECISION
    # ========================================================

    def make_decision(
        self,
        simulator
    ):

        candidates = self.get_safe_candidates(
            simulator
        )

        if not candidates:

            return {
                "time_min":
                    simulator.current_time_min,

                "action":
                    "HOLD",

                "train_id":
                    None,

                "next_section":
                    None,

                "ranking_score":
                    None,

                "reason":
                    "No safe RELEASE candidate",

                "candidates":
                    []
            }

        ranked = self.rank_candidates(
            simulator,
            candidates
        )

        best = ranked[0]

        return {
            "time_min":
                simulator.current_time_min,

            "action":
                "RELEASE",

            "train_id":
                best["train_id"],

            "next_section":
                best.get("next_section"),

            "classifier_probability":
                best.get(
                    "probability_release",
                    0.0
                ),

            "ranking_score":
                best["ranking_score"],

            "reason":
                "Selected highest-ranked safe RELEASE candidate",

            "candidates":
                ranked
        }

    # ========================================================
    # EXECUTE DECISION
    # ========================================================

    def execute_decision(
        self,
        simulator,
        decision
    ):

        if decision["action"] != "RELEASE":

            return {
                "executed":
                    False,

                "action":
                    "HOLD",

                "train_id":
                    None,

                "reason":
                    decision.get(
                        "reason",
                        "HOLD"
                    )
            }

        train_id = decision["train_id"]

        # Final safety validation immediately before
        # execution.

        safety_result = self.safety_controller.decide(
            simulator,
            train_id
        )

        if (
            not safety_result.get("safe", False)
            or
            safety_result.get("final_action")
            != "RELEASE"
        ):

            return {
                "executed":
                    False,

                "action":
                    "HOLD",

                "train_id":
                    train_id,

                "success":
                    False,

                "reason":
                    "Final safety check rejected the RELEASE."
            }

        success = simulator.start_train(
            train_id
        )

        return {
            "executed":
                bool(success),

            "action":
                "RELEASE",

            "train_id":
                train_id,

            "success":
                bool(success),

            "ranking_score":
                decision.get(
                    "ranking_score"
                ),

            "reason":
                (
                    "Train released"
                    if success
                    else
                    "Simulator rejected RELEASE"
                )
        }

    # ========================================================
    # CONTROL STEP
    # ========================================================

    def control_step(
        self,
        simulator
    ):

        decision = self.make_decision(
            simulator
        )

        execution = self.execute_decision(
            simulator,
            decision
        )

        return {
            "decision":
                decision,

            "execution":
                execution
        }
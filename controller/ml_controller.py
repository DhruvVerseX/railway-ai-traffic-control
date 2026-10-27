from pathlib import Path

import joblib
import pandas as pd


class MLTrainController:
    """
    ML-based train traffic controller.

    Loads the trained Random Forest model and converts
    the current simulator state into the exact feature
    format used during training.
    """

    def __init__(self, network, train_database, model_path=None):
        self.network = network
        self.train_database = train_database

        if model_path is None:
            project_root = Path(__file__).resolve().parent.parent
            model_path = (
                project_root
                / "ml"
                / "models"
                / "train_controller_v2.pkl"
            )

        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"ML model not found: {self.model_path}"
            )

        self.model = joblib.load(self.model_path)

        # Prevent excessive parallel workers during repeated simulations.
        # The saved model is a Pipeline, so n_jobs belongs to
        # the final RandomForest estimator inside the pipeline.
        if hasattr(self.model, "n_jobs"):
            self.model.n_jobs = 1

        if hasattr(self.model, "steps"):
            final_estimator = self.model.steps[-1][1]

            if hasattr(final_estimator, "n_jobs"):
                final_estimator.n_jobs = 1

    # ========================================================
    # FEATURE EXTRACTION
    # ========================================================

    def extract_features(self, simulator, train_id):
        """
        Extract the same features used during V2 model training
        from the current simulator state.
        """

        if train_id not in simulator.trains:
            raise ValueError(
                f"Train '{train_id}' not found in simulator."
            )

        train = simulator.trains[train_id]

        train_data = self.train_database.get_train(train_id)

        if train_data is None:
            raise ValueError(
                f"Train '{train_id}' not found in train database."
            )

        # ----------------------------------------------------
        # Basic train information
        # ----------------------------------------------------

        priority = float(train_data["priority"])
        delay_min = float(train.delay_min)
        entry_time_min = float(train.entry_time_min)

        waiting = int(train.status in {'WAITING', 'NOT_ENTERED', 'APPROACHING'}
                      and simulator.current_time_min >= max(train.entry_time_min, train.ready_time_min))
        running = 1 if train.status == "RUNNING" else 0
        arrived = 1 if train.status == "ARRIVED" else 0

        current_time_min = float(simulator.current_time_min)

        max_speed_kmph = float(train_data["max_speed_kmph"])
        length_m = float(train_data["length_m"])

        train_type = str(train_data.get("train_type", "")).lower()
        is_freight = 1 if "freight" in train_type else 0

        # ----------------------------------------------------
        # Find next section
        # ----------------------------------------------------

        movement = simulator.movement_model.build_movement(train_id)

        section_index = train.section_index

        if section_index >= len(movement.section_sequence):
            next_section = ""
        else:
            next_section = movement.section_sequence[section_index]

        # ----------------------------------------------------
        # Next section occupancy
        # ----------------------------------------------------

        occupant = simulator.get_section_occupant(next_section)

        next_section_occupied = (
            1 if occupant is not None and occupant != train_id else 0
        )

        # ----------------------------------------------------
        # Waiting trains
        # ----------------------------------------------------

        waiting_trains = [
            other_train
            for other_id, other_train in simulator.trains.items()
            if (
                other_id != train_id
                and other_train.status in {'WAITING', 'NOT_ENTERED', 'APPROACHING'}
                and simulator.current_time_min >= max(other_train.entry_time_min, other_train.ready_time_min)
            )
        ]

        waiting_train_count = len(waiting_trains)

        # ----------------------------------------------------
        # Competitors for the same next section
        # ----------------------------------------------------

        same_section_competitors = 0
        highest_competitor_priority = 0.0
        highest_competitor_delay = 0.0

        for other_train in waiting_trains:

            try:
                other_movement = (
                    simulator.movement_model.build_movement(
                        other_train.train_id
                    )
                )

                other_index = other_train.section_index

                if other_index >= len(
                    other_movement.section_sequence
                ):
                    continue

                other_next_section = (
                    other_movement.section_sequence[other_index]
                )

                if other_next_section == next_section:

                    same_section_competitors += 1

                    other_data = self.train_database.get_train(
                        other_train.train_id
                    )

                    if other_data is not None:

                        other_priority = float(
                            other_data["priority"]
                        )

                        other_delay = float(
                            other_train.delay_min
                        )

                        highest_competitor_priority = max(
                            highest_competitor_priority,
                            other_priority
                        )

                        highest_competitor_delay = max(
                            highest_competitor_delay,
                            other_delay
                        )

            except Exception:
                continue

        # ----------------------------------------------------
        # Advantage features
        # ----------------------------------------------------

        priority_advantage = (
            priority - highest_competitor_priority
        )

        delay_advantage = (
            delay_min - highest_competitor_delay
        )

        # ----------------------------------------------------
        # Section occupancy
        # ----------------------------------------------------

        features = {
            "priority": priority,
            "delay_min": delay_min,
            "entry_time_min": entry_time_min,
            "waiting": waiting,
            "running": running,
            "arrived": arrived,
            "current_time_min": current_time_min,
            "max_speed_kmph": max_speed_kmph,
            "length_m": length_m,
            "is_freight": is_freight,
            "next_section": next_section,
            "next_section_occupied": next_section_occupied,
            "waiting_train_count": waiting_train_count,
            "same_section_competitors": same_section_competitors,
            "highest_competitor_priority": (
                highest_competitor_priority
            ),
            "highest_competitor_delay": (
                highest_competitor_delay
            ),
            "priority_advantage": priority_advantage,
            "delay_advantage": delay_advantage,
        }

        for section_id in self.network.sections:

            features[
                f"section_{section_id}_occupied"
            ] = (
                1
                if simulator.get_section_occupant(section_id)
                is not None
                else 0
            )

        return features

    # ========================================================
    # PREDICTION
    # ========================================================

    def predict(self, features):
        """
        Predict HOLD or RELEASE from a feature dictionary.
        """

        feature_df = pd.DataFrame([features])

        prediction = self.model.predict(feature_df)[0]

        probabilities = self.model.predict_proba(
            feature_df
        )[0]

        classes = self.model.classes_

        probability_dict = {
            class_name: float(probability)
            for class_name, probability in zip(
                classes,
                probabilities
            )
        }

        return {
            "action": prediction,
            "probabilities": probability_dict
        }

    # ========================================================
    # PREDICT TRAIN
    # ========================================================

    def predict_train(self, simulator, train_id):
        """
        Extract the current simulator state for a train
        and return the ML recommendation.
        """

        features = self.extract_features(
            simulator,
            train_id
        )

        result = self.predict(features)

        result["train_id"] = train_id
        result["next_section"] = features["next_section"]

        return result

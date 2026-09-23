import sys
from pathlib import Path

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "training_data.csv"
)

MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "train_controller.pkl"


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

def load_dataset():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found:\n{DATASET_PATH}"
        )

    return pd.read_csv(DATASET_PATH)


# --------------------------------------------------
# PREPARE FEATURES
# --------------------------------------------------

def prepare_data(df):

    # These columns are deliberately excluded.
    #
    # train_id:
    #   Could allow the model to memorize individual trains.
    #
    # scenario_type:
    #   Artificial metadata from our scenario generator.
    #
    # target_action:
    #   This is what we are trying to predict.
    #
    # target_score:
    #   Used to determine the target and would cause leakage.

    excluded_columns = [
        "train_id",
        "scenario_type",
        "target_action",
        "target_score",
    ]

    X = df.drop(columns=excluded_columns)
    y = df["target_action"]

    return X, y


# --------------------------------------------------
# BUILD MODEL
# --------------------------------------------------

def build_model(X):

    categorical_features = [
        "next_section"
    ]

    numerical_features = [
        column
        for column in X.columns
        if column not in categorical_features
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                categorical_features,
            ),
            (
                "numerical",
                "passthrough",
                numerical_features,
            ),
        ]
    )

    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    return model


# --------------------------------------------------
# TRAIN AND EVALUATE
# --------------------------------------------------

def train_model():

    print("\n" + "=" * 60)
    print("TRAINING FIRST ML MODEL")
    print("=" * 60)

    df = load_dataset()

    print(f"\nDataset rows: {len(df)}")

    X, y = prepare_data(df)

    print(f"Features used: {len(X.columns)}")
    print(f"Target classes: {sorted(y.unique())}")

    # --------------------------------------------------
    # TRAIN / TEST SPLIT
    # --------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    print(f"\nTraining rows: {len(X_train)}")
    print(f"Testing rows:  {len(X_test)}")

    # --------------------------------------------------
    # BUILD AND TRAIN
    # --------------------------------------------------

    model = build_model(X_train)

    print("\nTraining Random Forest...")

    model.fit(X_train, y_train)

    print("Training complete.")

    # --------------------------------------------------
    # PREDICTIONS
    # --------------------------------------------------

    y_pred = model.predict(X_test)

    # --------------------------------------------------
    # EVALUATION
    # --------------------------------------------------

    accuracy = accuracy_score(y_test, y_pred)

    print("\n" + "=" * 60)
    print("MODEL PERFORMANCE")
    print("=" * 60)

    print(f"\nAccuracy: {accuracy:.4f}")
    print(f"Accuracy: {accuracy * 100:.2f}%")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            y_pred,
            digits=4,
        )
    )

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # --------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    import joblib

    joblib.dump(
        model,
        MODEL_PATH,
    )

    print("\n" + "=" * 60)
    print("MODEL SAVED")
    print("=" * 60)

    print(f"\n{MODEL_PATH}")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    train_model()
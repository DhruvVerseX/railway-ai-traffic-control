import sys
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "ml" / "data" / "training_data_v2.csv"
MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "train_controller_v2.pkl"


# ============================================================
# LOAD DATASET
# ============================================================

print("\n" + "=" * 60)
print("TRAINING V2 TRAIN TRAFFIC MODEL")
print("=" * 60)

print(f"\nLoading dataset:")
print(DATASET_PATH)

df = pd.read_csv(DATASET_PATH)

print(f"Rows:    {len(df)}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# FEATURES AND TARGET
# ============================================================

TARGET = "target_action"

# These columns identify the row or describe the answer.
# They must NOT be given to the ML model as input features.
DROP_COLUMNS = [
    "train_id",
    "scenario_type",
    "target_action",
    "target_score",
]

X = df.drop(columns=DROP_COLUMNS)
y = df[TARGET]


print("\nFeatures used by model:")
for column in X.columns:
    print(f"  - {column}")

print(f"\nNumber of features before encoding: {len(X.columns)}")


# ============================================================
# IDENTIFY FEATURE TYPES
# ============================================================

categorical_features = [
    "next_section"
]

numeric_features = [
    column
    for column in X.columns
    if column not in categorical_features
]


# ============================================================
# PREPROCESSING
# ============================================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features,
        ),
        (
            "numeric",
            "passthrough",
            numeric_features,
        ),
    ]
)


# ============================================================
# MODEL
# ============================================================

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)


pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model),
    ]
)


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y,
)


print("\n" + "=" * 60)
print("TRAIN / TEST SPLIT")
print("=" * 60)

print(f"Training rows: {len(X_train)}")
print(f"Testing rows:  {len(X_test)}")


# ============================================================
# TRAIN
# ============================================================

print("\nTraining Random Forest...")

pipeline.fit(X_train, y_train)

print("Training complete.")


# ============================================================
# PREDICTION
# ============================================================

y_pred = pipeline.predict(X_test)


# ============================================================
# EVALUATION
# ============================================================

accuracy = accuracy_score(y_test, y_pred)

print("\n" + "=" * 60)
print("MODEL PERFORMANCE")
print("=" * 60)

print(f"\nAccuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))


# ============================================================
# SAVE MODEL
# ============================================================

MODEL_DIR.mkdir(parents=True, exist_ok=True)

joblib.dump(pipeline, MODEL_PATH)

print("\n" + "=" * 60)
print("MODEL SAVED")
print("=" * 60)

print(f"\nSaved to:")
print(MODEL_PATH)

print("\nV2 MODEL TRAINING COMPLETE")
print("=" * 60)
from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "train_controller_v2.pkl"
DATASET_PATH = PROJECT_ROOT / "ml" / "data" / "training_data_v2.csv"


# ============================================================
# LOAD MODEL
# ============================================================

print("\n" + "=" * 60)
print("V2 MODEL ANALYSIS")
print("=" * 60)

print("\nLoading model:")
print(MODEL_PATH)

pipeline = joblib.load(MODEL_PATH)

print("Model loaded successfully.")


# ============================================================
# MODEL INFORMATION
# ============================================================

model = pipeline.named_steps["model"]

print("\n" + "=" * 60)
print("MODEL INFORMATION")
print("=" * 60)

print(f"\nModel type: {type(model).__name__}")
print(f"Number of trees: {model.n_estimators}")
print(f"Maximum depth: {model.max_depth}")
print(f"Minimum samples per leaf: {model.min_samples_leaf}")
print(f"Class weight: {model.class_weight}")


# ============================================================
# GET FEATURE NAMES
# ============================================================

preprocessor = pipeline.named_steps["preprocessor"]

feature_names = preprocessor.get_feature_names_out()

importances = model.feature_importances_

importance_df = pd.DataFrame({
    "feature": feature_names,
    "importance": importances
})

importance_df = importance_df.sort_values(
    by="importance",
    ascending=False
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 60)
print("TOP FEATURE IMPORTANCES")
print("=" * 60)

for _, row in importance_df.head(25).iterrows():
    print(
        f"{row['feature']:<45} "
        f"{row['importance']:.4f}"
    )


# ============================================================
# IMPORTANCE GROUPS
# ============================================================

print("\n" + "=" * 60)
print("FEATURE IMPORTANCE GROUPS")
print("=" * 60)

def group_feature(feature_name):
    if "next_section_occupied" in feature_name:
        return "next_section_occupied"
    if "priority_advantage" in feature_name:
        return "priority_advantage"
    if "delay_advantage" in feature_name:
        return "delay_advantage"
    if "waiting_train_count" in feature_name:
        return "waiting_train_count"
    if "same_section_competitors" in feature_name:
        return "same_section_competitors"
    if "highest_competitor_priority" in feature_name:
        return "highest_competitor_priority"
    if "highest_competitor_delay" in feature_name:
        return "highest_competitor_delay"
    if "section_" in feature_name and "_occupied" in feature_name:
        return "section_occupancy"
    if "next_section_" in feature_name:
        return "next_section"
    if "priority" in feature_name:
        return "priority"
    if "delay_min" in feature_name:
        return "delay"
    if "entry_time_min" in feature_name:
        return "entry_time"
    if "current_time_min" in feature_name:
        return "current_time"
    if "max_speed" in feature_name:
        return "speed"
    if "length" in feature_name:
        return "length"
    if "freight" in feature_name:
        return "freight"
    if feature_name.endswith("__waiting") or feature_name.endswith("_waiting"):
        return "waiting"
    if "running" in feature_name:
        return "running"
    if "arrived" in feature_name:
        return "arrived"

    return "other"


importance_df["group"] = importance_df["feature"].apply(
    group_feature
)

grouped_importance = (
    importance_df
    .groupby("group")["importance"]
    .sum()
    .sort_values(ascending=False)
)

print("\nTotal importance by feature group:")

for group, importance in grouped_importance.items():
    print(f"{group:<35} {importance:.4f}")


# ============================================================
# DATASET CHECK
# ============================================================

df = pd.read_csv(DATASET_PATH)

print("\n" + "=" * 60)
print("DATASET INFORMATION")
print("=" * 60)

print(f"\nRows: {len(df)}")
print(f"Columns: {len(df.columns)}")

print("\nTarget distribution:")

print(df["target_action"].value_counts())

print("\nTarget percentages:")

print(
    df["target_action"]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 60)
print("V2 MODEL ANALYSIS COMPLETE")
print("=" * 60)
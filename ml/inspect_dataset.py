import sys
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# PROJECT PATH
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "ml" / "data" / "training_data_v2.csv"


# --------------------------------------------------
# LOAD DATASET
# --------------------------------------------------

def load_dataset():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found:\n{DATASET_PATH}"
        )

    return pd.read_csv(DATASET_PATH)


# --------------------------------------------------
# BASIC INSPECTION
# --------------------------------------------------

def inspect_basic(df):
    print("\n" + "=" * 60)
    print("BASIC DATASET INFORMATION")
    print("=" * 60)

    print(f"Rows:    {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")


# --------------------------------------------------
# MISSING VALUES
# --------------------------------------------------

def inspect_missing_values(df):
    print("\n" + "=" * 60)
    print("MISSING VALUES")
    print("=" * 60)

    missing = df.isnull().sum()

    missing = missing[missing > 0]

    if missing.empty:
        print("No missing values found.")
    else:
        print(missing)


# --------------------------------------------------
# DUPLICATES
# --------------------------------------------------

def inspect_duplicates(df):
    print("\n" + "=" * 60)
    print("DUPLICATES")
    print("=" * 60)

    duplicates = df.duplicated().sum()

    print(f"Duplicate rows: {duplicates}")


# --------------------------------------------------
# TARGET DISTRIBUTION
# --------------------------------------------------

def inspect_target(df):
    print("\n" + "=" * 60)
    print("TARGET ACTION DISTRIBUTION")
    print("=" * 60)

    counts = df["target_action"].value_counts()

    print(counts)

    print("\nPercentages:")
    print(
        df["target_action"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )


# --------------------------------------------------
# SCENARIO DISTRIBUTION
# --------------------------------------------------

def inspect_scenarios(df):
    print("\n" + "=" * 60)
    print("SCENARIO DISTRIBUTION")
    print("=" * 60)

    print(df["scenario_type"].value_counts())


# --------------------------------------------------
# SCENARIO × TARGET
# --------------------------------------------------

def inspect_scenario_target(df):
    print("\n" + "=" * 60)
    print("SCENARIO × TARGET ACTION")
    print("=" * 60)

    table = pd.crosstab(
        df["scenario_type"],
        df["target_action"]
    )

    print(table)


# --------------------------------------------------
# OCCUPANCY × TARGET
# --------------------------------------------------

def inspect_occupancy_target(df):
    print("\n" + "=" * 60)
    print("NEXT SECTION OCCUPANCY × TARGET")
    print("=" * 60)

    table = pd.crosstab(
        df["next_section_occupied"],
        df["target_action"]
    )

    print(table)


# --------------------------------------------------
# NUMERIC FEATURES
# --------------------------------------------------

def inspect_numeric_features(df):
    print("\n" + "=" * 60)
    print("NUMERIC FEATURE SUMMARY")
    print("=" * 60)

    numeric_columns = df.select_dtypes(
        include=["number"]
    ).columns

    print(
        df[numeric_columns]
        .describe()
        .round(2)
        .to_string()
    )


# --------------------------------------------------
# TARGET SCORE
# --------------------------------------------------

def inspect_target_score(df):
    print("\n" + "=" * 60)
    print("TARGET SCORE")
    print("=" * 60)

    print(
        df.groupby("target_action")["target_score"]
        .agg(["count", "min", "mean", "max"])
        .round(2)
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\nTRAINING DATASET INSPECTION")

    df = load_dataset()

    inspect_basic(df)
    inspect_missing_values(df)
    inspect_duplicates(df)
    inspect_target(df)
    inspect_scenarios(df)
    inspect_scenario_target(df)
    inspect_occupancy_target(df)
    inspect_numeric_features(df)
    inspect_target_score(df)

    print("\n" + "=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
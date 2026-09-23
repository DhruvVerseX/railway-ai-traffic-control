import os

# Prevent excessive parallel threads from scikit-learn / OpenBLAS.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import pickle
from pathlib import Path

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

DATASET_FILE = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "ranking_training_data.csv"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "ml"
    / "models"
)

MODEL_FILE = (
    MODEL_DIR
    / "action_ranking_model.pkl"
)


# ============================================================
# SETTINGS
# ============================================================

TEST_SCENARIO_START = 80

RANDOM_STATE = 42


# ============================================================
# LOAD DATASET
# ============================================================

df = pd.read_csv(
    DATASET_FILE
)


# ============================================================
# COLUMN DEFINITIONS
# ============================================================

metadata_columns = {
    "train_id",
    "scenario_id",
    "scenario_type",
    "decision_time_min",
    "section_id",
    "target_score"
}


feature_columns = [
    column
    for column in df.columns
    if column not in metadata_columns
]


categorical_features = [
    "next_section"
]


numeric_features = [
    feature
    for feature in feature_columns
    if feature not in categorical_features
]


# ============================================================
# SCENARIO-BASED TRAIN / TEST SPLIT
# ============================================================

train_mask = (
    df["scenario_id"]
    < TEST_SCENARIO_START
)

test_mask = (
    df["scenario_id"]
    >= TEST_SCENARIO_START
)


# ============================================================
# BUILD X / y
# ============================================================

X = df[
    feature_columns
].copy()


y = df[
    "target_score"
].astype(float)


# ------------------------------------------------------------
# Convert numeric features to actual numbers
# ------------------------------------------------------------

for feature in numeric_features:

    X[feature] = pd.to_numeric(
        X[feature],
        errors="raise"
    )


# ------------------------------------------------------------
# Keep next_section categorical
# ------------------------------------------------------------

X["next_section"] = (
    X["next_section"]
    .astype(str)
)


# ------------------------------------------------------------
# Create train / test sets
# ------------------------------------------------------------

X_train = X.loc[
    train_mask
].copy()

X_test = X.loc[
    test_mask
].copy()


y_train = y.loc[
    train_mask
].copy()

y_test = y.loc[
    test_mask
].copy()


# ============================================================
# PRINT DATASET INFORMATION
# ============================================================

print("\n==========================================")
print("RANKING MODEL TRAINING")
print("==========================================")

print(
    "Total rows:",
    len(df)
)

print(
    "Training rows:",
    len(X_train)
)

print(
    "Testing rows:",
    len(X_test)
)

print(
    "Training scenarios:",
    df.loc[
        train_mask,
        "scenario_id"
    ].nunique()
)

print(
    "Testing scenarios:",
    df.loc[
        test_mask,
        "scenario_id"
    ].nunique()
)

print(
    "Number of features:",
    len(feature_columns)
)


# ============================================================
# PREPROCESSING
# ============================================================

preprocessor = ColumnTransformer(
    transformers=[

        (
            "categorical",

            OneHotEncoder(
                handle_unknown="ignore"
            ),

            categorical_features
        ),

        (
            "numeric",

            "passthrough",

            numeric_features
        )
    ]
)


# ============================================================
# TRANSFORM DATA
# ============================================================

print("\nPreparing features...")

X_train_transformed = (
    preprocessor.fit_transform(
        X_train
    )
)

X_test_transformed = (
    preprocessor.transform(
        X_test
    )
)


print(
    "Transformed training shape:",
    X_train_transformed.shape
)

print(
    "Transformed testing shape:",
    X_test_transformed.shape
)


# ============================================================
# RANDOM FOREST REGRESSOR
# ============================================================

model = RandomForestRegressor(

    n_estimators=300,

    max_depth=14,

    min_samples_leaf=2,

    random_state=RANDOM_STATE,

    n_jobs=1
)


print("\nTraining Random Forest...")

model.fit(
    X_train_transformed,
    y_train
)


# ============================================================
# PREDICTIONS
# ============================================================

print("Generating predictions...")

predictions = model.predict(
    X_test_transformed
)


# ============================================================
# REGRESSION METRICS
# ============================================================

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


print("\n=== REGRESSION PERFORMANCE ===")

print(
    "MAE:",
    round(mae, 4)
)

print(
    "RMSE:",
    round(rmse, 4)
)

print(
    "R²:",
    round(r2, 4)
)


# ============================================================
# RANKING ACCURACY
#
# For each decision group:
#
#   actual best candidate
#              vs
#   predicted best candidate
#
# This is more important than R² for our application.
# ============================================================

test_groups = {}


for index, row in df.loc[
    test_mask
].iterrows():

    key = (
        row["scenario_id"],
        row["decision_time_min"]
    )

    if key not in test_groups:

        test_groups[key] = []


    # Convert original dataframe index
    # to prediction-array position.

    prediction_index = (
        X_test.index.get_loc(index)
    )


    test_groups[key].append(
        {
            "index":
                prediction_index,

            "actual_score":
                float(
                    row["target_score"]
                ),

            "prediction":
                float(
                    predictions[
                        prediction_index
                    ]
                ),

            "train_id":
                row["train_id"]
        }
    )


# ============================================================
# CALCULATE RANKING METRICS
# ============================================================

total_groups = 0

correct_groups = 0

regret_values = []


for group_rows in test_groups.values():

    if len(group_rows) < 2:

        continue


    total_groups += 1


    # --------------------------------------------------------
    # Actual best action
    # --------------------------------------------------------

    actual_best = max(
        group_rows,

        key=lambda row:
            row["actual_score"]
    )


    # --------------------------------------------------------
    # Model predicted best action
    # --------------------------------------------------------

    predicted_best = max(
        group_rows,

        key=lambda row:
            row["prediction"]
    )


    # --------------------------------------------------------
    # Check whether model selected true best
    # --------------------------------------------------------

    if (
        predicted_best["train_id"]
        == actual_best["train_id"]
    ):

        correct_groups += 1


    # --------------------------------------------------------
    # Calculate regret
    # --------------------------------------------------------

    regret = (
        actual_best["actual_score"]
        -
        predicted_best["actual_score"]
    )


    regret_values.append(
        regret
    )


# ============================================================
# RANKING METRICS
# ============================================================

ranking_accuracy = (

    correct_groups
    /
    total_groups
    *
    100

    if total_groups > 0

    else 0
)


average_regret = (

    sum(regret_values)
    /
    len(regret_values)

    if regret_values

    else 0
)


zero_regret = sum(

    1

    for regret
    in regret_values

    if abs(regret) < 1e-9
)


zero_regret_rate = (

    zero_regret
    /
    len(regret_values)
    *
    100

    if regret_values

    else 0
)


# ============================================================
# PRINT RANKING PERFORMANCE
# ============================================================

print("\n=== RANKING PERFORMANCE ===")

print(
    "Test decision groups:",
    total_groups
)

print(
    "Correct best-action selections:",
    correct_groups
)

print(
    "Ranking accuracy:",
    round(
        ranking_accuracy,
        2
    ),
    "%"
)

print(
    "Average regret:",
    round(
        average_regret,
        4
    )
)

print(
    "Zero-regret selections:",
    round(
        zero_regret_rate,
        2
    ),
    "%"
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

feature_names = (
    preprocessor
    .get_feature_names_out()
)


importances = (
    model.feature_importances_
)


importance_pairs = sorted(

    zip(
        feature_names,
        importances
    ),

    key=lambda pair:
        pair[1],

    reverse=True
)


print(
    "\n=== TOP 20 FEATURE IMPORTANCES ==="
)


for feature, importance in (
    importance_pairs[:20]
):

    print(
        feature,
        ":",
        round(
            importance,
            4
        )
    )


# ============================================================
# SAVE MODEL + PREPROCESSOR
# ============================================================

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


model_package = {

    "model":
        model,

    "preprocessor":
        preprocessor,

    "feature_columns":
        feature_columns,

    "categorical_features":
        categorical_features,

    "numeric_features":
        numeric_features
}


with open(
    MODEL_FILE,
    "wb"
) as file:

    pickle.dump(
        model_package,
        file
    )


# ============================================================
# FINAL
# ============================================================

print(
    "\n=========================================="
)

print(
    "RANKING MODEL TRAINING COMPLETE"
)

print(
    "=========================================="
)

print(
    "Model saved to:"
)

print(
    MODEL_FILE
)
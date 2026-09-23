from pathlib import Path

import joblib
import pandas as pd


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "train_controller.pkl"
)


# --------------------------------------------------
# LOAD MODEL
# --------------------------------------------------

def load_model():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found:\n{MODEL_PATH}"
        )

    return joblib.load(MODEL_PATH)


# --------------------------------------------------
# FEATURE IMPORTANCE
# --------------------------------------------------

def analyze_feature_importance(model):

    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE")
    print("=" * 60)

    # Our model is a Pipeline:
    #   preprocessing → Random Forest
    #
    # Therefore we first extract the two components.

    preprocessor = model.named_steps["preprocessor"]
    classifier = model.named_steps["classifier"]

    # Get names after OneHotEncoder transforms next_section.
    feature_names = preprocessor.get_feature_names_out()

    importances = classifier.feature_importances_

    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances
    })

    importance_df = importance_df.sort_values(
        by="importance",
        ascending=False
    )

    print("\nAll features:\n")

    for _, row in importance_df.iterrows():

        print(
            f"{row['feature']:<45}"
            f"{row['importance']:.4f}"
        )

    print("\n" + "=" * 60)
    print("TOP 10 FEATURES")
    print("=" * 60)

    print(
        importance_df
        .head(10)
        .to_string(index=False)
    )


# --------------------------------------------------
# MODEL INFORMATION
# --------------------------------------------------

def show_model_information(model):

    print("\n" + "=" * 60)
    print("MODEL INFORMATION")
    print("=" * 60)

    classifier = model.named_steps["classifier"]

    print(f"\nModel type: {type(classifier).__name__}")
    print(f"Number of trees: {classifier.n_estimators}")
    print(f"Maximum depth: {classifier.max_depth}")
    print(f"Minimum samples per leaf: {classifier.min_samples_leaf}")
    print(f"Class weighting: {classifier.class_weight}")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\nTRAINED MODEL ANALYSIS")

    model = load_model()

    show_model_information(model)
    analyze_feature_importance(model)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
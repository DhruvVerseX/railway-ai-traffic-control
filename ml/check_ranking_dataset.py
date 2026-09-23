import csv
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_FILE = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "ranking_training_data.csv"
)


# ============================================================
# LOAD DATASET
# ============================================================

with open(
    DATASET_FILE,
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)
    rows = list(reader)

columns = reader.fieldnames


# ============================================================
# BASIC INFORMATION
# ============================================================

print("\n==========================================")
print("RANKING DATASET CHECK")
print("==========================================")

print(
    "Rows:",
    len(rows)
)

print(
    "Columns:",
    len(columns)
)


# ============================================================
# REQUIRED COLUMNS
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
    for column in columns
    if column not in metadata_columns
]

print(
    "Feature columns:",
    len(feature_columns)
)


# ============================================================
# MISSING VALUES
# ============================================================

missing_counts = Counter()

for row in rows:

    for column in columns:

        value = row[column]

        if value is None or value.strip() == "":
            missing_counts[column] += 1


print("\n=== MISSING VALUES ===")

if not missing_counts:

    print("No missing values.")

else:

    for column, count in missing_counts.items():

        print(
            column,
            ":",
            count
        )


# ============================================================
# DUPLICATES
# ============================================================

row_tuples = [
    tuple(row[column] for column in columns)
    for row in rows
]

duplicate_count = (
    len(row_tuples)
    - len(set(row_tuples))
)


print("\n=== DUPLICATES ===")

print(
    "Duplicate rows:",
    duplicate_count
)


# ============================================================
# TARGET SCORE
# ============================================================

scores = [
    float(row["target_score"])
    for row in rows
]

print("\n=== TARGET SCORE ===")

print(
    "Minimum:",
    min(scores)
)

print(
    "Maximum:",
    max(scores)
)

print(
    "Average:",
    round(
        sum(scores) / len(scores),
        4
    )
)


# ============================================================
# SCORE DISTRIBUTION
# ============================================================

print("\n=== SCORE DISTRIBUTION ===")

score_ranges = [
    ("<-2000", lambda x: x < -2000),
    ("-2000 to -1500", lambda x: -2000 <= x < -1500),
    ("-1500 to -1000", lambda x: -1500 <= x < -1000),
    ("-1000 to -500", lambda x: -1000 <= x < -500),
    (">=-500", lambda x: x >= -500),
]

for name, condition in score_ranges:

    count = sum(
        1
        for score in scores
        if condition(score)
    )

    percentage = (
        count
        / len(scores)
        * 100
    )

    print(
        f"{name}: {count} "
        f"({percentage:.2f}%)"
    )


# ============================================================
# DECISION GROUPS
#
# A decision group = one scenario at one simulation time.
# Every candidate inside that group was evaluated from the
# same traffic state.
# ============================================================

groups = defaultdict(list)

for row in rows:

    key = (
        row["scenario_id"],
        row["decision_time_min"]
    )

    groups[key].append(row)


group_sizes = [
    len(candidates)
    for candidates in groups.values()
]


print("\n=== DECISION GROUPS ===")

print(
    "Decision groups:",
    len(groups)
)

print(
    "Minimum candidates per group:",
    min(group_sizes)
)

print(
    "Maximum candidates per group:",
    max(group_sizes)
)

print(
    "Average candidates per group:",
    round(
        sum(group_sizes)
        / len(group_sizes),
        2
    )
)


# ============================================================
# GROUPS WITH ONLY ONE CANDIDATE
# ============================================================

single_candidate_groups = sum(
    1
    for size in group_sizes
    if size < 2
)

print(
    "Groups with <2 candidates:",
    single_candidate_groups
)


# ============================================================
# BEST-CANDIDATE DISTRIBUTION
# ============================================================

best_candidate_count = 0
unique_best_count = 0

for group_rows in groups.values():

    best_score = max(
        float(row["target_score"])
        for row in group_rows
    )

    best_rows = [
        row
        for row in group_rows
        if float(row["target_score"])
        == best_score
    ]

    if len(best_rows) == 1:

        unique_best_count += 1

    best_candidate_count += len(best_rows)


print("\n=== BEST ACTION ANALYSIS ===")

print(
    "Decision groups:",
    len(groups)
)

print(
    "Groups with unique best action:",
    unique_best_count
)

print(
    "Groups with tied best actions:",
    len(groups) - unique_best_count
)


# ============================================================
# TARGET SCORE VARIATION
#
# This tells us whether ranking is actually meaningful.
# If almost every candidate in a group has the same score,
# there is little for a ranking model to learn.
# ============================================================

score_ranges_per_group = []

for group_rows in groups.values():

    group_scores = [
        float(row["target_score"])
        for row in group_rows
    ]

    variation = (
        max(group_scores)
        - min(group_scores)
    )

    score_ranges_per_group.append(
        variation
    )


print("\n=== WITHIN-DECISION SCORE VARIATION ===")

print(
    "Average score range:",
    round(
        sum(score_ranges_per_group)
        / len(score_ranges_per_group),
        4
    )
)

print(
    "Maximum score range:",
    round(
        max(score_ranges_per_group),
        4
    )
)

zero_variation = sum(
    1
    for value in score_ranges_per_group
    if value == 0
)

print(
    "Groups with identical scores:",
    zero_variation
)

print(
    "Groups with different scores:",
    len(groups) - zero_variation
)


# ============================================================
# POTENTIAL DATA LEAKAGE CHECK
# ============================================================

print("\n=== FEATURE / TARGET CHECK ===")

leakage_names = [
    "target",
    "score",
    "label",
    "outcome",
    "throughput_contribution",
    "waiting_penalty",
    "delay_penalty",
    "conflict_penalty",
    "priority_bonus"
]

possible_leaks = []

for feature in feature_columns:

    feature_lower = feature.lower()

    for forbidden in leakage_names:

        if forbidden in feature_lower:

            possible_leaks.append(
                feature
            )

            break


if possible_leaks:

    print(
        "WARNING: Possible target-related features:"
    )

    for feature in possible_leaks:

        print(
            " ",
            feature
        )

else:

    print(
        "No obvious target-related feature names found."
    )


# ============================================================
# FEATURE TYPES
# ============================================================

print("\n=== FEATURE TYPE CHECK ===")

non_numeric_features = []

for feature in feature_columns:

    values = [
        row[feature]
        for row in rows
        if row[feature] != ""
    ]

    try:

        for value in values:

            float(value)

    except ValueError:

        non_numeric_features.append(
            feature
        )


if non_numeric_features:

    print(
        "Non-numeric features:"
    )

    for feature in non_numeric_features:

        print(
            " ",
            feature
        )

else:

    print(
        "All feature columns are numeric."
    )


# ============================================================
# SAMPLE DECISION GROUP
# ============================================================

print("\n=== SAMPLE DECISION GROUP ===")

sample_key = next(
    iter(groups)
)

sample_rows = groups[sample_key]

print(
    "Scenario:",
    sample_key[0]
)

print(
    "Decision time:",
    sample_key[1]
)

for row in sorted(
    sample_rows,
    key=lambda x:
        float(x["target_score"]),
    reverse=True
):

    print(
        "Train:",
        row["train_id"],
        "| Section:",
        row["section_id"],
        "| Score:",
        row["target_score"]
    )


# ============================================================
# FINAL STATUS
# ============================================================

print("\n==========================================")
print("DATASET CHECK COMPLETE")
print("==========================================")

if (
    not missing_counts
    and duplicate_count == 0
    and single_candidate_groups == 0
    and not possible_leaks
    and not non_numeric_features
):

    print(
        "STATUS: DATASET LOOKS CLEAN FOR "
        "INITIAL RANKING MODEL TRAINING."
    )

else:

    print(
        "STATUS: REVIEW WARNINGS ABOVE "
        "BEFORE TRAINING."
    )
import csv
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

INPUT_FILE = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "ranking_training_data.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "ranking_training_data_v2.csv"
)


# ============================================================
# LOAD ORIGINAL DATASET
# ============================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    rows = list(reader)


if not rows:
    raise ValueError(
        "Ranking dataset is empty."
    )


# ============================================================
# GROUP CANDIDATE ACTIONS BY DECISION POINT
#
# Every group represents one traffic state / decision time.
# All candidate actions inside that group were evaluated by
# the optimizer.
# ============================================================

groups = {}


for row in rows:

    key = (
        row["scenario_id"],
        row["decision_time_min"]
    )

    if key not in groups:

        groups[key] = []

    groups[key].append(row)


# ============================================================
# CREATE V2 TARGET
#
# Instead of predicting the absolute optimizer score:
#
#     target_score
#
# we calculate:
#
#     relative_score =
#         candidate_score - best_score_in_this_group
#
#
# Therefore:
#
# BEST ACTION  -> 0
# WORSE ACTION -> negative value
#
# Example:
#
# T001 -> -1530
# T006 -> -1280
# T009 -> -1200  <- best
#
# becomes:
#
# T001 -> -330
# T006 ->  -80
# T009 ->    0
#
# The model therefore learns which candidate is better
# relative to the other candidates at the SAME decision point.
# ============================================================

output_rows = []


for group_rows in groups.values():

    # --------------------------------------------------------
    # Find the best optimizer score in this decision point
    # --------------------------------------------------------

    best_score = max(
        float(row["target_score"])
        for row in group_rows
    )


    # --------------------------------------------------------
    # Convert every candidate into a relative score
    # --------------------------------------------------------

    for row in group_rows:

        absolute_score = float(
            row["target_score"]
        )

        relative_score = (
            absolute_score
            - best_score
        )


        new_row = dict(row)

        new_row["relative_score"] = round(
            relative_score,
            6
        )


        output_rows.append(
            new_row
        )


# ============================================================
# COLUMN ORDER
# ============================================================

fieldnames = list(
    rows[0].keys()
)

fieldnames.append(
    "relative_score"
)


# ============================================================
# SAVE V2 DATASET
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        output_rows
    )


# ============================================================
# DATASET STATISTICS
# ============================================================

relative_scores = [
    float(
        row["relative_score"]
    )
    for row in output_rows
]


best_count = sum(
    1
    for score in relative_scores
    if abs(score) < 1e-9
)


print("\n==========================================")
print("RANKING DATASET V2")
print("==========================================")

print(
    "Original rows:",
    len(rows)
)

print(
    "V2 rows:",
    len(output_rows)
)

print(
    "Decision groups:",
    len(groups)
)

print(
    "Best-action labels:",
    best_count
)

print(
    "Minimum relative score:",
    round(
        min(relative_scores),
        4
    )
)

print(
    "Maximum relative score:",
    round(
        max(relative_scores),
        4
    )
)

print(
    "Average relative score:",
    round(
        sum(relative_scores)
        /
        len(relative_scores),
        4
    )
)


# ============================================================
# CHECK THAT EVERY GROUP HAS A ZERO-SCORE BEST ACTION
# ============================================================

groups_without_best = 0


for group_rows in groups.values():

    scores = [
        float(
            row["relative_score"]
        )
        for row in output_rows
        if (
            row["scenario_id"]
            == group_rows[0]["scenario_id"]
            and
            row["decision_time_min"]
            == group_rows[0]["decision_time_min"]
        )
    ]

    if not any(
        abs(score) < 1e-9
        for score in scores
    ):

        groups_without_best += 1


print(
    "Groups without best-action label:",
    groups_without_best
)


# ============================================================
# FINAL
# ============================================================

print("\n==========================================")
print("RANKING DATASET V2 CREATED")
print("==========================================")

print(
    "Saved to:"
)

print(
    OUTPUT_FILE
)
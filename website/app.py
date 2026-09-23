import streamlit as st

from railway_ai.simulation.network import RailwayNetwork
from railway_ai.input.input_state import TrainDatabase
from railway_ai.scenarios.mixed_scenario_builder import MixedScenarioBuilder
from railway_ai.simulation.simulator import RailwaySimulator
from railway_ai.controller.ml_controller import MLTrainController
from railway_ai.controller.ai_controller import AITrainTrafficController


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Railway AI Traffic Control",
    page_icon="🚆",
    layout="wide"
)


# =========================================================
# PROJECT OBJECTS
# =========================================================

@st.cache_resource
def load_project():

    network = RailwayNetwork()

    train_database = TrainDatabase()

    scenario_builder = MixedScenarioBuilder(
        network,
        train_database
    )

    # V2 machine-learning model
    ml_controller = MLTrainController(
        network,
        train_database
    )

    # Complete AI controller:
    # ML prediction + safety/conflict checking
    ai_controller = AITrainTrafficController(
        network,
        train_database
    )

    return (
        network,
        train_database,
        scenario_builder,
        ml_controller,
        ai_controller
    )


(
    network,
    train_database,
    scenario_builder,
    ml_controller,
    ai_controller
) = load_project()


# =========================================================
# SESSION STATE
# =========================================================

if "simulator" not in st.session_state:
    st.session_state.simulator = RailwaySimulator(network)

if "scenario_loaded" not in st.session_state:
    st.session_state.scenario_loaded = False

if "scenario_id" not in st.session_state:
    st.session_state.scenario_id = None

if "ai_recommendations" not in st.session_state:
    st.session_state.ai_recommendations = []

if "safe_ai_decision" not in st.session_state:
    st.session_state.safe_ai_decision = None

if "last_ai_execution" not in st.session_state:
    st.session_state.last_ai_execution = None


simulator = st.session_state.simulator


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_train_data(train_id):

    train = train_database.get_train(train_id)

    if isinstance(train, dict):
        return train

    if hasattr(train, "__dict__"):
        return vars(train)

    return {}


def get_train_speed(sim_train):

    if sim_train.status != "RUNNING":
        return 0.0

    section_id = sim_train.current_section

    if not section_id:
        return 0.0

    section = network.sections.get(section_id)

    if section is None:
        return 0.0

    train_data = get_train_data(sim_train.train_id)

    max_speed = float(
        train_data.get(
            "max_speed_kmph",
            section.normal_speed_kmph
        )
    )

    return min(
        max_speed,
        section.normal_speed_kmph
    )


def get_status_label(status):

    labels = {
        "RUNNING": "🟢 Moving",
        "WAITING": "🟡 Waiting",
        "NOT_ENTERED": "⚪ Not entered",
        "ARRIVED": "🔵 Arrived"
    }

    return labels.get(status, status)


def start_eligible_trains():

    started = []

    for train_id, train in simulator.trains.items():

        if train.status not in ["WAITING", "NOT_ENTERED"]:
            continue

        if simulator.current_time_min < train.entry_time_min:
            continue

        success = simulator.start_train(train_id)

        if success:
            started.append(train_id)

    return started


# =========================================================
# RAW ML PREDICTIONS
# =========================================================

def get_ai_recommendations():

    recommendations = []

    for train_id, train in simulator.trains.items():

        if train.status not in ["WAITING", "NOT_ENTERED"]:
            continue

        if simulator.current_time_min < train.entry_time_min:
            continue

        try:

            result = ml_controller.predict_train(
                simulator,
                train_id
            )

            recommendations.append(result)

        except Exception as e:

            recommendations.append(
                {
                    "train_id": train_id,
                    "error": str(e)
                }
            )

    return recommendations


# =========================================================
# SAFETY-CHECKED AI DECISION
# =========================================================

def get_safe_ai_decision():

    try:

        result = ai_controller.make_decision(
            simulator
        )

        return result

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# EXECUTE AI DECISION
# =========================================================

def execute_ai_decision():

    try:

        # control_step performs the complete AI control cycle:
        #
        # 1. Find eligible trains
        # 2. Get ML predictions
        # 3. Apply safety/conflict checking
        # 4. Select the final action
        # 5. Execute RELEASE if selected
        #
        result = ai_controller.control_step(
            simulator
        )

        return result

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# HEADER
# =========================================================

st.title("🚆 Railway AI Traffic Control")

st.caption(
    "AI-powered decision support for railway section traffic management"
)


# =========================================================
# SIMULATION CONTROLS
# =========================================================

st.subheader("Simulation")

col1, col2, col3, col4 = st.columns(4)


# ---------------------------------------------------------
# GENERATE SCENARIO
# ---------------------------------------------------------

with col1:

    if st.button(
        "Generate Scenario",
        width="stretch"
    ):

        scenario_id = "WEB_001"

        traffic_state = scenario_builder.generate_mixed_scenario(
            scenario_id=scenario_id,
            num_trains=6,
            scenario_type="random",
            decision_time_min=5.0,
            running_advance_min=5.0,
            seed=42
        )

        simulator.load_traffic(
            traffic_state,
            train_database
        )

        st.session_state.scenario_loaded = True
        st.session_state.scenario_id = scenario_id

        # Clear old AI results.
        st.session_state.ai_recommendations = []
        st.session_state.safe_ai_decision = None
        st.session_state.last_ai_execution = None

        # Start trains already eligible to enter.
        start_eligible_trains()

        st.rerun()


# ---------------------------------------------------------
# ADVANCE TIME
# ---------------------------------------------------------

with col2:

    if st.button(
        "▶ Advance 5 min",
        width="stretch",
        disabled=not st.session_state.scenario_loaded
    ):

        simulator.advance_time(5)

        # Start newly eligible trains.
        start_eligible_trains()

        # Previous AI results are now outdated.
        st.session_state.ai_recommendations = []
        st.session_state.safe_ai_decision = None
        st.session_state.last_ai_execution = None

        st.rerun()


# ---------------------------------------------------------
# START ELIGIBLE
# ---------------------------------------------------------

with col3:

    if st.button(
        "▶ Start Eligible",
        width="stretch",
        disabled=not st.session_state.scenario_loaded
    ):

        start_eligible_trains()

        st.session_state.ai_recommendations = []
        st.session_state.safe_ai_decision = None
        st.session_state.last_ai_execution = None

        st.rerun()


# ---------------------------------------------------------
# RESET
# ---------------------------------------------------------

with col4:

    if st.button(
        "↻ Reset",
        width="stretch"
    ):

        st.session_state.simulator = RailwaySimulator(network)

        st.session_state.scenario_loaded = False
        st.session_state.scenario_id = None

        st.session_state.ai_recommendations = []
        st.session_state.safe_ai_decision = None
        st.session_state.last_ai_execution = None

        st.rerun()


# =========================================================
# SIMULATION STATUS
# =========================================================

if st.session_state.scenario_loaded:

    st.info(
        f"Scenario: {st.session_state.scenario_id}   |   "
        f"Simulation time: {simulator.current_time_min:.1f} min"
    )

else:

    st.info(
        "Generate a scenario to load trains into the simulator."
    )


# =========================================================
# CURRENT TRAFFIC
# =========================================================

st.subheader("Current Traffic")


if not simulator.trains:

    st.write("No trains currently loaded.")

else:

    rows = []

    for train_id, sim_train in simulator.trains.items():

        train_data = get_train_data(train_id)

        train_name = train_data.get(
            "train_name",
            train_data.get(
                "name",
                "Unknown"
            )
        )

        train_type = train_data.get(
            "train_type",
            train_data.get(
                "type",
                "Unknown"
            )
        )

        priority = train_data.get(
            "priority",
            0
        )

        max_speed = train_data.get(
            "max_speed_kmph",
            ""
        )

        speed = get_train_speed(sim_train)

        current_location = (
            sim_train.current_section
            if sim_train.current_section
            else sim_train.current_station
        )

        rows.append(
            {
                "Train": train_id,
                "Name": train_name,
                "Type": train_type,
                "Location": current_location,
                "Next": sim_train.next_station or "-",
                "Speed (km/h)": round(speed, 1),
                "Max Speed": max_speed,
                "Status": get_status_label(
                    sim_train.status
                ),
                "Delay (min)": round(
                    sim_train.delay_min,
                    1
                ),
                "Priority": priority
            }
        )

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True
    )


# =========================================================
# AI DECISION SUPPORT
# =========================================================

st.divider()

st.subheader("🤖 AI Decision Support")

st.caption(
    "The V2 machine-learning model predicts HOLD or RELEASE. "
    "The safety layer checks section occupancy, conflicts and "
    "headway constraints before an action can be executed."
)


if not st.session_state.scenario_loaded:

    st.info(
        "Generate a scenario first."
    )

else:

    col1, col2, col3 = st.columns(3)


    # -----------------------------------------------------
    # ASK ML MODEL
    # -----------------------------------------------------

    with col1:

        if st.button(
            "🤖 Ask ML Model",
            width="stretch"
        ):

            st.session_state.ai_recommendations = (
                get_ai_recommendations()
            )

            st.session_state.safe_ai_decision = None
            st.session_state.last_ai_execution = None

            st.rerun()


    # -----------------------------------------------------
    # SAFETY CHECK
    # -----------------------------------------------------

    with col2:

        if st.button(
            "🛡️ Safety Check",
            width="stretch"
        ):

            st.session_state.safe_ai_decision = (
                get_safe_ai_decision()
            )

            st.session_state.last_ai_execution = None

            st.rerun()


    # -----------------------------------------------------
    # EXECUTE AI
    # -----------------------------------------------------

    with col3:

        if st.button(
            "▶ Execute AI Decision",
            width="stretch"
        ):

            result = execute_ai_decision()

            st.session_state.last_ai_execution = result

            # After execution, previous prediction is no
            # longer the current traffic-state prediction.
            st.session_state.ai_recommendations = []

            st.session_state.safe_ai_decision = None

            st.rerun()


# =========================================================
# ML PREDICTIONS
# =========================================================

recommendations = st.session_state.ai_recommendations


if recommendations:

    st.write("### ML Predictions")

    for rec in recommendations:

        # -------------------------------------------------
        # ERROR
        # -------------------------------------------------

        if "error" in rec:

            st.error(
                f"{rec.get('train_id', 'Unknown')}: "
                f"{rec['error']}"
            )

            continue

        # -------------------------------------------------
        # BASIC VALUES
        # -------------------------------------------------

        train_id = rec.get(
            "train_id",
            "Unknown"
        )

        next_section = rec.get(
            "next_section",
            "-"
        )

        action = rec.get(
            "action",
            "-"
        )

        probabilities = rec.get(
            "probabilities",
            {}
        )

        hold_prob = 0.0
        release_prob = 0.0

        if isinstance(probabilities, dict):

            hold_prob = probabilities.get(
                "HOLD",
                0.0
            )

            release_prob = probabilities.get(
                "RELEASE",
                0.0
            )

        try:

            hold_prob = float(
                hold_prob
            )

            release_prob = float(
                release_prob
            )

        except (TypeError, ValueError):

            hold_prob = 0.0
            release_prob = 0.0

        # -------------------------------------------------
        # DISPLAY ACTION
        # -------------------------------------------------

        if action == "RELEASE":

            st.success(
                f"**{train_id} → RELEASE**"
            )

        elif action == "HOLD":

            st.warning(
                f"**{train_id} → HOLD**"
            )

        else:

            st.info(
                f"**{train_id} → {action}**"
            )

        # -------------------------------------------------
        # METRICS
        # -------------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Train",
            train_id
        )

        c2.metric(
            "Next Section",
            next_section
        )

        c3.metric(
            "Release Probability",
            f"{release_prob:.1%}"
        )

        c4.metric(
            "Hold Probability",
            f"{hold_prob:.1%}"
        )

        st.divider()


elif st.session_state.scenario_loaded:

    # Only show this message if the user has explicitly
    # asked the ML model and there were no results.
    pass


# =========================================================
# SAFETY-CHECKED AI DECISION
# =========================================================

safe_decision = st.session_state.safe_ai_decision


if safe_decision:

    st.write("### 🛡️ Safety-Checked AI Decision")

    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    if "error" in safe_decision:

        st.error(
            f"AI controller error: "
            f"{safe_decision['error']}"
        )

    else:

        selected = safe_decision.get(
            "selected_action"
        )

        if selected:

            train_id = selected.get(
                "train_id",
                "-"
            )

            action = selected.get(
                "final_action",
                selected.get(
                    "action",
                    "-"
                )
            )

            next_section = selected.get(
                "next_section",
                "-"
            )

            safe = selected.get(
                "safe",
                True
            )

            reason = selected.get(
                "reason",
                ""
            )

            # -------------------------------------------------
            # FINAL DECISION
            # -------------------------------------------------

            if action == "RELEASE" and safe:

                st.success(
                    f"### ✅ FINAL DECISION: RELEASE {train_id}"
                )

            else:

                st.warning(
                    f"### 🛑 FINAL DECISION: HOLD {train_id}"
                )

            # -------------------------------------------------
            # DECISION INFORMATION
            # -------------------------------------------------

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Train",
                train_id
            )

            c2.metric(
                "Next Section",
                next_section
            )

            c3.metric(
                "Safety",
                "SAFE" if safe else "BLOCKED"
            )

            # -------------------------------------------------
            # REASON
            # -------------------------------------------------

            if reason:

                st.info(
                    f"**Reason:** {reason}"
                )

        else:

            st.info(
                "No eligible train requires a decision "
                "at the current simulation time."
            )


# =========================================================
# LAST AI EXECUTION
# =========================================================

execution = st.session_state.last_ai_execution


if execution:

    st.divider()

    st.subheader("⚡ AI Execution Result")

    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    if "error" in execution:

        st.error(
            f"AI execution error: "
            f"{execution['error']}"
        )

    else:

        selected = execution.get(
            "selected_action"
        )

        if selected:

            train_id = selected.get(
                "train_id",
                "-"
            )

            action = selected.get(
                "final_action",
                selected.get(
                    "action",
                    "-"
                )
            )

            next_section = selected.get(
                "next_section",
                "-"
            )

            safe = selected.get(
                "safe",
                True
            )

            reason = selected.get(
                "reason",
                ""
            )

            # -------------------------------------------------
            # EXECUTION STATUS
            # -------------------------------------------------

            if action == "RELEASE" and safe:

                st.success(
                    f"### 🚆 AI EXECUTED: RELEASE {train_id}"
                )

                st.caption(
                    f"{train_id} was released into "
                    f"{next_section}."
                )

            elif action == "HOLD":

                st.warning(
                    f"### 🛑 AI EXECUTED: HOLD {train_id}"
                )

                st.caption(
                    "The train remains waiting."
                )

            else:

                st.info(
                    f"### AI Action: {action}"
                )

            # -------------------------------------------------
            # EXECUTION DETAILS
            # -------------------------------------------------

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Train",
                train_id
            )

            c2.metric(
                "Action",
                action
            )

            c3.metric(
                "Section",
                next_section
            )

            if reason:

                st.info(
                    f"**Reason:** {reason}"
                )

        else:

            st.info(
                "The AI controller did not select a train "
                "for execution at this time."
            )


# =========================================================
# SIMPLE TRAFFIC SUMMARY
# =========================================================

st.subheader("Traffic Summary")


if simulator.trains:

    total = len(simulator.trains)

    moving = sum(
        1
        for train in simulator.trains.values()
        if train.status == "RUNNING"
    )

    waiting = sum(
        1
        for train in simulator.trains.values()
        if train.status == "WAITING"
    )

    not_entered = sum(
        1
        for train in simulator.trains.values()
        if train.status == "NOT_ENTERED"
    )

    arrived = sum(
        1
        for train in simulator.trains.values()
        if train.status == "ARRIVED"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Total Trains",
        total
    )

    c2.metric(
        "Moving",
        moving
    )

    c3.metric(
        "Waiting",
        waiting
    )

    c4.metric(
        "Not Entered",
        not_entered
    )

    c5.metric(
        "Arrived",
        arrived
    )


# =========================================================
# CURRENT SECTION OCCUPANCY
# =========================================================

st.subheader("Section Occupancy")


if simulator.section_occupancy:

    occupancy_rows = []

    for section_id, train_ids in simulator.section_occupancy.items():

        occupancy_rows.append(
            {
                "Section": section_id,
                "Train(s)": ", ".join(train_ids)
            }
        )

    st.dataframe(
        occupancy_rows,
        width="stretch",
        hide_index=True
    )

else:

    st.write(
        "No sections currently occupied."
    )


# =========================================================
# EVENT LOG
# =========================================================

st.subheader("Event Log")


if simulator.history:

    recent_events = simulator.history[-15:]

    for event in recent_events:

        if isinstance(event, dict):

            time = event.get(
                "time_min",
                event.get(
                    "time",
                    ""
                )
            )

            event_type = event.get(
                "event",
                event.get(
                    "event_type",
                    ""
                )
            )

            train_id = event.get(
                "train_id",
                ""
            )

            st.text(
                f"[{time}] {event_type} {train_id}"
            )

else:

    st.write(
        "No events yet."
    )
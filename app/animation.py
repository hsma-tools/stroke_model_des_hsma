"""
Functions to transform stroke patient event logs into vidigi animations.
"""

import time

import pandas as pd

from vidigi.prep import reshape_for_animations, generate_animation_df
from vidigi.animation import generate_animation
from vidigi.utils import EventPosition, create_event_position_df
import streamlit as st

# Fixed layout describing where each event should appear in the animation
EVENT_POSITION_DF = create_event_position_df(
    [
        EventPosition(event="arrival", x=50, y=875, label="Arrival"),
        EventPosition(
            event="nurse_q_start_time", x=205, y=800, label="Waiting for Nurse"
        ),
        EventPosition(
            event="nurse_triage_start_time",
            x=205,
            y=700,
            resource="number_of_nurses",
            label="Being Triaged by Nurse",
        ),
        EventPosition(
            event="ct_scan_start_time",
            x=205,
            y=600,
            label="Undergoing CT Scan",
        ),
        EventPosition(
            event="ctp_scan_start_time",
            x=405,
            y=600,
            label="Undergoing CTP Scan",
        ),
        EventPosition(
            event="sdec_admit_time",
            x=605,
            y=400,
            resource="sdec_beds",
            label="In SDEC",
        ),
        EventPosition(
            event="ward_q_start_time",
            x=205,
            y=400,
            label="Waiting for Bed\non Main Stroke Ward",
        ),
        EventPosition(
            event="ward_admit_time",
            x=605,
            y=150,
            resource="number_of_ward_beds",
            label="In Stroke Ward",
        ),
        EventPosition(event="depart", x=805, y=100, label="Exit"),
    ]
)


def convert_event_log(patient_df, run=1):
    """
    Convert a wide-format patient event table into a long-format event log.

    Parameters
    ----------
    patient_df : pd.DataFrame
        Wide-format event data with one row per patient per run. Must contain
        a "run" column, time columns (e.g., "clock_start") and resource ID
        columns (e.g., "nurse_attending_id").
    run : int, optional
        Simulation run to extract from `patient_df`. Defaults to 1.

    Returns
    -------
    pd.DataFrame
        Long-format event log with columns including: "id", "time", "event",
        "event_type", and "resource_id" (where applicable).
    """
    # Restrict to the specified simulation run
    run_df = patient_df[patient_df["run"] == run]

    # Keep only the columns required for the animation event log
    cols = [
        "id",
        "patient_diagnosis_type",
        "thrombolysis",
        "admission_avoidance",
        "arrived_ooh",
        "advanced_ct_pathway",
        "clock_start",
        "nurse_q_start_time",
        "nurse_triage_start_time",
        "nurse_triage_end_time",
        "ct_scan_start_time",
        "ct_scan_end_time",
        "ctp_scan_start_time",
        "ctp_scan_end_time",
        "sdec_admit_time",
        "sdec_discharge_time",
        "ward_q_start_time",
        "ward_admit_time",
        "ward_discharge_time",
        "exit_time",
    ]
    times_df = run_df.reindex(columns=cols).copy()

    # For patients with missing exit time, use the latest non-null time in
    # their row
    cols_max = [
        "clock_start",
        "nurse_q_start_time",
        "nurse_triage_start_time",
        "nurse_triage_end_time",
        "ct_scan_start_time",
        "ct_scan_end_time",
        "ctp_scan_start_time",
        "ctp_scan_end_time",
        "sdec_admit_time",
        "sdec_discharge_time",
        "ward_q_start_time",
        "ward_admit_time",
        "ward_discharge_time",
        "exit_time",
    ]
    existing = times_df.columns.intersection(cols_max)
    row_max = times_df[existing].max(axis=1)
    times_df["exit_time"] = times_df["exit_time"].fillna(row_max)

    # Reshape from wide to long: one row per patient per event
    times_df_long = times_df.melt(
        id_vars=[
            "id",
            "patient_diagnosis_type",
            "thrombolysis",
            "admission_avoidance",
            "advanced_ct_pathway",
            "arrived_ooh",
        ]
    ).rename(columns={"variable": "event", "value": "time"})

    # Map time-stamped columns to generic event types for vidigi
    event_map = {
        "clock_start": "arrival_departure",
        "nurse_q_start_time": "queue",
        "nurse_triage_start_time": "resource_use",
        "nurse_triage_end_time": "resource_use_end",
        "ct_scan_start_time": "queue",
        "ct_scan_end_time": "queue",
        "ctp_scan_start_time": "queue",
        "ctp_scan_end_time": "queue",
        "sdec_admit_time": "resource_use",
        "sdec_discharge_time": "resource_use_end",
        "ward_q_start_time": "queue",
        "ward_admit_time": "resource_use",
        "ward_discharge_time": "resource_use_end",
        "exit_time": "arrival_departure",
    }
    times_df_long["event_type"] = times_df_long["event"].apply(lambda x: event_map[x])

    # Extract resource assignments (nurse, SDEC bed, ward bed) per patient
    resource_ids = run_df[["id", "nurse_attending_id", "sdec_bed_id", "ward_bed_id"]]
    resource_ids = resource_ids.melt(id_vars="id", value_name="resource_id")

    # Map resource ID columns to the events where the resource is in use
    resource_mapping_df = pd.DataFrame(
        [
            {"variable": "nurse_attending_id", "event": "nurse_triage_start_time"},
            {"variable": "nurse_attending_id", "event": "nurse_triage_end_time"},
            {"variable": "sdec_bed_id", "event": "sdec_admit_time"},
            {"variable": "sdec_bed_id", "event": "sdec_discharge_time"},
            {"variable": "ward_bed_id", "event": "ward_admit_time"},
            {"variable": "ward_bed_id", "event": "ward_discharge_time"},
        ]
    )

    # Attach resource IDs to the corresponding events
    resource_ids = resource_ids.merge(
        resource_mapping_df, on="variable", how="inner"
    ).drop(columns=["variable"])

    # Combine events and resource IDs, dropping any rows with no timestamp
    event_log = times_df_long.merge(
        resource_ids, on=["id", "event"], how="outer"
    ).dropna(subset="time")

    # Rename start/exit events to match vidigi event position configuration
    event_log["event"] = event_log["event"].replace(
        {"clock_start": "arrival", "exit_time": "depart"}
    )

    return event_log


def create_vidigi_animation(
    event_log,
    scenario,
    event_position_df=EVENT_POSITION_DF,
    snapshot_interval=15,
    step_snapshot_max=100,
    entity_col_name="id",
    gap_between_resource_rows=50,
    gap_between_resources=20,
    limit_duration=None,
):
    """
    Build a vidigi animation figure from an event log and scenario settings.

    Parameters
    ----------
    event_log : pd.DataFrame
        Long-format event log for a single simulation run. Must contain
        "id", "time", "event", and any columns used in `event_position_df`
        (for example, "patient_diagnosis_type").
    scenario : object
        Configuration object with attributes like `warm_up_period`,
        `sim_duration` and `sdec_opening_hour`.
    event_position_df : pd.DataFrame, optional
        Event layout table describing where each event appears in the
        animation. Defaults to `EVENT_POSITION_DF`.
    snapshot_interval : int, optional
        Time between animation snapshots, in simulation time units. Defaults to
        15.
    step_snapshot_max : int, optional
        Maximum number of snapshots to generate. Defaults to 180.
    entity_col_name : str, optional
        Column name for the entity identifier. Defaults to "id".
    gap_between_resource_rows : int, optional
        Vertical spacing between rows of resource icons. Defaults to 50.
    gap_between_resources : int, optional
        Horizontal spacing between distinct resources. Defaults to 20.

    Returns
    -------
    plotly.graph_objs._figure.Figure
        Plotly figure object containing the vidigi animation.
    """
    # Enforce that the event log contains only a single simulation run
    if "run" in event_log.columns:
        if event_log["run"].nunique() > 1:
            raise ValueError(
                f"'run' column has {event_log['run'].nunique()} unique values;"
                f" please pass in a filtered event log with only one run"
            )

    # Calculate warm-up and plotting end times in simulation minutes
    warm_up_threshold = scenario.warm_up_period + (scenario.sdec_opening_hour * 60)

    if limit_duration is None:
        limit_duration = (scenario.sim_duration / 12 / 2) + (
            scenario.sdec_opening_hour * 60
        )
    limit_duration_inc_warmup = limit_duration + scenario.warm_up_period

    print(f"Limit duration: {limit_duration}")

    # Find the latest event for each patient
    latest_event_per_id = (
        event_log.groupby("id", as_index=False)["time"]
        .max()
        .rename(columns={"time": "latest_event_time"})
    )

    print("Last event per ID - first 5 rows")
    print(latest_event_per_id.head())

    # Identify patients whose activity extends beyond the warm-up period
    latest_event_per_id = latest_event_per_id[
        latest_event_per_id["latest_event_time"] >= warm_up_threshold
    ]

    print(
        "Placement dataframe started construction at "
        + f"{time.strftime('%H:%M:%S', time.localtime())}"
    )
    print(f"Before warm-up filtering: {len(event_log)} rows")

    # Exclude patients whose last event occurs before the warm-up period ends
    event_log = event_log[event_log["id"].isin(latest_event_per_id["id"].values)]
    print(f"After warm-up filtering: {len(event_log)} rows")

    # Create snapshot-level entity positions over time
    full_patient_df = reshape_for_animations(
        event_log,
        entity_col_name=entity_col_name,
        limit_duration=limit_duration_inc_warmup,
        every_x_time_units=snapshot_interval,
        step_snapshot_max=step_snapshot_max,
    )

    # Drop snapshots that occur before the warm-up period
    full_patient_df = full_patient_df[
        full_patient_df["snapshot_time"] >= warm_up_threshold
    ]

    print("Full patient df (5 rows)")
    print(full_patient_df.head())
    print(f"Warm-up duration: {warm_up_threshold}")

    # Attach x–y positions and queue/resource layout for animation
    full_patient_df_plus_pos = generate_animation_df(
        full_entity_df=full_patient_df,
        entity_col_name=entity_col_name,
        event_position_df=event_position_df,
        wrap_queues_at=25,
        step_snapshot_max=step_snapshot_max,
        gap_between_entities=15,
        gap_between_queue_rows=30,
        gap_between_resource_rows=gap_between_resource_rows,
        debug_mode=True,
        step_snapshot_limit_gauges=True,
        gap_between_resources=gap_between_resources,
    )
    final_df = full_patient_df_plus_pos.copy()

    # Change icon depending on stroke type
    icon_map = {
        "ICH": "🩸",
        "I": "⌚",
        "TIA": "➡️",
        "Stroke Mimic": "🪞",
        "Non Stroke": "🚷",
    }
    final_df["icon"] = final_df.apply(
        lambda row: icon_map.get(row["patient_diagnosis_type"], row["icon"]),
        axis=1,
    )
    # final_df["icon"] = final_df.apply(
    #     lambda x: x["icon"] + "*" if x["admission_avoidance"] else x["icon"],
    #     axis=1
    # )

    # Build the interactive animation using vidigi
    fig = generate_animation(
        full_entity_df_plus_pos=final_df,
        event_position_df=event_position_df,
        scenario=scenario,
        entity_col_name=entity_col_name,
        plotly_height=700,
        frame_duration=600,
        frame_transition_duration=800,
        plotly_width=1200,
        override_x_max=800,
        override_y_max=900,
        entity_icon_size=20,
        gap_between_resource_rows=gap_between_resource_rows,
        include_play_button=True,
        add_background_image=None,
        display_stage_labels=True,
        time_display_units="day_clock_ampm",
        simulation_time_unit="minutes",
        setup_mode=False,
        debug_mode=True,
        resource_icon_size=15,
        text_size=20,
        # start_time=f"{scenario.sdec_opening_hour}:00:00",
        gap_between_resources=gap_between_resources,
    )

    return fig


@st.fragment
def display_animation(patient_df, scenario_class_instance, limit_duration):

    selected_run = st.selectbox(
        "Select a run",
        options=list(range(1, max(patient_df.run) + 1)),
        index=0,
        key="select_run_animation",
    )

    generate_animation = st.button("Click to generate an animation of the system")

    if generate_animation:
        with st.spinner(
            "Generating Animation (may take up to 5 minutes - please be patient!)",
        ):
            st.markdown("""
🩸 = Intracerebral Haemorrhage (ICH) |
⌚ = Ischaemic Stroke |
➡️ = Transient Ischaemic Attack (TIA) |
🪞 = Stroke Mimic |
🚷 = Non Stroke |
""")
            event_log = convert_event_log(patient_df, run=selected_run)
            return st.plotly_chart(
                create_vidigi_animation(
                    event_log,
                    scenario=scenario_class_instance,
                    limit_duration=limit_duration,
                )
            )

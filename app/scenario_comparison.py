import pandas as pd
import streamlit as st
from stroke_ward_model.metrics import Metrics
from app_utils import iconMetricContainer
import numpy as np

SCENARIO_PARAMS = {
    "sim_duration_days": ("Simulation Duration (days)", "days"),
    "sim_duration_years": ("Simulation Duration (years)", "years"),
    "number_of_ward_beds": ("Number of beds in Ward", "beds"),
    "sdec_beds": ("Number of beds in SDEC", "beds"),
    "start_hour_ctp": ("CTP Opening Hour", "hour"),
    "duration_hours_ctp": ("CTP Duration", "hours"),
    "end_hour_ctp": ("CTP Closing Hour", "hour"),
    "start_hour_sdec": ("SDEC Opening Hour", "hour"),
    "duration_hours_sdec": ("SDEC Duration", "hours"),
    "end_hour_sdec": ("SDEC Closing Hour", "hour"),
    "average_patients_per_run": ("Average Patients per Run", "patients"),
    "min_patients_per_run": ("Min Patients per Run", "patients"),
    "max_patients_per_run": ("Max Patients per Run", "patients"),
    "average_patients_per_year": ("Average Patients per Year", "patients"),
    "average_patients_per_day": ("Average Patients per Day", "patients"),
    "therapy_sdec": ("Therapy available in SDEC?", "True (1)/False (0)"),
    "thrombolysis_los_save": (
        "LoS proportion for thrombolysed patient versus unthrombolysed",
        "proportion",
    ),
    "sdec_dr_cost_min": ("SDEC staffing cost per minute", "£"),
    "sdec_bed_day_saving": (
        "Bed days assumed saved per admission avoidance through SDEC",
        "days",
    ),
    "inpatient_bed_cost": (
        "Cost per saved bed day (admission avoidance via SDEC)",
        "£",
    ),
    "short_term_thrombolysis_savings": (
        "Short-term (LoS-based) thrombolysis savings calculated?",
        "True (1)/False (0)",
    ),
    "inpatient_bed_cost_thrombolysis": (
        "Cost per saved bed day (thrombolysis LoS savings) - only used if looking at short-term thrombolysis savings",
        "£",
    ),
    "fixed_thrombolysis_saving_amount_long_term": (
        "Fixed saving from thrombolysis - only used if looking at long-term thrombolysis savings",
        "£",
    ),
}

# attr: (label, unit, is_key, icon, delta_color)
OUTCOME_PARAMS = {
    "thrombolysis_yearly_save": (
        "Thrombolysis Yearly Saving",
        "£",
        True,
        "e133",
        "normal",
    ),
    "sdec_yearly_save": ("SDEC Yearly Saving", "£", True, "e4d0", "normal"),
    "overall_yearly_save": ("Overall Yearly Saving", "£", True, "f04b", "normal"),
    "extra_throm": ("Additional Thrombolysis", "patients", False, None, "normal"),
    "extra_throm_yearly": (
        "Additional Thrombolysis per Year",
        "patients",
        True,
        "e138",
        "normal",
    ),
    "thrombolysis_rate": (
        "Overall Thrombolysis Rate",
        "patients",
        True,
        "e133",
        "normal",
    ),
    "thrombolysis_rate_without_ctp": (
        "Thrombolysis Rate (excluding patients enabled by CTP scanning)",
        "patients",
        False,
        "e133",
        "normal",
    ),
    "avoid_yearly": ("Admissions Avoided per Year", "patients", True, "e0b6", "normal"),
    "avoid_yearly_min": (
        "Admissions Avoided per Year (Min)",
        "patients",
        False,
        None,
        "normal",
    ),
    "avoid_yearly_max": (
        "Admissions Avoided per Year (Max)",
        "patients",
        False,
        None,
        "normal",
    ),
    "admit_delay_yearly": (
        "Admission Delays per Year",
        "patients",
        True,
        "f38c",
        "inverse",
    ),
    "admit_delay_yearly_min": (
        "Admission Delays per Year (Min)",
        "patients",
        False,
        None,
        "inverse",
    ),
    "admit_delay_yearly_max": (
        "Admission Delays per Year (Max)",
        "patients",
        False,
        None,
        "inverse",
    ),
    "mean_ward_occ": ("Mean Ward Occupancy", "beds", False, "e13c", "inverse"),
    "mean_ward_occ_perc": ("Mean Ward Occupancy (%)", "%", True, "e13c", "inverse"),
    "patients_inside_sdec_operating_hours": (
        "Patients Inside SDEC Hours",
        "patients",
        False,
        "e14b",
        "normal",
    ),
    "patients_inside_sdec_operating_hours_per_year": (
        "Patients Inside SDEC Hours per Year",
        "patients",
        False,
        "e14b",
        "normal",
    ),
    "patients_outside_sdec_operating_hours_per_year": (
        "Patients Outside SDEC Hours per Year",
        "patients",
        True,
        "e14b",
        "inverse",
    ),
    "sdec_full": ("SDEC Full", "patients", False, "e7ef", "inverse"),
    "sdec_full_per_year": ("SDEC Full per Year", "patients", True, "e7ef", "inverse"),
    "sdec_full_min": ("SDEC Full (Min)", "patients", False, "e7ef", "inverse"),
    "sdec_full_per_year_min": (
        "SDEC Full per Year (Min)",
        "patients",
        False,
        "e7ef",
        "inverse",
    ),
    "sdec_full_per_year_max": (
        "SDEC Full per Year (Max)",
        "patients",
        False,
        "e7ef",
        "inverse",
    ),
}

patient_level_metric_choices = {
    "Nurse Queue Time": "q_time_nurse",
    "Ward Queue Time": "q_time_ward",
    "Onset Type": "onset_type",
    "MRS Type": "mrs_type",
    "MRS on Discharge": "mrs_discharge",
    "Diagnosis": "diagnosis",
    "Patient Diagnosis": "patient_diagnosis",
    "Priority": "priority",
    "Non-Admission": "non_admission",
    "Advanced CT Pathway": "advanced_ct_pathway",
    "SDEC Pathway": "sdec_pathway",
    "SDEC Running when Required": "sdec_running_when_required",
    "SDEC Full when Required": "sdec_full_when_required",
    "Thrombolysis": "thrombolysis",
    "Thrombectomy": "thrombectomy",
    "Admission Avoidance": "admission_avoidance",
    "Patient with TIA, stroke mimic or non-stroke not admitted": "non_admitted_tia_ns_sm",
    "Ward LOS": "ward_los",
    "Ward LOS for Thrombolysis Patients": "ward_los_thrombolysis",
    "SDEC LOS": "sdec_los",
    "CTP duration": "ctp_duration",
    "CT duration": "ct_duration",
    "Arrived OOH": "arrived_ooh",
    "Patient Diagnosis Type": "patient_diagnosis_type",
}


@st.fragment
def render_run_manager():
    """
    Display controls to manage saved simulation runs.

    Within an expander, this fragment lists saved runs, allows users to
    select one or more runs to remove, warns if the baseline run is
    selected, and updates `st.session_state.metrics_runs` and
    `st.session_state.baseline_index` accordingly. If no runs have been
    saved yet, the fragment returns without rendering UI.

    Returns
    -------
    None
        The function renders controls directly in the Streamlit app.
    """
    runs = st.session_state.metrics_runs
    if not runs:
        return

    with st.expander("Manage saved runs"):
        labels = [r["label"] for r in runs]
        baseline_label = labels[st.session_state.baseline_index]

        to_remove = st.multiselect(
            "Select runs to remove",
            options=labels,
            format_func=lambda l: f"⭐ {l}" if l == baseline_label else l,
        )

        if to_remove:
            if baseline_label in to_remove:
                st.warning("⚠️ You have selected the current baseline for removal.")

            if st.button(f"🗑️ Remove {len(to_remove)} run(s)", type="primary"):
                st.session_state.metrics_runs = [
                    r for r in runs if r["label"] not in to_remove
                ]

                # Recalculate baseline index - fall back to 0 if baseline was removed
                remaining_labels = [r["label"] for r in st.session_state.metrics_runs]
                if baseline_label in remaining_labels:
                    st.session_state.baseline_index = remaining_labels.index(
                        baseline_label
                    )
                else:
                    st.session_state.baseline_index = 0

                st.toast(f"✅ Removed {len(to_remove)} run(s).")
                st.rerun()


def get_baseline() -> Metrics | None:
    """
    Retrieve the current baseline `Metrics` object from session state.

    The baseline is determined by `st.session_state.baseline_index` and
    is taken from `st.session_state.metrics_runs`. If no runs are stored,
    this function returns `None`.

    Returns
    -------
    stroke_ward_model.metrics.Metrics or None
        The baseline `Metrics` instance, or `None` if no runs exist.
    """
    runs = st.session_state.metrics_runs
    if not runs:
        return None
    return runs[st.session_state.baseline_index]["metrics"]


def build_comparison_df(run, baseline, param_map):
    """
    Build a comparison table for a single run against a baseline.

    The function uses `Metrics.diff` to compute per-metric differences
    between the selected run and the baseline, and returns a tidy
    `pandas.DataFrame` suitable for display in Streamlit.

    Parameters
    ----------
    run : dict
        A run entry from `st.session_state.metrics_runs` containing a
        "metrics" key whose value supports `.diff(baseline)`.
    baseline : stroke_ward_model.metrics.Metrics
        Baseline metrics object used as the reference in the comparison.
    param_map : dict
        Mapping from metric attribute names to tuples of the form
        `(label, unit, ...)`. Only attributes present both in
        `param_map` and in the diff result are included.

    Returns
    -------
    pandas.DataFrame
        Data frame with columns "Metric", "Unit",
        "Chosen Baseline", "Comparison Scenario" and
        "Difference".
    """
    diffs = run["metrics"].diff(baseline)
    rows = []
    for attr, (label, unit, *_) in param_map.items():
        if attr not in diffs:
            continue
        d = diffs[attr]
        rows.append(
            {
                "Metric": label,
                "Unit": unit,
                "Chosen Baseline": round(d["other"], 1),
                "Comparison Scenario": round(d["self"], 1),
                "Difference": round(d["difference"], 1),
            }
        )
    return pd.DataFrame(rows)  # no .set_index("Metric")


def style_difference_column(df: pd.DataFrame):
    """
    Style the "Difference" column of a comparison DataFrame.

    Positive differences are coloured green, negative differences red,
    and zero or non-numeric values use the default styling.

    Parameters
    ----------
    df : pandas.DataFrame
        Data frame produced by `build_comparison_df` with a
        "Difference" column.

    Returns
    -------
    pandas.io.formats.style.Styler
        A Styler object with conditional colouring applied to the
        "Difference" column.
    """
    def colour(val):
        if not isinstance(val, (int, float)):
            return ""
        if val > 0:
            return "color: green"
        if val < 0:
            return "color: red"
        return ""

    return df.style.map(colour, subset=["Difference"])


def render_key_metric_cards(run, baseline):
    """
    Render key outcome metrics for a run as Streamlit metric cards.

    This function compares the given run to the baseline using
    `Metrics.diff`, selects metrics flagged as key in `OUTCOME_PARAMS`,
    formats values and deltas (with special handling for currency), and
    displays them as three-column cards with icons and coloured deltas.

    Parameters
    ----------
    run : dict
        A run entry from `st.session_state.metrics_runs` containing a
        "label" and a "metrics" object that supports `.diff`.
    baseline : stroke_ward_model.metrics.Metrics
        Baseline metrics object used as the reference for deltas.

    Returns
    -------
    None
        The function renders metric cards directly in the Streamlit app.
    """
    diffs = run["metrics"].diff(baseline)
    key_metrics = {
        attr: val
        for attr, val in OUTCOME_PARAMS.items()
        if val[2]  # is_key == True
    }

    cols = st.columns(3)
    for idx, (attr, (label, unit, _, icon, delta_color)) in enumerate(
        key_metrics.items()
    ):
        if attr not in diffs:
            continue

        d = diffs[attr]
        formatted_val = (
            f"£{d['self']:,.1f}" if unit == "£" else f"{d['self']:,.1f} {unit}"
        )
        formatted_delta = (
            f"£{d['difference']:+,.1f}"
            if unit == "£"
            else f"{d['difference']:+,.1f} {unit}"
        )

        with cols[idx % 3]:
            with iconMetricContainer(
                key=f"metric_card_{attr}_{run['label']}",
                icon_unicode=icon,
                family="outline",
                icon_color="black",
                type="symbols",
            ):
                st.metric(
                    label=label,
                    value=formatted_val,
                    delta=formatted_delta,
                    delta_color=delta_color,
                    border=True,
                )


def render_full_comparison_table():
    """
    Render a full comparison table of scenario parameters and outcomes.

    For each metric defined in `SCENARIO_PARAMS` and `OUTCOME_PARAMS`,
    this function extracts values from every saved run, assembles them into
    a multi-indexed `pandas.DataFrame` (indexed by metric and unit), and
    displays the table with one column per run.

    Returns
    -------
    None
        The function renders a data table directly in the Streamlit app.
    """
    runs = st.session_state.metrics_runs
    if not runs:
        st.info("No runs saved yet.")
        return

    rows = []

    for attr, (label, unit, *_) in {**SCENARIO_PARAMS, **OUTCOME_PARAMS}.items():
        row = {"Metric": label, "Unit": unit}
        for run in runs:
            metrics = run["metrics"]
            val = (
                getattr(metrics, attr, None)
                if isinstance(metrics, Metrics)
                else metrics.values.get(attr)
            )
            val
            row[run["label"]] = (
                round(float(val), 1)
                if val is not None and not (isinstance(val, float) and np.isnan(val))
                else None
            )
        rows.append(row)

    df = pd.DataFrame(rows).set_index(["Metric", "Unit"])
    st.dataframe(df, width="stretch")


@st.fragment
def render_scenario_manager():
    """
    Display an interface to select a baseline run and compare scenarios.

    This fragment renders a summary table across all runs, allows users to
    choose a baseline run, and for each non-baseline run displays key
    metric cards plus separate comparison tables for scenario parameters
    and outcomes. If there are fewer than two runs, it shows an informative
    message instead.

    Returns
    -------
    None
        The function renders controls, metric cards and tables directly in
        the Streamlit app.
    """
    runs = st.session_state.metrics_runs

    if not runs:
        st.info("No runs saved yet. Run a simulation to get started.")
        return

    elif len(runs) == 1:
        st.info(
            "Only one run has been completed. Please run an additional simulation to use this tab."
        )
        return

    labels = [r["label"] for r in runs]

    with st.expander("Click to view a full summary table of all runs"):
        render_full_comparison_table()

    st.session_state.baseline_index = st.radio(
        "Baseline run",
        options=range(len(runs)),
        format_func=lambda i: f"{labels[i]}",
        index=st.session_state.baseline_index,
    )

    baseline = get_baseline()

    for i, run in enumerate(runs):
        if i == st.session_state.baseline_index:
            continue

        baseline_label = runs[st.session_state.baseline_index]["label"]
        st.subheader(f"{run['label']} :grey[vs] {baseline_label}")

        render_key_metric_cards(run, baseline)

        with st.expander("Scenario Parameters", expanded=False):
            param_df = build_comparison_df(run, baseline, SCENARIO_PARAMS)
            st.dataframe(style_difference_column(param_df), width="stretch")

        with st.expander("Outcomes", expanded=False):
            outcome_df = build_comparison_df(run, baseline, OUTCOME_PARAMS)
            st.dataframe(style_difference_column(outcome_df), width="stretch")

        st.divider()

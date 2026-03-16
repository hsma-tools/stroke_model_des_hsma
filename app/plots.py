"""
Create occupancy plot.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from vidigi.process_mapping import add_sim_timestamp, discover_dfg, dfg_to_graphviz

from animation import convert_event_log

from stroke_ward_model.plots import TrialPlots


def plot_occupancy(
    occupancy_df,
    total_sim_duration_days,
    warm_up_duration_days,
    plot_confidence_intervals=False,
):
    """
    Plot occupancy over time, optionally with confidence bands.

    Parameters
    ----------
    occ_df : pd.DataFrame
        Data frame with columns "Time" (minutes), "Occupancy", and "run".
    total_sim_days : float
        Total simulation duration in days.
    warm_up_days : float
        Warm-up duration in days; shown as a vertical line.
    plot_confidence_intervals : bool, optional
        If True, plot median and quantile bands across runs.
        If False, plot individual runs plus mean and rolling mean.

    Returns
    -------
    plotly.graph_objects.Figure
        Plotly figure showing occupancy trajectories.
    """
    # Convert from minutes to days
    occupancy_df["Days"] = occupancy_df["Time"] / 60 / 24

    # Define regular grid
    grid_days = np.arange(
        0,
        total_sim_duration_days,
        1 / 24,  # hourly
    )

    # Resample each run to the common grid (step-wise, ffill)
    resampled = []
    for run, g in occupancy_df.sort_values("Days").groupby("run"):
        g = g.set_index("Days")[["Occupancy"]]
        g = g.reindex(grid_days, method="ffill")
        g["run"] = run
        g = g.reset_index(names="Days")
        resampled.append(g)

    grid_df = pd.concat(resampled, ignore_index=True)

    # Mean occupancy across runs on the grid
    mean_df = grid_df.groupby("Days", as_index=False)["Occupancy"].mean()

    if plot_confidence_intervals:
        # Summary quantiles across runs at each time point
        summary_df = (
            grid_df.groupby("Days")["Occupancy"]
            .agg(
                min="min",
                p10=lambda x: x.quantile(0.1),
                p25=lambda x: x.quantile(0.25),
                median="median",
                p75=lambda x: x.quantile(0.75),
                p90=lambda x: x.quantile(0.9),
                max="max",
            )
            .reset_index()
        )

        occupancy_fig = go.Figure()

        # Min-max band (lightest)
        occupancy_fig.add_trace(
            go.Scatter(
                x=summary_df["Days"],
                y=summary_df["max"],
                mode="lines",
                line={"width": 0},
                line_shape="hv",
                showlegend=False,
            )
        )

        occupancy_fig.add_trace(
            go.Scatter(
                x=summary_df["Days"],
                y=summary_df["min"],
                mode="lines",
                line={"width": 0},
                line_shape="hv",
                fill="tonexty",
                name="Min–Max",
                fillcolor="rgba(0, 100, 200, 0.15)",
            )
        )

        # 10-90% band
        occupancy_fig.add_trace(
            go.Scatter(
                x=summary_df["Days"],
                y=summary_df["p90"],
                mode="lines",
                line={"width": 0},
                line_shape="hv",
                showlegend=False,
            )
        )

        occupancy_fig.add_trace(
            go.Scatter(
                x=summary_df["Days"],
                y=summary_df["p10"],
                mode="lines",
                line={"width": 0},
                line_shape="hv",
                fill="tonexty",
                name="10–90%",
                fillcolor="rgba(0, 100, 200, 0.35)",
            )
        )

        # 25=75% band (darkest)
        occupancy_fig.add_trace(
            go.Scatter(
                x=summary_df["Days"],
                y=summary_df["p75"],
                mode="lines",
                line={"width": 0},
                line_shape="hv",
                showlegend=False,
            )
        )

        occupancy_fig.add_trace(
            go.Scatter(
                x=summary_df["Days"],
                y=summary_df["p25"],
                mode="lines",
                line={"width": 0},
                line_shape="hv",
                fill="tonexty",
                name="25–75%",
                fillcolor="rgba(0, 100, 200, 0.6)",
            )
        )

        # Median line
        occupancy_fig.add_trace(
            go.Scatter(
                x=summary_df["Days"],
                y=summary_df["median"],
                mode="lines",
                line_shape="hv",
                name="Median",
                line={"width": 1.5, "color": "black"},
            )
        )

        occupancy_fig.update_layout(
            xaxis_title="Days",
            yaxis_title="Occupancy",
        )

    else:
        # Rolling mean of mean occupancy (7-day window)
        mean_df["rolling_mean_7"] = (
            mean_df["Occupancy"].rolling(window=7, center=True).mean()
        )

        # Create a line plot with one line per run
        occupancy_fig = px.line(occupancy_df, x="Days", y="Occupancy", color="run")
        occupancy_fig.update_traces(opacity=0.3)

        # Add mean line across runs
        occupancy_fig.add_scatter(
            x=mean_df["Days"],
            y=mean_df["Occupancy"],
            mode="lines",
            name="Mean across runs",
            line={"width": 2, "color": "black"},
        )

        # Add rolling mean line
        occupancy_fig.add_scatter(
            x=mean_df["Days"],
            y=mean_df["rolling_mean_7"],
            mode="lines",
            name="7-day rolling mean",
            line={"width": 1, "color": "green"},
        )

    # Mark warm-up period end
    occupancy_fig.add_vline(
        x=warm_up_duration_days,
        line_width=3,
        line_dash="dash",
        line_color="red",
    )

    return occupancy_fig


@st.fragment
def plot_dfg_per_feature(split_vars, patient_df):
    """
    Plot directly-follows graphs (DFGs) optionally faceted by up to two
    patient-level variables.

    Parameters
    ----------
    split_vars : dict
        Mapping from user-facing facet labels to column names in `patient_df`.
    patient_df : pandas.DataFrame
        Patient-level table containing the variables that can be used for
        faceting.

    Returns
    -------
    None
        The function renders DFG images directly in the
        Streamlit app.
    """
    # Choose an optional faceting variable
    selected_facet_var = st.selectbox(
        "Select a metric to facet the values by",
        options=[None] + list(split_vars.keys()),
        key="selected_facet_var_dfg",
    )

    # Choose an optional second faceting variable (rows)
    second_facet_options = [None] + [
        k for k in split_vars.keys() if k != selected_facet_var
    ]
    selected_facet_var_2 = st.selectbox(
        "Select a second metric to facet by (rows)",
        options=second_facet_options,
        key="selected_facet_var_2_dfg",
    )

    selected_run = st.selectbox(
        "Select a run", options=list(range(1, max(patient_df.run) + 1)), index=0
    )

    # Choose the time display label for the DFG
    time_format = st.radio(
        "Time Format",
        ["Display in Minutes", "Display in Hours", "Display in Days"],
    )

    if time_format == "Display in Minutes":
        unit = "minutes"
    elif time_format == "Display in Hours":
        unit = "hours"
    elif time_format == "Display in Days":
        unit = "days"

    def _render_dfg(container, df, run, unit, title=None):
        """Build and render a single DFG into `container`."""
        event_log = convert_event_log(df, run=run)
        event_log["event"] = event_log["event"].apply(
            lambda x: x.replace("_time", "").replace("_", " ")
        )
        event_log = add_sim_timestamp(event_log, time_unit="minutes")
        nodes, edges = discover_dfg(event_log, case_col="id", time_unit=unit)

        if len(edges) == 0:
            container.write(
                f"No process map could be generated: no directly-follows relationships in this subgroup ({title})."
            )
            return

        container.image(
            dfg_to_graphviz(
                nodes,
                edges,
                return_image=True,
                size=[8, 4],
                dpi=500,
                direction="TD",
                time_unit=unit,
                title=title,
            )
        )

    def _render_facet_row(df_row, run, unit, facet_col=None, facet_label_prefix=""):
        if facet_col is None:
            _render_dfg(st, df_row, run, unit)
        else:
            facet_values = sorted(
                df_row[facet_col].unique(), key=lambda x: (x is None, x)
            )  # <-- sort here
            if len(facet_values) > 3:
                containers = st.tabs([str(v) for v in facet_values])
            else:
                containers = st.columns(len(facet_values))

            for container, val in zip(containers, facet_values):
                df_sub = df_row[df_row[facet_col] == val]
                title = f"{facet_label_prefix}{facet_col}: {val}"
                _render_dfg(container, df_sub, run, unit, title=title)

    # --- Rendering ---
    if selected_facet_var is None:
        # No faceting at all — single DFG
        _render_dfg(st, patient_df, selected_run, unit)

    elif selected_facet_var_2 is None:
        # Single facet level (original behaviour)
        facet_col = split_vars[selected_facet_var]
        _render_facet_row(patient_df, selected_run, unit, facet_col=facet_col)

    else:
        # Two facet levels: second variable → rows, first variable → tabs/columns
        facet_col_1 = split_vars[selected_facet_var_2]  # rows
        facet_col_2 = split_vars[selected_facet_var]  # columns

        for row_val in sorted(
            patient_df[facet_col_1].unique(), key=lambda x: (x is None, x)
        ):
            st.subheader(f"{selected_facet_var_2}: {row_val}")
            df_row = patient_df[patient_df[facet_col_1] == row_val]
            _render_facet_row(
                df_row,
                selected_run,
                unit,
                facet_col=facet_col_2,
                facet_label_prefix=f"{selected_facet_var_2}: {row_val} | ",
            )
            st.divider()


@st.fragment
def generate_occupancy_plots(my_trial, warm_up_duration_days, sim_duration_days):
    """
    Display ward and SDEC occupancy plots and related result tables.

    Parameters
    ----------
    my_trial : object
        Trial object containing simulation results, including
        attributes such as `ward_occupancy_df`,
        `sdec_occupancy_df`, ``df_trial_results` and
        `trial_patient_df`.
    warm_up_duration_days : float
        Warm-up duration in days. Used both for plotting and
        to mark the end of the warm-up on the occupancy plots.
    sim_duration_days : float
        Main simulation duration in days (excluding warm-up).

    Returns
    -------
    None
        The function renders Plotly charts and data tables
        directly in the Streamlit app.
    """
    # Toggle whether to show quantile bands around occupancy
    conf_intervals = st.toggle("Show Confidence Intervals", value=True)

    st.subheader("Ward Occupancy Over Time")
    ward_occupancy_fig = plot_occupancy(
        occupancy_df=my_trial.ward_occupancy_df,
        total_sim_duration_days=(warm_up_duration_days + sim_duration_days),
        warm_up_duration_days=warm_up_duration_days,
        plot_confidence_intervals=conf_intervals,
    )
    st.plotly_chart(ward_occupancy_fig)

    st.subheader("SDEC Occupancy Over Time")
    sdec_occupancy_fig = plot_occupancy(
        occupancy_df=my_trial.sdec_occupancy_df,
        total_sim_duration_days=(warm_up_duration_days + sim_duration_days),
        warm_up_duration_days=warm_up_duration_days,
        plot_confidence_intervals=conf_intervals,
    )
    st.plotly_chart(sdec_occupancy_fig)

    # Detailed tabular outputs below the plots
    with st.expander("Click to view detailed result tables"):
        st.subheader("Full Per-Run Results for Trial")
        st.dataframe(my_trial.df_trial_results.T)

        st.subheader("Full Per-Patient Results for Trial (Including Warm-Up)")
        st.caption("These values are drawn from patient objects")
        st.dataframe(my_trial.trial_patient_df)

        st.subheader("Recorded Per-Patient Results for Trial (Excluding Warm-Up)")
        st.caption(
            "These values are recorded to the results dataframe tracking each patient"
        )
        st.dataframe(my_trial.trial_results_df)

        st.subheader("Ward Occupancy Audits")
        st.dataframe(my_trial.ward_occupancy_df)

        st.subheader("SDEC Occupancy Audits")
        st.dataframe(my_trial.sdec_occupancy_df)


@st.fragment
def plot_time_heatmap(patient_df, time_vars):
    time_col_pretty = st.selectbox(
        "Select a time variable to visualise", options=time_vars
    )

    time_col = time_vars[time_col_pretty]
    df = add_sim_timestamp(patient_df, time_col=time_col, time_unit="minutes")

    # 1. Extract the hour
    df[f"{time_col}_hour"] = df["timestamp"].apply(lambda x: x.hour)

    # 2. Get counts and reindex to include all hours (0-23)
    counts_series = df[f"{time_col}_hour"].value_counts()

    # This ensures 0 through 23 are all present, filling missing hours with 0
    full_hours_range = range(24)
    counts_by_hour = (
        counts_series.reindex(full_hours_range, fill_value=0).sort_index().reset_index()
    )
    counts_by_hour.columns = [f"{time_col}_hour", "count"]

    fig = go.Figure(
        data=go.Heatmap(
            z=[counts_by_hour["count"].values],
            x=counts_by_hour[f"{time_col}_hour"].values,
            y=["All"],
            colorscale="Blues",
            hoverongaps=False,
            xgap=3,
        )
    )

    fig.update_layout(
        title=f"{time_col_pretty} Heatmap by Hour",
        xaxis_title="Hour of Day",
        yaxis=dict(showticklabels=False),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(24)),
            ticktext=[f"{h}:00" for h in range(24)],  # Optional: prettier labels
        ),
    )

    return st.plotly_chart(fig)


@st.fragment
def plot_histogram(
    patient_df,
    patient_level_metric_choices,
    split_vars,
):
    patient_level_metric_selected = st.multiselect(
        "Select a metric to view the distribution of",
        options=list(patient_level_metric_choices.keys()),
    )

    selected_values = ["id", "run"] + [
        patient_level_metric_choices[k]
        for k in patient_level_metric_selected
        if k in patient_level_metric_choices
    ]

    selected_facet_var = st.selectbox(
        "Select a metric to facet the values by",
        options=[None] + list(split_vars.keys()),
    )

    normalise_los_to_days = st.toggle("Change LOS from Minutes to Days?")

    if selected_facet_var is not None:
        selected_facet_value = split_vars[selected_facet_var]
    else:
        selected_facet_value = None

    if selected_facet_var is not None:
        df = (
            patient_df[[selected_facet_value] + selected_values]
            .melt(id_vars=["id", "run", selected_facet_value])
            .copy()
        )
        if normalise_los_to_days:
            df["value"] = df["value"] / 60 / 24
        st.plotly_chart(
            px.histogram(
                data_frame=df,
                x="value",
                facet_row=selected_facet_value,
                facet_col="variable",
                # Scale plot with number of variables
                height=200 * len(df[selected_facet_value].unique()),
            )
        )

    else:
        df = patient_df[selected_values].melt(id_vars=["id", "run"]).copy()
        if normalise_los_to_days:
            df["value"] = df["value"] / 60 / 24
        st.plotly_chart(
            px.histogram(
                data_frame=df,
                x="value",
                facet_col="variable",
            )
        )


@st.fragment
def plot_arrivals_per_day_histogram(trial_object):

    st.subheader("Arrivals Per Day")

    selected_run = st.selectbox(
        "Select a run",
        options=list(range(1, max(trial_object.trial_patient_df.run) + 1)),
        index=0,
        key="run_select_arrivals_per_day_histogram",
    )

    trial_plots = TrialPlots(trial_object=trial_object)
    results = trial_plots.plot_arrivals_per_day(run=selected_run)

    st.plotly_chart(results["histogram"])

    st.plotly_chart(results["timeseries"])

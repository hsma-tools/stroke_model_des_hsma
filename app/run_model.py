"""
Page for users to choose parameters, run the model and view results.
"""

# External imports
import streamlit as st
import pandas as pd
import plotly.express as px

# Model imports
from stroke_ward_model.inputs import g
from stroke_ward_model.trial import Trial
from stroke_ward_model.metrics import Metrics

# App imports
from app_utils import (
    iconMetricContainer,
    save_run,
    render_state_io,
    time_vars,
    split_vars,
    refresh_runs_display,
)

from scenario_comparison import (
    render_scenario_manager,
    patient_level_metric_choices,
    render_run_manager,
)

from convert_event_log import convert_event_log, create_vidigi_animation

from plots import (
    plot_dfg_per_feature,
    generate_occupancy_plots,
    plot_histogram,
    plot_time_heatmap,
)


st.set_page_config(layout="wide", initial_sidebar_state="expanded")

st.logo("app/resources/nhs-logo-colour.png", size="large")

with open("app/resources/style.css") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

# --- Initialise state ---
if "metrics_runs" not in st.session_state:
    st.session_state.metrics_runs = []  # list of {"label": str, "metrics": Metrics}
if "baseline_index" not in st.session_state:
    st.session_state.baseline_index = 0

g.gen_graph = True


#########################
# MARK: Inputs          #
#########################
with st.sidebar:
    st.subheader("Stroke Ward Configuration")

    number_of_triage_nurses = st.slider(
        "Choose the number of nurses available for triage", 0, 10, 2
    )

    g.number_of_nurses = number_of_triage_nurses

    therapy_sdec = st.toggle(
        "Toggle whether the SDEC will run with full therapy support",
        help="""
Off = no therapy support.

If therapy support enabled, patients with a higher
 level of disability will be eligible for admission avoidance via SDEC (maximum
 MRS of 3 rather than 2 without therapy).

 Therapy incurs no cost in the model as
 the number of patients seen does not change - the point in their journey and
 location of where they are seen is the only thing changing.
        """,
    )
    g.therapy_sdec = therapy_sdec

    number_of_sdec_beds = st.slider(
        "Choose the number of beds available in the SDEC", 0, 20, 5
    )
    g.sdec_beds = number_of_sdec_beds

    number_of_ward_beds = st.slider(
        "Choose the number of beds available in the ward", 10, 100, 49
    )
    g.number_of_ward_beds = number_of_ward_beds

    st.caption(
        f"Total number of beds available: {number_of_ward_beds + number_of_sdec_beds}"
    )

    st.divider()
    ###############################
    # MARK: Opening Time params   #
    ###############################
    st.subheader("Opening Hours")

    set_opening_hours_as_perc = st.toggle(
        "Set the opening hours as a percentage of a day?"
    )

    if set_opening_hours_as_perc:
        sdec_unaval_perc = st.number_input(
            "What percentage of the day should the SDEC be available? (0-100)",
            min_value=0,
            max_value=100,
            value=33,
        )

        st.caption(
            f"""
This equates to the SDEC being open roughly {24 / 100 * sdec_unaval_perc:.1f}
hours a day
            """
        )

        ctp_unaval_perc = st.number_input(
            """
What percentage of the day should the CT Perfusion Scanner (CTP) be available?
(0-100)
            """,
            min_value=0.0,
            max_value=100.0,
            value=33.3,
        )

        st.caption(
            f"""
This equates to the CT perfusion scanner being available roughly
{24 / 100 * sdec_unaval_perc:.1f} hours a day
            """
        )

    else:
        sdec_avail_hours = st.slider(
            "How many hours a day should the SDEC be available?",
            0.0,
            24.0,
            12.0,
            step=0.25,
        )

        st.caption(f"The SDEC is available {sdec_avail_hours / 24.0:.1%} of the time")

        sdec_open_time = st.time_input(
            "What time should the SDEC be open from?", value="08:00", step=60 * 60
        )
        g.sdec_opening_hour = sdec_open_time.hour

        sdec_unaval_perc = ((24.0 - sdec_avail_hours) / 24.0) * 100

        ctp_avail_hours = st.slider(
            """
How many hours a day should the CT perfusion scanner be available?
            """,
            0.0,
            24.0,
            8.0,
            step=0.25,
        )

        st.caption(
            f"""
The CTP perfusion scanner is available {ctp_avail_hours / 24.0:.1%} of the time
            """
        )

        ctp_open_time = st.time_input(
            "What time should the CTP scanner be open from?",
            value="09:00",
            step=60 * 60,
        )

        g.ctp_opening_hour = ctp_open_time.hour

        ctp_unaval_perc = ((24.0 - ctp_avail_hours) / 24.0) * 100

    sdec_available_perc = 100.0 - sdec_unaval_perc
    ctp_available_perc = 100.0 - ctp_unaval_perc

    if sdec_available_perc <= 100 and sdec_available_perc >= 0:
        g.sdec_value = sdec_available_perc
        g.sdec_unav_freq = 1440 * (sdec_available_perc / 100)
        g.sdec_unav_time = 1440 - g.sdec_unav_freq
    elif sdec_available_perc == 100:
        g.sdec_value = sdec_available_perc
        g.sdec_unav_freq = g.sim_duration * 2
        g.sdec_unav_time = 0

    if ctp_available_perc <= 100 and ctp_available_perc >= 0:
        g.ctp_value = ctp_available_perc
        g.ctp_unav_freq = 1440 * (ctp_available_perc / 100)
        g.ctp_unav_time = 1440 - g.ctp_unav_freq
    elif ctp_available_perc == 100:
        g.ctp_value = ctp_available_perc
        g.ctp_unav_freq = g.sim_duration * 2
        g.ctp_unav_time = 0

    st.divider()

    ###############################
    # MARK: Demand params         #
    ###############################
    st.subheader("Demand")

    in_hours_demand_start = st.time_input(
        "What time does your in-hours demand start?", "07:00", step=60 * 60
    )

    g.in_hours_start = in_hours_demand_start.hour

    in_hours_mean_iat = st.number_input(
        """
What is the current average time (in minutes) between arrivals at the unit
in-hours?
        """,
        min_value=1.0,
        max_value=5000.0,
        value=200.0,
    )

    out_of_hours_demand_start = st.time_input(
        "What time does your out-of-hours demand start?", "00:00", step=60 * 60
    )

    g.ooh_start = out_of_hours_demand_start.hour

    out_of_hours_mean_iat = st.number_input(
        """
What is the current average time (in minutes) between arrivals at the unit
out-of-hours?
        """,
        min_value=1.0,
        max_value=5000.0,
        value=666.67,
    )

    # Calculate shift durations (handling midnight wrap-around)
    # This assumes 'In-Hours' lasts until 'OOH' starts
    in_hours_duration = (
        out_of_hours_demand_start.hour - in_hours_demand_start.hour
    ) % 24
    ooh_duration = 24 - in_hours_duration

    # Apply upscale to the Inter-Arrival Times for the model
    g.in_hours_start = in_hours_demand_start.hour
    g.ooh_start = out_of_hours_demand_start.hour

    upscale_pct = st.slider(
        "Upscale demand by percentage (%)",
        min_value=0,
        max_value=100,
        value=0,
        help="Reduces inter-arrival time to increase total patient volume.",
    )
    upscale_factor = 1 + (upscale_pct / 100)

    g.patient_inter_day = in_hours_mean_iat / upscale_factor
    g.patient_inter_night = out_of_hours_mean_iat / upscale_factor
    if upscale_factor != 1:
        st.caption(f"The new in-hours IAT is {g.patient_inter_day:.1f}")
        st.caption(f"The new out-of-hours IAT is {g.patient_inter_night:.1f}")

    # Calculate Annual Volumes for display
    # Formula: (60 / Adjusted IAT) * Hours per day * 365.25
    annual_in = (60 / g.patient_inter_day) * in_hours_duration * 365.25
    annual_out = (60 / g.patient_inter_night) * ooh_duration * 365.25
    total_annual = annual_in + annual_out

    # 4. Display Summary to User
    st.info(
        f"**Estimated Annual Volume:** {int(total_annual):,} arrivals per year"
        f" ({int(annual_in):,} In-Hours, {int(annual_out):,} Out-of-Hours)"
    )

    st.divider()

    ###############################
    # MARK: Advanced model params #
    ###############################
    st.subheader("Model Parameters (ADVANCED)")

    g.number_of_runs = st.number_input(
        "Number of Runs", min_value=1, max_value=100, value=10
    )

    # TODO: Are people likely to want to simulate partial years?
    # Could switch to number of years slider instead if not for ease.
    sim_duration_days = st.slider(
        "Number of days to simulate", 180, 365 * 5, value=365, step=5
    )
    sim_duration_minutes = sim_duration_days * 24 * 60

    g.sim_duration = sim_duration_minutes

    st.caption(
        f"""
You are simulating {(sim_duration_days // 365)}
year{"" if sim_duration_days // 365 == 1 else "s"} and
{sim_duration_days % 365} days
        """
    )

    warm_up_duration_days = st.slider(
        "Number of days to warm-up",
        30,
        180,
        value=90,
        step=5,
        help="""
This is how long the model will run for before starting to record results.
Warming up is recommended so that metrics aren't skewed by the ward starting
empty, which is an unrealistic sitution.\n\nYou can use the 'Occupancy Over
Time' graph to help assess whether your warm-up duration is appropriate.
        """,
    )
    warm_up_duration_minutes = warm_up_duration_days * 24 * 60

    g.warm_up_period = warm_up_duration_minutes

    debug_console = st.toggle("Turn on Debugging Console Messages", value=False)

    g.show_trace = debug_console

    master_seed = st.number_input(
        "Set the master seed",
        value=42,
        min_value=1,
        max_value=None,
        step=1,
        help="""
This parameter affects the random numbers used. Controlled random number
generation is used for inter-arrival times, activity times, and patient
attribute allocation.<br/><br/><b>It is recommended to keep the seed the same
when trying out different scenarios.</b>
        """,
    )

    g.master_seed = master_seed

    #####################
    # MARK: Run Model   #
    #####################

render_state_io()


new_run_tab, scenario_comparison_tab = st.tabs(
    ["Run a New Scenario", "Compare Scenarios"]
)


with new_run_tab:
    run_col_1, run_col_spacing, run_col_2 = st.columns([0.35, 0.15, 0.5])

    with run_col_1:
        st.subheader("Run a new scenario")

        existing_labels = [r["label"] for r in st.session_state.get("metrics_runs", [])]

        run_label = st.text_input(
            "Label this run", placeholder="e.g. 'Baseline' or 'Increased SDEC capacity'"
        )

        label_missing = run_label.strip() == ""
        label_duplicate = run_label.strip() in existing_labels

        if label_missing:
            st.caption("⚠️ Please enter a label before running.")
        elif label_duplicate:
            st.caption(
                f"⚠️ A run named '{run_label}' already exists. Please choose a unique label."
            )

        button_run_pressed = st.button(
            "Run simulation", disabled=label_missing or label_duplicate, type="primary"
        )

    if button_run_pressed:
        with st.spinner("Running Model - Please Wait", show_time=True):
            # Create an instance of the Trial class
            my_trial = Trial()

            # Call the run_trial method of our Trial object
            my_trial.run_trial()

            metrics = Metrics(
                g=g(),
                patient_df_including_warmup=my_trial.trial_patient_df,
                df_trial_results=my_trial.df_trial_results,
            )

            save_run(metrics, label=run_label or None)

            # st.write(my_trial.trial_info)

            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                [
                    "Overview",
                    "Output Graphs",
                    "Process Maps",
                    "Model Exploration",
                    "Animation",
                ]
            )

            ############################
            # MARK: Summary statistics #
            ############################
            with tab1:
                st.subheader("Configuration")

                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    with iconMetricContainer(
                        key="ctp_avail",
                        icon_unicode="ea4a",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="CTP scanners",
                            value="Yes" if g.number_of_ctp > 0 else "No",
                            border=True,
                        )

                        st.caption(
                            f"""
    Available from {metrics.start_hour_ctp:g}:00-{metrics.end_hour_ctp:g}:00 ({metrics.duration_hours_ctp:g}h)
                            """
                        )

                with col2:
                    with iconMetricContainer(
                        key="sdec_beds",
                        icon_unicode="e4d0",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label=f"SDEC beds",
                            value=g.sdec_beds,
                            border=True,
                        )

                        if g.sdec_beds > 0:
                            st.caption(
                                f"""
    Available from {metrics.start_hour_sdec:g}:00-{metrics.end_hour_sdec:g}:00 ({metrics.duration_hours_sdec:g}h)
                                """
                            )
                        else:
                            st.caption("")

                with col3:
                    with iconMetricContainer(
                        key="sdec_therapy",
                        icon_unicode="f2c2",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="SDEC Therapy",
                            value="Yes" if g.therapy_sdec else "No",
                            border=True,
                        )

                        # Blank lines for spacing
                        st.caption("")

                with col4:
                    with iconMetricContainer(
                        key="ward_bed_count",
                        icon_unicode="ea48",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Standard Ward Beds",
                            value=f"{g.number_of_ward_beds}",
                            border=True,
                        )

                        # Blank lines for spacing
                        st.caption("")

                with col5:
                    with iconMetricContainer(
                        key="triage_nurse_count",
                        icon_unicode="f5a3",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Triage Nurses",
                            value=f"{g.number_of_nurses}",
                            border=True,
                        )

                        # Blank lines for spacing
                        st.caption("")

                st.divider()
                st.subheader("Patient throughoutput")

                pcol1, pcol2, pcol3, pcol4 = st.columns(4)

                with pcol1:
                    with iconMetricContainer(
                        key="patients_per_year",
                        icon_unicode="ebcc",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Patients per Year",
                            value=f"{metrics.average_patients_per_year:.0f}",
                            border=True,
                        )

                    st.caption(f"""
    Range: {metrics.scale_to_year(metrics.min_patients_per_run):.0f}
    to {metrics.scale_to_year(metrics.max_patients_per_run):.0f}

    In-hours: {metrics.scale_to_year(metrics.in_hours_arrivals.mean()):.0f}
    (range: {metrics.scale_to_year(metrics.in_hours_arrivals.min()):.0f}
    to {metrics.scale_to_year(metrics.in_hours_arrivals.max()):.0f})

    Out-of-hours: {metrics.scale_to_year(metrics.ooh_arrivals.mean()):.0f}
    (range: {metrics.scale_to_year(metrics.ooh_arrivals.min()):.0f}
    to {metrics.scale_to_year(metrics.ooh_arrivals.max()):.0f})
                            """)

                with pcol2:
                    st.dataframe(
                        round(
                            metrics.diagnosis_by_stroke_type_count,
                            0,
                        ),
                        hide_index=True,
                    )

                with pcol3:
                    with iconMetricContainer(
                        key="patients_per_day",
                        icon_unicode="e878",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Patients per Day",
                            value=f"{(metrics.average_patients_per_day):.0f}",
                            border=True,
                        )

                with pcol4:
                    st.dataframe(
                        metrics.diagnosis_by_stroke_type_count_per_day.round(2),
                        hide_index=True,
                    )

                st.divider()

                st.subheader("Results")

                col1a, col2a, col3a = st.columns(3)

                # Add container with thrombolysis savings per year
                throm_yearly_save = (
                    my_trial.df_trial_results["Thrombolysis Savings (£)"]
                    / metrics.sim_duration_years
                ).mean()

                with col1a:
                    with iconMetricContainer(
                        key="thrombolysis_savings",
                        icon_unicode="e133",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Thrombolysis Savings per Year",
                            value=f"£{throm_yearly_save:,.0f}",
                            border=True,
                        )

                        st.caption(f"""
    The average total savings for the full model period
    of {metrics.sim_duration_display} were
    £{metrics.df_trial_results["Thrombolysis Savings (£)"].mean():,.0f}.
    This looks only at savings from patients who were able to be offered thrombolysis
    due to the enhanced capabilities of the CTP scanner.
    """)

                with col2a:
                    with iconMetricContainer(
                        key="sdec_savings",
                        icon_unicode="e4d0",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average SDEC Savings per Year",
                            value=f"£{metrics.sdec_yearly_save:,.0f}",
                            border=True,
                        )

                        st.caption(f"""
    The average total savings for the full model period
    of {metrics.sim_duration_display} were
    £{metrics.df_trial_results["SDEC Savings (£)"].mean():,.0f}. This is
    calculated as the total savings from running the SDEC, subtracting the
    medical cost of running the SDEC. SDEC running costs are set to
    £{(g.sdec_dr_cost_min * 60):.2f} per hour.
                        """)

                with col3a:
                    with iconMetricContainer(
                        key="overall_savings",
                        icon_unicode="f04b",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Overall Savings per Year",
                            value=f"£{metrics.overall_yearly_save:,.0f}",
                            border=True,
                        )

                        st.caption(
                            f"""
    The average total savings for the full model period
    of {metrics.sim_duration_display} were
    £{metrics.df_trial_results["Total Savings"].mean():,.0f}.
                            """
                        )

                st.html("<br/>")

                col1b, col2b, col3b = st.columns(3)

                with col1b:
                    # Add container with extra patients thrombolysed per year
                    with iconMetricContainer(
                        key="additional_thrombolysis",
                        icon_unicode="e138",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Extra patients thrombolysed per year",
                            value=f"{metrics.extra_throm_yearly:.0f}",
                            border=True,
                        )

                        st.caption("""
    This looks at the average count of patients who were able to be offered
    thrombolysis due to the enhanced capabilities of the CTP scanner.
                        """)

                with col2b:
                    # Add container with average admissions avoided per year
                    with iconMetricContainer(
                        key="admissions_avoided",
                        icon_unicode="e0b6",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Admissions Avoided per Year",
                            value=f"{metrics.avoid_yearly:,.0f}",
                            border=True,
                        )

                        st.caption(
                            f"""
    Avoided admissions are those patients who were able to leave after being seen
    in SDEC, and would have had a full admission if the SDEC was not available.
    Range = {metrics.avoid_yearly_min} to {metrics.avoid_yearly_max} per year across runs.

    The average total number of admissions avoided for the full model period
    of {metrics.sim_duration_display} were
    {metrics.df_trial_results["Number of Admissions Avoided In Run"].mean():,.0f}.
                            """
                        )

                # Add container with mean ward occupancy
                with col3b:
                    with iconMetricContainer(
                        key="ward_occupancy",
                        icon_unicode="e13c",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Mean Ward Occupancy",
                            value=f"""
    {metrics.mean_ward_occ:,.0f} of {g.number_of_ward_beds} beds
                            """,
                            border=True,
                        )

                        st.caption(
                            f"""
    This is an average occupancy of {(metrics.mean_ward_occ / g.number_of_ward_beds):.1%}
                            """
                        )

                col1c, col2c, col3c = st.columns(3)

                # Add container with average admission delays per year
                with col1c:
                    with iconMetricContainer(
                        key="admission_delays",
                        icon_unicode="f38c",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Admission Delays per Year",
                            value=f"{metrics.admit_delay_yearly:,.0f}",
                            border=True,
                        )

                        st.caption(
                            f"""
    Range = {metrics.admit_delay_yearly_min} to {metrics.admit_delay_yearly_max} per year across runs.
    The average number of admissions that were delayed for the full model period
    of {metrics.sim_duration_display} were
    {metrics.df_trial_results["Number of Admission Delays"].mean():,.0f}.
                            """
                        )

                # Add container with average duration of admission delays
                with col2c:
                    with iconMetricContainer(
                        key="admission_delay_average",
                        icon_unicode="e425",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Ward Admission Delay Duration",
                            value=f"""
    {g.trial_mean_q_time_ward[g.trials_run_counter]} hours
                            """,
                            border=True,
                        )

                # Add container with maximum duration of admission delay
                with col3c:
                    with iconMetricContainer(
                        key="admission_delay_max",
                        icon_unicode="f377",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Maximum Ward Admission Delay Duration",
                            value=f"""
    {g.trial_max_q_time_ward[g.trials_run_counter]} hours
                            """,
                            border=True,
                        )

                    st.caption("""
    This looks at the maximum delay seen across all model runs
                    """)

                col1d, col2d = st.columns(2)

                # Add container with average duration of nurse triage delay
                with col1d:
                    with iconMetricContainer(
                        key="nurse_delay_average",
                        icon_unicode="e425",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Nurse Triage Delay Duration",
                            value=f"""
    {g.trial_mean_q_time_nurse[g.trials_run_counter]} minutes
                            """,
                            border=True,
                        )

                # Add container with maximum duration of nurse triage delay
                with col2d:
                    with iconMetricContainer(
                        key="nurse_delay_max",
                        icon_unicode="f377",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Maximum Nurse Triage Delay Duration",
                            value=f"""
    {g.trial_max_q_time_nurse[g.trials_run_counter]} minutes
                            """,
                            border=True,
                        )

                    st.caption("""
    This looks at the maximum delay seen across all model runs
                    """)

                col1e, col2e = st.columns(2)

                # Add container with patients outside SDEC
                # operating hours
                with col1e:
                    with iconMetricContainer(
                        key="arrive_outside_sdec_operating_hours",
                        icon_unicode="e14b",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="""
    Average Patients Outside of SDEC Operating Hours
                            """,
                            # value=f"{patients_outside_sdec_operating_hours_per_year:.0f} of {average_patients_per_year:.0f} ({(patients_outside_sdec_operating_hours_per_year / average_patients_per_year):.1%})",
                            value=f"""
    {metrics.patients_outside_sdec_operating_hours_per_year:.0f} of
    {metrics.average_patients_per_year:.0f}
    ({(metrics.patients_outside_sdec_operating_hours_per_year / metrics.average_patients_per_year):.1%})
                            """,
                            border=True,
                        )

                        st.caption("""
    This looks at the average count of patients who were unable to be routed to
    SDEC after their CT or CTP scan due to SDEC being shut.
                        """)

                with col2e:
                    with iconMetricContainer(
                        key="arrive_sdec_is_full",
                        icon_unicode="e7ef",
                        family="outline",
                        icon_color="black",
                        type="symbols",
                    ):
                        st.metric(
                            label="Average Patients Bypassing SDEC Due to it Being Full",
                            value=f"""
    {metrics.sdec_full_per_year:.0f} of
    {metrics.patients_inside_sdec_operating_hours_per_year:.0f}
    ({(metrics.sdec_full_per_year / metrics.patients_inside_sdec_operating_hours_per_year):.1%})
    """,
                            border=True,
                        )

                        st.caption(f"""
    This looks at the average count across all runs of patients arriving in SDEC
    during its open hours who had to be routed directly to a ward due to the SDEC
    being full. Range across runs = {metrics.sdec_full_per_year_min:.0f} to {metrics.sdec_full_per_year_max:.0f} patients per year.
                        """)

                st.subheader("Full Per-Run Results for Trial")

                st.dataframe(my_trial.df_trial_results.T)

            with tab2:
                generate_occupancy_plots(
                    my_trial=my_trial,
                    warm_up_duration_days=warm_up_duration_days,
                    sim_duration_days=sim_duration_days,
                )

            ##############################
            #  MARK: Process Maps (DFGs) #
            ##############################
            with tab3:
                plot_dfg_per_feature(
                    split_vars=split_vars,
                    patient_df=metrics.patient_df,
                )

            with tab4:
                ####################################
                # MARK: Flexible Plot of Variables #
                ####################################
                plot_histogram(
                    patient_df=metrics.patient_df,
                    patient_level_metric_choices=patient_level_metric_choices,
                    split_vars=split_vars,
                )

                ####################################
                # MARK: Heatmap                    #
                ####################################
                plot_time_heatmap(patient_df=metrics.patient_df, time_vars=time_vars)

            #########################
            # MARK: Animation       #
            #########################
            with tab5:
                # This needs to receive the full dataframe, including patients
                # generated before the warm-up period elapsed
                # st.write("Event Log")
                # st.write(event_log)
                # st.plotly_chart(
                #     create_vidigi_animation_advanced(event_log, scenario=g())
                # )

                # st.write(create_vidigi_animation(event_log, scenario=g()))
                st.write("Coming Soon!")

            refresh_runs_display()

with scenario_comparison_tab:
    render_run_manager()
    render_scenario_manager()

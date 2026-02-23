"""
Generates plots and visual summaries from stroke ward simulation outputs.
"""

import plotly.express as px


class TrialPlots:
    """
    Create interactive visualisations from a stroke ward simulation trial.
    """
    def __init__(self, trial_object):
        """
        Initialise the TrialPlots object with trial results.

        Parameters
        ----------
        trial_object : stroke_ward_model.trial.Trial
            Completed Trial object whose patient-level DataFrame will be used
            for plotting.
        """
        self.trial_object = trial_object
        self.trial_patient_df = self.trial_object.trial_patient_df

    def plot_los(self):
        """
        Plot a histogram of SDEC length of stay for all patients in the trial.

        Returns
        -------
        plotly.graph_objs._figure.Figure
            Plotly Figure object showing the distribution of `sdec_los` values.
        """
        return px.histogram(self.trial_patient_df, x="sdec_los")

    def plot_arrivals_per_day(self, run):
        """
        Plot daily arrivals for a single simulation run.

        We filter to one run because aggregating over all runs would average
        out day-to-day variability and flatten the pattern of busy and quiet
        days that we want to inspect.

        We keep all patients as daily arrival counts are not affected by
        whether we are in the warm-up period or not.

        Parameters
        ----------
        run : int
            Run number to filter on (values from the `run` column).

        Returns
        -------
        dict[str, plotly.graph_objs._figure.Figure]
            Dictionary with two Plotly figures:
            - 'histogram': distribution of arrivals per day (how many days
              had N arrivals)
            - 'timeseries': arrivals per day over time within the chosen run
        """
        df_run = self.trial_patient_df[self.trial_patient_df["run"] == run]

        # Convert arrival time (minutes) into arrival day index
        arrival_day = (df_run["clock_start"] // (24 * 60)).astype(int)

        # Count number of arrivals per day (series indexed by day)
        daily_counts = arrival_day.value_counts().sort_index()

        # Histogram: distribution of daily arrivals
        fig_hist = px.histogram(x=daily_counts.values)
        fig_hist.update_layout(
            showlegend=False,
            xaxis_title="Number of arrivals per day",
            yaxis_title="Frequency",
            title=f"Distribution of daily arrivals (run {run})",
        )

        # Time series: arrivals per day over the simulation
        fig_ts = px.line(
            x=daily_counts.index,
            y=daily_counts.values,
            labels={"x": "Day of simulation", "y": "Number of arrivals"},
            title=f"Arrivals per day over time (run {run})",
        )

        return {"histogram": fig_hist, "timeseries": fig_ts}


if __name__ == "__ main __":
    from stroke_ward_model.inputs import g
    from stroke_ward_model.trial import Trial

    g.number_of_ward_beds = 30
    g.sim_duration = 365 * 24 * 60
    g.sdec_beds = 8
    sdec_value = 33.3
    g.sdec_value = sdec_value
    g.sdec_unav_freq = 1440 * (sdec_value / 100)
    g.sdec_unav_time = 1440 - g.sdec_unav_freq

    ctp_value = 50
    g.ctp_value = ctp_value
    g.ctp_unav_freq = 1440 * (ctp_value / 100)
    g.ctp_unav_time = 1440 - g.ctp_unav_freq
    ctp_input = True

    my_trial = Trial()

    # Call the run_trial method of our Trial object
    my_trial.run_trial()

    print(my_trial.trial_info)

    print(my_trial.df_trial_results.T)

    print(my_trial.trial_patient_df.head())

    plots = TrialPlots(my_trial)

    plots.plot_los()

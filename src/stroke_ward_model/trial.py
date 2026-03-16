"""
Runs multiple simulation replications and aggregates run-level results.
"""

from stroke_ward_model.inputs import g
from stroke_ward_model.model import Model
import pandas as pd
# Class representing a Trial for our simulation - a batch of simulation runs.


# MARK: Trial class
class Trial:
    """
    Orchestrator for running multiple simulation iterations (runs) and
    aggregating results.

    The Trial class manages the execution of multiple `Model` instances as
    defined in the global configuration. It collects performance metrics,
    financial data, and patient-level logs from each individual run into
    centralised DataFrames for cross-run analysis.

    Attributes
    ----------
    df_trial_results : pd.DataFrame
        A summary DataFrame where each row represents a single simulation run.
        Tracks metrics such as mean queue times, occupancy, and financial
        savings.
    model_objects : list
        A collection of `Model` instances created during the trial, allowing
        for post-hoc inspection of specific run states.
    trial_patient_dataframes : list
        A list of DataFrames, each containing detailed attribute data for every
        patient in a specific run.
    trial_patient_df : pd.DataFrame
        The master DataFrame created by concatenating all patient-level data
        across all runs in the trial.
    trial_info : str
        A descriptive string containing the configuration settings used for
        the current trial (e.g., SDEC therapy status and resource availability).

    Notes
    -----
    GENAI declaration (SR): this docstring has been generated with the aid
    of Google Gemini Flash.
    All generated content has been thoroughly reviewed.
    """

    # The constructor sets up a pandas dataframe that will store the key
    # results from each run with run number as the index.

    def __init__(self):
        self.df_trial_results = pd.DataFrame()
        self.df_trial_results["Run Number"] = [0]
        self.df_trial_results["Mean Q Time Nurse (Mins)"] = [0.0]
        self.df_trial_results["Max Q Time Nurse (Mins)"] = [0.0]
        self.df_trial_results["Number of Admissions Avoided In Run"] = [0.0]
        self.df_trial_results["Mean Q Time Ward (Hour)"] = [0.0]
        self.df_trial_results["Max Q Time Ward (Hour)"] = [0.0]
        self.df_trial_results["Mean Occupancy"] = [0.0]
        self.df_trial_results["Number of Admission Delays"] = [0.0]
        self.df_trial_results["Mean Length of Stay Ward (Hours)"] = [0.0]
        self.df_trial_results["Financial Savings of Admissions Avoidance (£)"] = [0.0]
        self.df_trial_results["SDEC Medical Staff Cost (£)"] = [0.0]
        self.df_trial_results["SDEC Savings (£)"] = [0.0]
        self.df_trial_results["Thrombolysis Savings (£)"] = [0.0]
        self.df_trial_results["Total Savings"] = [0.0]
        self.df_trial_results["Mean MRS Change"] = [0.0]
        self.df_trial_results["Mean Number of Patients Assessed"] = [0.0]
        self.df_trial_results["Number of Intracranial Haemhorrhage patients"] = [0.0]
        self.df_trial_results["Number of Ischaemic Stroke patients"] = [0.0]
        self.df_trial_results["Number of TIA patients"] = [0.0]
        self.df_trial_results["Number of Stroke Mimic patients"] = [0.0]
        self.df_trial_results["Number of Non-Stroke patients"] = [0.0]
        self.df_trial_results[
            "Mean Additional Thrombolysed Patients From CTP Running"
        ] = [0.0]
        self.df_trial_results.set_index("Run Number", inplace=True)

        self.ward_occupancy_audits = []
        self.ward_occupancy_df = pd.DataFrame()

        self.sdec_occupancy_audits = []
        self.sdec_occupancy_df = pd.DataFrame()

        self.model_objects = []
        # self.patient_objects = {}

        self.trial_patient_dataframes = []
        self.trial_patient_df = pd.DataFrame()

        self.results_dataframes = []
        self.trial_results_df = pd.DataFrame()

    # MARK: M: run_trial
    # Method to run a trial

    def run_trial(self):
        """
        Executes the batch of simulation runs and aggregates the resulting data.

        This method performs the following steps:

        1. Loops through the number of runs specified in `g.number_of_runs`.

        2. Instantiates and executes a `Model` for each run.

        3. Collects summary metrics (e.g., queue times, savings) into `df_trial_results`.

        4. Flattens patient-level data into a single master DataFrame.

        5. Calculates trial-level means and updates the global `g` class attributes.

        6. Optionally exports results to a CSV file if `g.write_to_csv` is True.

        This method dynamically updates the global configuration class `g` by
        calculating the mean of results across all runs and storing them in
        dictionaries keyed by the trial counter.

        See Also
        --------
        Model.run : The method called to execute an individual simulation iteration.

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.
        """
        # Run the simulation for the number of runs specified in g class.
        # For each run, we create a new instance of the Model class and call its
        # run method, which sets everything else in motion.  Once the run has
        # completed, we grab out the stored run results
        # and store it against the run number in the trial results dataframe.

        for run in range(g.number_of_runs):
            my_model = Model(run)
            my_model.run()

            self.model_objects.append(my_model)

            self.df_trial_results.loc[run] = [
                my_model.mean_q_time_nurse,
                my_model.max_q_time_nurse,
                my_model.number_of_admissions_avoided,
                my_model.mean_q_time_ward,
                my_model.max_q_time_ward,
                my_model.mean_ward_occupancy,
                my_model.admission_delays,
                my_model.mean_los_ward,
                my_model.sdec_financial_savings,
                my_model.medical_staff_cost,
                my_model.savings_sdec,
                my_model.thrombolysis_savings,
                my_model.total_savings,
                my_model.mean_mrs_change,
                my_model.patient_counter,
                my_model.ich_patients_count,
                my_model.i_patients_count,
                my_model.tia_patients_count,
                my_model.stroke_mimic_patient_count,
                my_model.non_stroke_patient_count,
                my_model.additional_thrombolysis_from_ctp,
            ]

            # self.patient_objects[run] = my_model.patient_objects
            patient_dataframe = pd.DataFrame(
                [p.__dict__ for p in my_model.patient_objects]
            )
            patient_dataframe["run"] = run + 1
            self.trial_patient_dataframes.append(patient_dataframe)
            my_model.results_df["run"] = run + 1
            self.results_dataframes.append(my_model.results_df)

            my_model.ward_occupancy_graph_df["run"] = run + 1
            self.ward_occupancy_audits.append(my_model.ward_occupancy_graph_df)

            my_model.sdec_occupancy_graph_df["run"] = run + 1
            self.sdec_occupancy_audits.append(my_model.sdec_occupancy_graph_df)

        self.trial_patient_df = pd.concat(self.trial_patient_dataframes)
        self.ward_occupancy_df = pd.concat(self.ward_occupancy_audits)
        self.sdec_occupancy_df = pd.concat(self.sdec_occupancy_audits)
        self.trial_results_df = pd.concat(self.results_dataframes)

        if g.write_to_csv == True:
            self.df_trial_results.to_csv(
                f"trial {g.trials_run_counter} trial results.csv", index=False
            )

        # TODO: SR: FIX appending of per-run graphs to trial class
        # if g.gen_graph:
        #     self.graph_objects.append(my_model.plot_stroke_run_graphs(plot=False))

        # This is new code that will store all averages to compare across
        # the different trials. It does this by checking if the attribute
        # exists in the global g class, and if it doesn't it creates it. It
        # then stores the mean of each run against the attribute
        # (eg "trial_mean_q_time_nurse")

        # The mean is stored against the key of g.trials_run_counter.

        for attr, col in [
            ("trial_mean_q_time_nurse", "Mean Q Time Nurse (Mins)"),
            ("trial_max_q_time_nurse", "Max Q Time Nurse (Mins)"),
            (
                "trial_number_of_admissions_avoided",
                "Number of Admissions Avoided In Run",
            ),
            ("trial_mean_q_time_ward", "Mean Q Time Ward (Hour)"),
            ("trial_max_q_time_ward", "Max Q Time Ward (Hour)"),
            ("trial_mean_occupancy", "Mean Occupancy"),
            ("trial_number_of_admission_delays", "Number of Admission Delays"),
            (
                "trial_financial_savings_of_a_a",
                "Financial Savings of Admissions Avoidance (£)",
            ),
            ("sdec_medical_cost", "SDEC Medical Staff Cost (£)"),
            ("trial_sdec_financial_savings", "SDEC Savings (£)"),
            ("trial_thrombolysis_savings", "Thrombolysis Savings (£)"),
            ("trial_total_savings", "Total Savings"),
            ("trial_mrs_change", "Mean MRS Change"),
            ("trial_patient_count", "Mean Number of Patients Assessed"),
            (
                "trial_additional_thrombolysis_from_ctp",
                "Mean Additional Thrombolysed Patients From CTP Running",
            ),
        ]:
            # Checks to see if the attribute already exists and if it doesn't
            # create it. Creates a mean of each trial and creates a dictionary
            # that can be read later.

            if not hasattr(g, attr):
                setattr(g, attr, {})
            if "max" in attr:
                getattr(g, attr)[g.trials_run_counter] = round(
                    self.df_trial_results[col].max(), 2
                )
            else:
                getattr(g, attr)[g.trials_run_counter] = round(
                    self.df_trial_results[col].mean(), 2
                )

        # Code to store the configuration that was used for this trial.
        self.trial_info = (
            f"Trial {g.trials_run_counter}, SDEC Therapy = {g.therapy_sdec},"
            f" SDEC Open % = {g.sdec_value}, CTP Open % = {g.ctp_value}"
        )

        print("---------------------------------------------------")
        print(f"{self.trial_info}")
        print(f"Trial {g.trials_run_counter} Results:")
        print(" ")
        print(
            f"Trial Mean Q Time Nurse (Mins):     \
              {g.trial_mean_q_time_nurse[g.trials_run_counter]}"
        )
        print(
            f"Trial Max Q Time Nurse (Mins):     \
              {g.trial_max_q_time_nurse[g.trials_run_counter]}"
        )
        print(
            f"Trial Number of Admissions Avoided: \
              {g.trial_number_of_admissions_avoided[g.trials_run_counter]}"
        )
        print(
            f"Trial Mean Q Time Ward (Hours):     \
              {g.trial_mean_q_time_ward[g.trials_run_counter]}"
        )
        print(
            f"Trial Max Q Time Ward (Hours):     \
              {g.trial_max_q_time_ward[g.trials_run_counter]}"
        )
        print(
            f"Trial Mean Ward Occupancy:          \
              {g.trial_mean_occupancy[g.trials_run_counter]}"
        )
        print(
            f"Trial Number of Admission Delays:   \
              {g.trial_number_of_admission_delays[g.trials_run_counter]}"
        )
        print(
            f"Trial SDEC Total Savings (£):       \
              {g.trial_financial_savings_of_a_a[g.trials_run_counter]}"
        )
        print(
            f"Trial SDEC Medical Cost (£):        \
              {g.sdec_medical_cost[g.trials_run_counter]}"
        )
        print(
            f"Trial SDEC Savings - Cost (£):      \
              {g.trial_sdec_financial_savings[g.trials_run_counter]}"
        )
        print(
            f"Trial Thrombolysis Savings (£):     \
              {g.trial_thrombolysis_savings[g.trials_run_counter]}"
        )
        print(
            f"Trial Total Savings (£):            \
              {g.trial_total_savings[g.trials_run_counter]}"
        )
        print(
            f"Mean MRS Change:                    \
              {g.trial_mrs_change[g.trials_run_counter]}"
        )
        print(
            f"Mean Assessed Patients:                    \
              {g.trial_patient_count[g.trials_run_counter]}"
        )
        print(
            f"Mean Additional Thrombolysed Patients From CTP Running:                    \
              {g.trial_additional_thrombolysis_from_ctp[g.trials_run_counter]}"
        )

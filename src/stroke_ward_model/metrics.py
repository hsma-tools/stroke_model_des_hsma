import pandas as pd
import numpy as np
import json
from dataclasses import dataclass


class Metrics:
    """
    Calculates and stores performance, pathway, and financial metrics based on
    hospital simulation trial results.

    This class filters out warm-up period patients, calculates time-scaled
    metrics (daily, yearly), tracks facility utilizations (SDEC, CTP), and
    evaluates financial savings and avoided admissions.

    Parameters
    ----------
    g : object
        A simulation globals/parameters object containing duration, facility
        opening hours, bed counts, and trial run counters.
    patient_df_including_warmup : pd.DataFrame
        DataFrame containing patient-level data across simulation runs, including
        those generated during the warm-up period.
    df_trial_results : pd.DataFrame
        DataFrame containing aggregated trial-level results, such as savings,
        admission delays, and mean occupancy.

    Attributes
    ----------
    patient_df : pd.DataFrame
        Filtered patient data excluding those generated during the warm-up period.
    sim_duration_days : float
        The total duration of the simulation in days.
    sim_duration_years : float
        The total duration of the simulation in years.
    average_patients_per_year : float
        The average number of patient arrivals scaled to a full year.
    overall_yearly_save : float
        The mean total monetary savings scaled per year.
    avoid_yearly : float
        The mean number of full admissions avoided per year due to SDEC.
    diagnosis_by_stroke_type_count : pd.DataFrame
        Count of patients grouped by stroke diagnosis type per run.
    """

    def __init__(self, g, patient_df_including_warmup, df_trial_results):

        self.patient_df_including_warmup = patient_df_including_warmup
        self.g = g
        self.df_trial_results = df_trial_results

        # Filter out any patients who were generated before the warm-up
        # period elapsed
        self.patient_df = self.patient_df_including_warmup[
            ~self.patient_df_including_warmup["generated_during_warm_up"]
        ]

        # Time attributes
        self.sim_duration_days = g.sim_duration / 60 / 24
        self.sim_duration_years = self.sim_duration_days / 365
        self.sim_duration_display = f"""
{(self.sim_duration_days // 365):.0f}
year{"" if self.sim_duration_days // 365 == 1 else "s"} and
{(self.sim_duration_days % 365):.0f} days
            """

        self.start_hour_ctp = g.ctp_opening_hour
        self.duration_hours_ctp = ((24 * 60) - g.ctp_unav_time) / 60
        self.end_hour_ctp = (self.start_hour_ctp + self.duration_hours_ctp) % 24

        self.start_hour_sdec = g.sdec_opening_hour
        self.duration_hours_sdec = ((24 * 60) - g.sdec_unav_time) / 60
        self.end_hour_sdec = (self.start_hour_sdec + self.duration_hours_sdec) % 24

        # Additional attributes for reporting
        self.number_of_ward_beds = g.number_of_ward_beds
        self.sdec_beds = g.sdec_beds

        self.therapy_sdec = int(g.therapy_sdec)
        self.thrombolysis_los_save = g.thrombolysis_los_save

        self.sdec_dr_cost_min = g.sdec_dr_cost_min
        self.sdec_bed_day_saving = g.sdec_bed_day_saving
        self.inpatient_bed_cost = g.inpatient_bed_cost
        self.short_term_thrombolysis_savings = int(g.short_term_thrombolysis_savings)
        self.inpatient_bed_cost_thrombolysis = g.inpatient_bed_cost_thrombolysis
        self.fixed_thrombolysis_saving_amount_long_term = (
            g.fixed_thrombolysis_saving_amount_long_term
        )

        # Patients per run
        self.average_patients_per_run = self.patient_df.groupby("run").size().mean()
        self.min_patients_per_run = self.patient_df.groupby("run").size().min()
        self.max_patients_per_run = self.patient_df.groupby("run").size().max()

        self.average_patients_per_year = self.scale_to_year(
            self.average_patients_per_run
        )

        self.average_patients_per_day = self.average_patients_per_year / 365

        self.in_hours_arrivals = (
            self.patient_df[self.patient_df["arrived_ooh"] == False]
            .groupby("run")
            .size()
        )

        self.ooh_arrivals = (
            self.patient_df[self.patient_df["arrived_ooh"] == True]
            .groupby("run")
            .size()
        )

        # Trial-level results

        # SDEC savings per year
        self.sdec_yearly_save = (
            self.df_trial_results["SDEC Savings (£)"] / self.sim_duration_years
        ).mean()

        # Thrombolysis savings per year
        self.thrombolysis_yearly_save = (
            self.df_trial_results["Thrombolysis Savings (£)"] / self.sim_duration_years
        ).mean()

        # Overall savings per year
        self.overall_yearly_save = (
            self.df_trial_results["Total Savings"] / self.sim_duration_years
        ).mean()

        # Number of additional patients who are able to have thrombolysis thanks to having
        # a CTP scan
        self.extra_throm = g.trial_additional_thrombolysis_from_ctp[
            g.trials_run_counter
        ]
        self.extra_throm_yearly = self.scale_to_year(self.extra_throm)

        # Total number of patients thrombolysed
        self.thrombolysed = (
            self.patient_df[self.patient_df["thrombolysis"] == True]
            .groupby("run")
            .size()
            .mean()
        )

        self.thrombolysed_per_year = self.scale_to_year(self.thrombolysed)
        # SSNAP uses all strokes as denominator (even though patients with ICH should never
        # be thrombolysed in practice)
        # https://ssnap.zendesk.com/hc/en-us/articles/23535233448093-3-1-Percentage-of-all-stroke-patients-given-thrombolysis-Reperfusion-domain
        # (plus discussions with JW to confirm what 'all patients in the cohort' includes)
        self.eligible_for_thrombolysis = (
            self.patient_df[
                self.patient_df["patient_diagnosis_type"].isin(["I", "ICH"])
            ]
            .groupby("run")
            .size()
            .mean()
        )

        self.eligible_for_thrombolysis_per_year = self.scale_to_year(
            self.eligible_for_thrombolysis
        )

        self.thrombolysis_rate = (
            self.thrombolysed / self.eligible_for_thrombolysis_per_year
        )

        self.count_thrombolysis_without_ctp = self.thrombolysed - self.extra_throm
        self.thrombolysis_rate_without_ctp = (
            self.count_thrombolysis_without_ctp
            / self.eligible_for_thrombolysis_per_year
        )

        # Number of patients who can avoid a full admission due to SDEC operating
        self.avoid_yearly = self.scale_to_year(
            (self.df_trial_results["Number of Admissions Avoided In Run"]).mean()
        )

        # Add range seen across different sim runs
        self.avoid_yearly_min = self.scale_to_year(
            (self.df_trial_results["Number of Admissions Avoided In Run"]).min()
        )

        self.avoid_yearly_max = self.scale_to_year(
            (self.df_trial_results["Number of Admissions Avoided In Run"]).max()
        )

        # Ischaemic stroke admissions avoided
        self.avoid_yearly_ischaemic = self.scale_to_year(
            self.patient_df[
                (self.patient_df["patient_diagnosis_type"].isin(["I"]))
                & (self.patient_df["admission_avoidance"] == True)
            ]
            .groupby("run")
            .size()
            .mean()
        )

        # ICH stroke admissions avoided
        self.avoid_yearly_ich = self.scale_to_year(
            self.patient_df[
                (self.patient_df["patient_diagnosis_type"].isin(["ICH"]))
                & (self.patient_df["admission_avoidance"] == True)
            ]
            .groupby("run")
            .size()
            .mean()
        )

        # Admissions avoided through therapy provision
        self.avoid_yearly_therapy = self.scale_to_year(
            self.patient_df[
                (self.patient_df["admission_avoidance"] == True)
                & (self.patient_df["admission_avoidance_because_of_therapy"] == True)
            ]
            .groupby("run")
            .size()
            .mean()
        )

        # Number of patients with a delayed admission to a stroke ward per year
        self.admit_delay_yearly = (
            self.df_trial_results["Number of Admission Delays"]
            / self.sim_duration_years
        ).mean()

        # Add range seen across different sim runs
        self.admit_delay_yearly_min = (
            self.df_trial_results["Number of Admission Delays"]
            / self.sim_duration_years
        ).min()

        self.admit_delay_yearly_max = (
            self.df_trial_results["Number of Admission Delays"]
            / self.sim_duration_years
        ).max()

        # Mean ward occupancy (count)
        self.mean_ward_occ = self.df_trial_results["Mean Occupancy"].mean()
        self.mean_ward_occ_perc = (self.mean_ward_occ / g.number_of_ward_beds) * 100

        self.diagnosis_by_stroke_type_count = pd.DataFrame()
        self.diagnosis_by_stroke_type_count_per_year = pd.DataFrame()
        self.diagnosis_by_stroke_type_count_per_day = pd.DataFrame()

        self.patients_inside_sdec_operating_hours = np.nan
        self.patients_inside_sdec_operating_hours_per_year = np.nan
        self.patients_outside_sdec_operating_hours_per_year = np.nan

        self.sdec_full = np.nan
        self.sdec_full_per_year = np.nan

        self.create_diagnosis_by_stroke_type_count()
        self.calculate_missed_opportunities()

    def create_diagnosis_by_stroke_type_count(self):
        """
        Groups the filtered patient dataset by diagnosis type and computes
        the mean counts per simulation run, per year, and per day.

        The resulting DataFrames are stored in the instance attributes:
        `diagnosis_by_stroke_type_count`,
        `diagnosis_by_stroke_type_count_per_year`, and
        `diagnosis_by_stroke_type_count_per_day`.
        """

        self.diagnosis_by_stroke_type_count = (
            self.patient_df.groupby(["run", "patient_diagnosis_type"])
            .size()
            .groupby("patient_diagnosis_type")
            .mean()
            .reset_index(name="mean_patients_per_run")
        )

        self.diagnosis_by_stroke_type_count["patient_diagnosis_type"] = pd.Categorical(
            self.diagnosis_by_stroke_type_count["patient_diagnosis_type"],
            categories=["ICH", "I", "TIA", "Stroke Mimic", "Non Stroke"],
            ordered=True,
        )

        self.diagnosis_by_stroke_type_count = (
            self.diagnosis_by_stroke_type_count.sort_values("patient_diagnosis_type")
        )

        self.diagnosis_by_stroke_type_count["mean_patients_per_run"] = (
            self.diagnosis_by_stroke_type_count["mean_patients_per_run"]
            / (self.g.sim_duration / 60 / 24)
            * 365
        )

        self.diagnosis_by_stroke_type_count_per_year = (
            self.diagnosis_by_stroke_type_count.copy()
        )

        self.diagnosis_by_stroke_type_count_per_day = (
            self.diagnosis_by_stroke_type_count_per_year.copy()
        )

        self.diagnosis_by_stroke_type_count = (
            self.diagnosis_by_stroke_type_count.rename(
                columns={
                    "patient_diagnosis_type": "Diagnosis",
                    "mean_patients_per_run": "Count",
                }
            )
        )

        self.diagnosis_by_stroke_type_count_per_year = (
            self.diagnosis_by_stroke_type_count_per_year.rename(
                columns={
                    "patient_diagnosis_type": "Diagnosis",
                    "mean_patients_per_run": "Count",
                }
            )
        )

        self.diagnosis_by_stroke_type_count_per_day["mean_patients_per_run"] = (
            self.diagnosis_by_stroke_type_count_per_day["mean_patients_per_run"] / 365
        )

        self.diagnosis_by_stroke_type_count_per_day = (
            self.diagnosis_by_stroke_type_count_per_day.rename(
                columns={
                    "patient_diagnosis_type": "Diagnosis",
                    "mean_patients_per_run": "Count",
                }
            )
        )

    def calculate_missed_opportunities(self):
        """
        Calculates the volume of missed treatment opportunities based on SDEC
        availability and capacity.

        Computes the number of patients arriving inside/outside SDEC operating
        hours when required, and the frequency of instances where SDEC was
        full when required. Extrapolates these counts to yearly metrics.
        """
        self.patients_inside_sdec_operating_hours = (
            self.patient_df[(self.patient_df["sdec_running_when_required"] == True)]
            .groupby("run")
            .size()
            .mean()
        )

        self.patients_inside_sdec_operating_hours_per_year = (
            self.patients_inside_sdec_operating_hours / (self.g.sim_duration / 60 / 24)
        ) * 365

        self.patients_outside_sdec_operating_hours_per_year = (
            self.average_patients_per_year
            - self.patients_inside_sdec_operating_hours_per_year
        )

        self.sdec_full = (
            self.patient_df[self.patient_df["sdec_full_when_required"] == True]
            .groupby("run")
            .size()
            .mean()
        )

        self.sdec_full_per_year = (
            self.sdec_full / (self.g.sim_duration / 60 / 24)
        ) * 365

        self.sdec_full_min = (
            self.patient_df[self.patient_df["sdec_full_when_required"] == True]
            .groupby("run")
            .size()
            .min()
        )

        self.sdec_full_per_year_min = (
            self.sdec_full_min / (self.g.sim_duration / 60 / 24)
        ) * 365

        self.sdec_full_max = (
            self.patient_df[self.patient_df["sdec_full_when_required"] == True]
            .groupby("run")
            .size()
            .max()
        )

        self.sdec_full_per_year_max = self.scale_to_year(self.sdec_full_max)

    def scale_to_year(self, value):
        """
        Scales a given simulation value to a yearly equivalent based on the
        configured simulation duration.

        Parameters
        ----------
        value : float or int
            The numeric value to be scaled (e.g., patient count per run).

        Returns
        -------
        float
            The input value proportionally scaled to a 365-day year.
        """
        return (value / (self.g.sim_duration / 60 / 24)) * 365

    def diff(self, other: "Metrics | MetricsSnapshot") -> dict:
        """
        Computes the numerical difference between the attributes of this instance
        and another Metrics or MetricsSnapshot instance.

        Parameters
        ----------
        other : Metrics or MetricsSnapshot
            The target object to compare against. Must contain compatible
            numeric attributes.

        Returns
        -------
        dict
            A dictionary where each key is an attribute name, mapping to a nested
            dictionary containing 'self' (current value), 'other' (comparison value),
            and 'difference' (self - other).

        Raises
        ------
        TypeError
            If the provided `other` argument is not an instance of `Metrics`
            or lacks a `values` attribute (as in `MetricsSnapshot`).
        """
        if isinstance(other, Metrics):
            other_values = {
                attr: float(getattr(other, attr))
                for attr in vars(other)
                if isinstance(
                    getattr(other, attr), (int, float, np.integer, np.floating)
                )
                and not np.isnan(getattr(other, attr))
            }
        elif hasattr(other, "values"):  # MetricsSnapshot
            other_values = other.values
        else:
            raise TypeError(f"Cannot diff against {type(other)}")

        results = {}
        for attr in vars(self):
            self_val = getattr(self, attr)
            if not isinstance(self_val, (int, float, np.integer, np.floating)):
                continue
            if np.isnan(self_val):
                continue
            other_val = other_values.get(attr)
            if other_val is None:
                continue
            results[attr] = {
                "self": self_val,
                "other": other_val,
                "difference": self_val - other_val,
            }
        return results


@dataclass
class MetricsSnapshot:
    """
    A lightweight, serialisable version of a Metrics instance.

    This dataclass is designed to capture and store the purely numeric, non-NaN
    scalar values from a live `Metrics` object, making it suitable for JSON
    serialization, saving to disk, or comparing historical simulation runs.

    Attributes
    ----------
    label : str
        A human-readable identifier or name for this specific snapshot.
    values : dict
        A dictionary containing the numeric scalar metrics extracted from a
        `Metrics` instance, where keys are metric names and values are floats.
    """

    label: str
    values: dict  # the numeric scalars from Metrics.diff / vars()

    def diff(self, other: "Metrics | MetricsSnapshot") -> dict:
        """
        Computes the numerical difference between the metric values of this
        snapshot and another `Metrics` or `MetricsSnapshot` instance.

        Parameters
        ----------
        other : Metrics or MetricsSnapshot
            The target object to compare against. Must contain compatible
            numeric attributes or a `values` dictionary.

        Returns
        -------
        dict
            A dictionary where each key is a metric name, mapping to a nested
            dictionary containing 'self' (current snapshot value), 'other'
            (comparison value), and 'difference' (self - other).

        Raises
        ------
        TypeError
            If the provided `other` argument is not an instance of `Metrics`
            or `MetricsSnapshot`.
        """
        if hasattr(other, "values"):  # MetricsSnapshot
            other_values = other.values
        elif hasattr(other, "__dict__"):  # Metrics
            other_values = {
                attr: float(getattr(other, attr))
                for attr in vars(other)
                if isinstance(
                    getattr(other, attr), (int, float, np.integer, np.floating)
                )
                and not np.isnan(getattr(other, attr))
            }
        else:
            raise TypeError(f"Cannot diff against {type(other)}")

        results = {}
        for key, self_val in self.values.items():
            other_val = other_values.get(key)
            if other_val is None:
                continue
            results[key] = {
                "self": self_val,
                "other": other_val,
                "difference": self_val - other_val,
            }
        return results

    def to_dict(self) -> dict:
        """
        Serializes the snapshot instance into a standard Python dictionary.

        Returns
        -------
        dict
            A dictionary representation of the snapshot, containing the 'label'
            and 'values' keys.
        """
        return {"label": self.label, "values": self.values}

    @classmethod
    def from_dict(cls, data: dict) -> "MetricsSnapshot":
        """
        Constructs a `MetricsSnapshot` instance from a dictionary representation.

        Parameters
        ----------
        data : dict
            A dictionary containing at least the keys 'label' (str) and
            'values' (dict).

        Returns
        -------
        MetricsSnapshot
            A newly initialized snapshot instance populated with the provided data.
        """
        return cls(label=data["label"], values=data["values"])

    @classmethod
    def from_metrics(cls, metrics: "Metrics", label: str) -> "MetricsSnapshot":
        """
        Builds a lightweight snapshot from a live `Metrics` instance.

        Iterates through the attributes of a `Metrics` object, extracting only
        the valid (non-NaN) integer and floating-point values, casting them to
        standard Python floats to ensure JSON compatibility.

        Parameters
        ----------
        metrics : Metrics
            The live `Metrics` object to be serialized.
        label : str
            A string identifier to assign to the newly created snapshot.

        Returns
        -------
        MetricsSnapshot
            A snapshot instance containing the extracted numeric values.
        """
        values = {}
        for attr in vars(metrics):
            val = getattr(metrics, attr)
            if not isinstance(val, (int, float, np.integer, np.floating)):
                continue
            if np.isnan(val):
                continue
            values[attr] = float(val)  # ensure plain Python float for JSON
        return cls(label=label, values=values)

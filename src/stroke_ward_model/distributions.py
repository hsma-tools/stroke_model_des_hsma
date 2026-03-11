"""
Initialises and manages random distributions used throughout the simulation.
"""

import numpy as np
import pandas as pd
from sim_tools.distributions import Exponential, Normal, DiscreteEmpirical, Uniform
from typing import Optional
from numpy.random import SeedSequence

from stroke_ward_model.inputs import g


class NSPPThinningModified:
    """
    MODIFIED FROM SIM_TOOLS TO HANDLE BOUNDARY BUG

    Non Stationary Poisson Process via Thinning.

    Thinning is an acceptance-rejection approach to sampling
    inter-arrival times (IAT) from a time-dependent distribution
    where each time period follows its own exponential distribution.

    This implementation takes mean inter-arrival times as inputs, making it
    consistent with NumPy's exponential distribution parameterization.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        interval_width: Optional[float] = None,
        random_seed1: Optional[int | SeedSequence] = None,
        random_seed2: Optional[int | SeedSequence] = None,
    ):
        """
        Non Stationary Poisson Process via Thinning.

        Time dependency is andled for a single table
        consisting of equally spaced intervals.

        Parameters
        ----------
        data: pandas.DataFrame
            DataFrame with time points and mean inter-arrival times.
            Columns should be "t" and "mean_iat" respectively.

        interval_width: float, optional (default=None)
            The width of each time interval. If None, it will be calculated
            from consecutive time points in the data. Required if data has only
            one row.

        random_seed1: int | SeedSequence, optional (default=None)
            Random seed for the exponential distribution

        random_seed2: int | SeedSequence, optional (default=None)
            Random seed for the uniform distribution used
            for acceptance/rejection sampling.
        """
        self.data = data
        self.arr_rng = np.random.default_rng(random_seed1)
        self.thinning_rng = np.random.default_rng(random_seed2)

        # Find the minimum mean IAT (corresponds to the maximum arrival rate)
        self.min_iat = data["mean_iat"].min()

        if self.min_iat <= 0:
            raise ValueError("Mean inter-arrival times must be positive")

        # Use provided interval width or calculate from data
        if interval_width is not None:
            self.interval = interval_width
        elif len(data) > 1:
            # Calculate from data (assumes all intervals are equal in length)
            self.interval = data.iloc[1]["t"] - data.iloc[0]["t"]
        else:
            raise ValueError(
                "With only one data point, interval_width must be provided"
            )

        self.rejects_last_sample = None

    def __repr__(self):
        """Return a string representation of the NSPPThinning instance."""
        # Truncate the data representation if too long
        max_len = 100
        data_str = repr(self.data)
        if len(data_str) > max_len:
            data_str = data_str[:max_len] + "..."

        # Return class name with both data and interval information
        return (
            f"{self.__class__.__name__}(data={data_str}, "
            + f"interval={self.interval})"
        )

    def sample(self, simulation_time: float) -> float:
        """
        Run a single iteration of acceptance-rejection
        thinning alg to sample the next inter-arrival time

        Parameters
        ----------
        simulation_time: float
            The current simulation time. This is used to look up
            the mean IAT for the time period.

        Returns
        -------
        float
            The inter-arrival time
        """

        # included for audit and tracking purposes.
        self.rejects_last_sample = 0

        interarrival_time = 0.0

        while True:
            w = self.arr_rng.exponential(self.min_iat)
            candidate_time = simulation_time + interarrival_time + w

            idx = int(candidate_time // self.interval) % len(self.data)
            mean_iat_candidate = self.data["mean_iat"].iloc[idx]

            u = self.thinning_rng.uniform()

            if u < (self.min_iat / mean_iat_candidate):
                interarrival_time += w
                break
            else:
                interarrival_time += w
                self.rejects_last_sample += 1

        return interarrival_time


##############################
# MARK: Set up distributions #
##############################
def initialise_distributions(self):
    """
    Set up distributions for sampling from.
    Pulls distribution parameters from g class where relevant.
    Use of Seed
    """
    ss = np.random.SeedSequence(g.master_seed + self.run_number)
    seeds = ss.spawn(40)

    # Generate a dataframe for in and out of hours starts
    def build_iat_dataframe(step_minutes=60):
        t = np.arange(0, 24 * 60, step_minutes)

        start = g.in_hours_start * 60
        end = g.ooh_start * 60

        if start < end:
            # Normal case (does not cross midnight)
            in_hours_mask = (t >= start) & (t < end)
        else:
            # Crosses midnight
            in_hours_mask = (t >= start) | (t < end)

        mean_iat = np.where(in_hours_mask, g.patient_inter_day, g.patient_inter_night)
        df = pd.DataFrame({"t": t, "mean_iat": mean_iat})
        print(df)
        return df

    self.iat_dataframe = build_iat_dataframe()

    # Inter-arrival times
    self.patient_inter_dist = NSPPThinningModified(
        data=self.iat_dataframe,
        interval_width=60,
        random_seed1=seeds[0],
        random_seed2=seeds[1],
    )

    # Activity duration dists
    # These are the activities that are *not* dependent on patient attributes
    self.nurse_consult_time_dist = Exponential(
        mean=g.mean_n_consult_time, random_seed=seeds[2]
    )
    self.ct_time_dist = Exponential(mean=g.mean_n_ct_time, random_seed=seeds[3])
    self.sdec_time_dist = Exponential(mean=g.mean_n_sdec_time, random_seed=seeds[4])

    # Ward stay dists
    # These are the activities that are dependent on patient attributes
    self.i_ward_time_mrs_0_dist = Exponential(
        mean=g.mean_n_i_ward_time_mrs_0, random_seed=seeds[5]
    )
    self.i_ward_time_mrs_1_dist = Exponential(
        mean=g.mean_n_i_ward_time_mrs_1, random_seed=seeds[6]
    )
    self.i_ward_time_mrs_2_dist = Exponential(
        mean=g.mean_n_i_ward_time_mrs_2, random_seed=seeds[7]
    )
    self.i_ward_time_mrs_3_dist = Exponential(
        mean=g.mean_n_i_ward_time_mrs_3, random_seed=seeds[8]
    )
    self.i_ward_time_mrs_4_dist = Exponential(
        mean=g.mean_n_i_ward_time_mrs_4, random_seed=seeds[9]
    )
    self.i_ward_time_mrs_5_dist = Exponential(
        mean=g.mean_n_i_ward_time_mrs_5, random_seed=seeds[10]
    )

    self.ich_ward_time_mrs_0_dist = Exponential(
        mean=g.mean_n_ich_ward_time_mrs_0, random_seed=seeds[11]
    )
    self.ich_ward_time_mrs_1_dist = Exponential(
        mean=g.mean_n_ich_ward_time_mrs_1, random_seed=seeds[12]
    )
    self.ich_ward_time_mrs_2_dist = Exponential(
        mean=g.mean_n_ich_ward_time_mrs_2, random_seed=seeds[13]
    )
    self.ich_ward_time_mrs_3_dist = Exponential(
        mean=g.mean_n_ich_ward_time_mrs_3, random_seed=seeds[14]
    )
    self.ich_ward_time_mrs_4_dist = Exponential(
        mean=g.mean_n_ich_ward_time_mrs_4, random_seed=seeds[15]
    )
    self.ich_ward_time_mrs_5_dist = Exponential(
        mean=g.mean_n_ich_ward_time_mrs_5, random_seed=seeds[16]
    )

    self.tia_ward_time_dist = Exponential(
        mean=g.mean_n_tia_ward_time, random_seed=seeds[17]
    )
    self.non_stroke_ward_time_dist = Exponential(
        mean=g.mean_n_non_stroke_ward_time, random_seed=seeds[18]
    )

    # Patient Attribute Distributions
    self.onset_type_distribution_in_hours = DiscreteEmpirical(
        values=[0, 1, 2],
        freq=[
            g.in_hours_known_onset,
            g.in_hours_unknown_onset_inside_ctp,
            g.in_hours_unknown_onset_outside_ctp,
        ],  # equal weight of all possibilities
        random_seed=seeds[19],
    )

    self.onset_type_distribution_out_of_hours = DiscreteEmpirical(
        values=[0, 1, 2],
        freq=[
            g.out_of_hours_known_onset,
            g.out_of_hours_unknown_onset_inside_ctp,
            g.out_of_hours_unknown_onset_outside_ctp,
        ],  # equal weight of all possibilities
        random_seed=seeds[32],
    )

    self.mrs_type_distribution = Exponential(g.mean_mrs, random_seed=seeds[20])

    self.diagnosis_distribution = DiscreteEmpirical(
        values=list(range(0, 101)),  # 0 to 100 (upper is exclusive)
        freq=[1 for _ in range(101)],  # equal weight of all possibilities
        random_seed=seeds[21],
    )

    self.non_admission_distribution = DiscreteEmpirical(
        values=list(range(0, 101)),  # 0 to 100 (upper is exclusive)
        freq=[1 for _ in range(101)],  # equal weight of all possibilities
        random_seed=seeds[22],
    )

    # TODO: Is this the best distribution for this?
    # Per-patient diagnosis randomisation
    # self.ich_range = random.normalvariate(g.ich, 1)
    self.ich_range_distribution = Normal(g.ich, 1, random_seed=seeds[23])
    # self.i_range = max(random.normalvariate(g.i, 1), self.ich_range)
    self.i_range_distribution = Normal(g.i, 1, random_seed=seeds[24])
    # self.tia_range = max(random.normalvariate(g.tia, 1), self.i_range)
    self.tia_range_distribution = Normal(g.tia, 1, random_seed=seeds[25])
    # self.stroke_mimic_range = max(
    #     random.normalvariate(g.stroke_mimic, 1), self.tia_range
    # )
    self.stroke_mimic_range_distribution = Normal(
        g.stroke_mimic, 1, random_seed=seeds[26]
    )
    # self.non_stroke_range = max(
    #     random.normalvariate(g.stroke_mimic, 1), self.stroke_mimic_range
    # )
    self.non_stroke_range_distribution = Normal(
        g.stroke_mimic, 1, random_seed=seeds[27]
    )

    # TODO: Is this the best distribution for this?
    # Admission chance distributions
    # self.tia_admission_chance = random.normalvariate(g.tia_admission, 1)
    self.tia_admission_chance_distribution = Normal(
        g.tia_admission, 1, random_seed=seeds[28]
    )
    # self.stroke_mimic_admission_chance = random.normalvariate(
    #     g.stroke_mimic_admission, 1
    # )
    self.stroke_mimic_admission_chance_distribution = Normal(
        g.stroke_mimic_admission, 1, random_seed=seeds[29]
    )

    # MRS on discharge distribution
    self.mrs_reduction_during_stay = DiscreteEmpirical(
        values=[0, 1],
        freq=[1, 1],
        random_seed=seeds[30],
    )

    self.mrs_reduction_during_stay_thrombolysed = DiscreteEmpirical(
        values=[0, 1, 2],
        freq=[1, 1, 1],
        random_seed=seeds[31],
    )

    self.thrombolysis_contraindication_chance = Uniform(
        low=0, high=1, random_seed=seeds[32]
    )

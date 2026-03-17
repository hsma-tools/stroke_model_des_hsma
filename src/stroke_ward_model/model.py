"""
Implements the stroke ward simulation model, processes, and experiment logic.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import simpy

# import random
from sim_tools.trace import trace

# import simpy.resources
from stroke_ward_model.utils import minutes_to_ampm
from vidigi.resources import VidigiPriorityStore as PriorityResource
from vidigi.resources import VidigiStore as Resource

from stroke_ward_model.inputs import g
from stroke_ward_model.entities import Patient
from stroke_ward_model.distributions import initialise_distributions


# MARK: Model
# Class representing the model of the stroke assessment / treatment process
class Model:
    """
    A SimPy simulation model representing a stroke patient pathway.

    This class coordinates the simulation environment, manages clinical
    resources (nurses, scanners, and beds), and tracks performance metrics
    throughout the duration of a simulation run.

    Parameters
    ----------
    run_number : int
        The unique identifier for the specific simulation run.

    Attributes
    ----------
    env : simpy.core.Environment
        The SimPy environment in which the simulation is executed.
    patient_counter : int
        A running count of patients who have entered the system, used as a
        unique ID. This is shared across in-hours and out-of-hours arrivals.
    nurse : vidigi.resources.VidigiStore
        A SimPy resource representing stroke nurses available for assessment.
    ctp_scanner : vidigi.resources.VidigiPriorityStore
        A priority resource representing CTP scanners.
    sdec_bed : vidigi.resources.VidigiPriorityStore
        A priority resource representing Same Day Emergency Care (SDEC) beds.
    ward_bed : vidigi.resources.VidigiStore
        A SimPy resource representing standard ward beds.
    run_number : int
        The identifier for the current simulation iteration.
    results_df : pd.DataFrame
        A central data repository for patient-level results, including queue
        times, lengths of stay, and diagnostic statuses.
    sdec_freeze_counter : int
        Counter tracking the frequency of SDEC capacity freezes.
    mean_q_time_nurse : float
        The calculated average time patients spent queuing for a nurse.
    mean_q_time_ward : float
        The calculated average time patients spent queuing for a ward bed.
    mean_los_ward : float
        The average length of stay for patients admitted to the ward.
    thrombolysis_savings : float
        Aggregated metric representing the savings or benefits derived from
        thrombolysis.
    q_for_assessment : list
        A list tracking patients currently waiting in the assessment queue.
    nurse_q_graph_df : pd.DataFrame
        Time-series data for monitoring nurse queue lengths over time.
    sdec_occupancy : list
        Historical record of SDEC bed utilization.
    admission_avoidance : list
        Historical record of patients who avoided inpatient admission.
    ward_occupancy : list
        Historical record of ward bed utilization.
    non_admissions : list
        Record of patients classified as non-admissions.
    occupancy_graph_df : pd.DataFrame
        Time-series data for monitoring ward occupancy levels.
    patient_objects : list
        A collection of all `Patient` class instances created during the
        simulation.

    Notes
    -----
    GENAI declaration (SR): this docstring has been generated with the aid
    of Google Gemini Flash.
    All generated content has been thoroughly reviewed.
    """

    initialise_distributions = initialise_distributions

    # Constructor to set up the model for a run. We pass in a run number when
    # we create a new model.
    def __init__(self, run_number):
        # Create a SimPy environment
        self.env = simpy.Environment()

        # Create a patient counter for the first patient Generator
        self.patient_counter = 0

        # Create a SimPy resources to represent stroke nurses, ctp scanners,
        # sdec beds, and ward beds. Set in class g

        # SR: I have replaced these with the Vidigi equivalents, which are
        # functionally identical apart from also allowing the resource ID to be
        # tracked, which is useful for animation
        # self.nurse = simpy.Resource(self.env, capacity=g.number_of_nurses)
        self.nurse = Resource(self.env, num_resources=g.number_of_nurses)

        # self.ctp_scanner = simpy.PriorityResource(self.env, capacity=g.number_of_ctp)
        self.ctp_scanner = PriorityResource(self.env, num_resources=g.number_of_ctp)

        # self.sdec_bed = simpy.PriorityResource(self.env, capacity=g.sdec_beds)
        self.sdec_bed = PriorityResource(self.env, num_resources=g.sdec_beds)

        # self.ward_bed = simpy.Resource(self.env, capacity=g.number_of_ward_beds)
        self.ward_bed = Resource(self.env, num_resources=g.number_of_ward_beds)

        # Store the passed in run number
        self.run_number = run_number

        # Create a Pandas DataFrame that will store a majority of the results
        # with the patient ID as the index.
        self.results_df = pd.DataFrame()
        self.results_df["Patient ID"] = [1]
        self.results_df["Q Time Nurse"] = [0.0]
        self.results_df["Time with Nurse"] = [0.0]
        self.results_df["Q Time Ward"] = [0.0]
        self.results_df["Ward LOS"] = [0.0]
        self.results_df["Time with CTP"] = [0.0]
        self.results_df["Time with CT"] = [0.0]
        self.results_df["Time in SDEC"] = [0.0]
        self.results_df["CTP Status"] = [""]
        self.results_df["SDEC Status"] = [""]
        self.results_df["Thrombolysis"] = [""]
        self.results_df["SDEC Occupancy"] = [0.0]
        self.results_df["Admission Avoidance"] = [""]
        self.results_df["SDEC Savings"] = [0.0]
        self.results_df["MRS Type"] = [0.0]
        self.results_df["MRS DC"] = [0.0]
        self.results_df["MRS Change"] = [0.0]
        self.results_df["Onset Type"] = [0.0]
        self.results_df["Diagnosis Type"] = [""]
        self.results_df["Thrombolysis Savings"] = [0.0]
        self.results_df["Ward Occupancy"] = [0.0]
        self.results_df["Arrival Time"] = [0.0]
        self.results_df["Patient Gen 1 Status"] = [""]
        self.results_df["Patient Gen 2 Status"] = [""]
        self.results_df.set_index("Patient ID", inplace=True)

        # A variable to count the number of SDEC freezes
        self.sdec_freeze_counter = 0

        # Create a variable to store the mean queuing time for the nurse
        self.mean_q_time_nurse = 0

        # Create a variable to store the mean queuing time for the nurse
        self.max_q_time_nurse = 0

        # Create a variable to store the mean time waiting for a ward bed
        self.mean_q_time_ward = 0

        # Create a variable to store the max time waiting for a ward bed
        self.max_q_time_ward = 0

        # Create a variable to store the mean length of stay in the ward
        self.mean_los_ward = 0

        # Create a variable to store the mean number of thrombolysis savings
        self.thrombolysis_savings = 0

        # set up a list to store the queue for stroke nurse assessment
        self.q_for_assessment = []

        # a PD dataframe for the assessment queue graph
        self.nurse_q_graph_df = pd.DataFrame()
        self.nurse_q_graph_df["Time"] = [0.0]
        self.nurse_q_graph_df["Patients in Assessment Queue"] = [0.0]

        # a list that will store the number of patients in the SDEC
        self.sdec_occupancy = []

        # A list that will store the number of admissions avoided
        self.admission_avoidance = []

        # A list that will store the number of patients in the ward
        self.ward_occupancy = []

        # A list to store the number of patients avoiding admission
        self.non_admissions = []

        self.ward_occupancy_graph_df = pd.DataFrame()
        self.ward_occupancy_graph_df["Time"] = [0.0]
        self.ward_occupancy_graph_df["Occupancy"] = [0.0]
        self.ward_occupancy_graph_df["During Warm-Up"] = True

        self.sdec_occupancy_graph_df = pd.DataFrame()
        self.sdec_occupancy_graph_df["Time"] = [0.0]
        self.sdec_occupancy_graph_df["Occupancy"] = [0.0]
        self.sdec_occupancy_graph_df["During Warm-Up"] = True

        # A list to store the patient objects
        self.patient_objects = []

        # Add counts for each type of stroke patient to cross-check with this
        # in other places
        self.i_patients_count = 0
        self.ich_patients_count = 0
        self.tia_patients_count = 0
        self.stroke_mimic_patient_count = 0
        self.non_stroke_patient_count = 0

        # Add a count of patients who were able to be thrombolysed due to the
        # use of the CT perfusion scanner but otherwise would not have been
        # able to be thrombolysed
        self.additional_thrombolysis_from_ctp = 0

        self.initialise_distributions()

    def is_in_hours(self, time_of_day):
        start = g.in_hours_start * 60
        end = g.ooh_start * 60

        if start < end:
            # Normal case (does not cross midnight)
            return start <= time_of_day < end
        else:
            # Wraps over midnight
            return time_of_day >= start or time_of_day < end

    def is_out_of_hours(self, time_of_day):
        return not self.is_in_hours(time_of_day)

    # MARK: M: in-hours arrivals
    # A generator function for the patient arrivals in hours.
    def generator_patient_arrivals(self):
        """
        A SimPy process generator that handles "in-hours" patient arrivals.

        This function runs as a continuous loop. It checks if the current
        simulation time is within daytime operating hours (0-960 minutes
        relative to the start of a 1440-minute day).

        If in-hours, it:

        1. Updates global arrival flags.

        2. Instantiates a new Patient object.

        3. Records trace information.

        4. Triggers the `stroke_assessment` process for the patient.

        5. Samples an inter-arrival time and yields a timeout.

        If out-of-hours, it yields a small timeout before checking again.

        Arrival rates are determined by `random.expovariate` using the
        `g.patient_inter_day` parameter. NOTE that this does not use the
        `g.patient_inter_day` parameter directly, and instead uses it
        alongside a rate modifier - careful inspection of the code to
        understand the impacts of changing `g.patient_inter_day` is
        recommended, and this may be adjusted in a future version of the model.

        Patients generated here have their `arrived_ooh` attribute set to False.

        This process triggers the `stroke_assessment` process for every
        newly created patient.

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.
        """
        while True:
            sampled_inter = self.patient_inter_dist.sample(simulation_time=self.env.now)

            # Freeze this instance of this function in place until the
            # inter-arrival time has elapsed.
            yield self.env.timeout(sampled_inter)

            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"⏲️ Next patient arriving in {sampled_inter:.1f} minutes",
                identifier=self.patient_counter,
                config=g.trace_config,
            )

            # Increment the patient counter by 1 for each new patient
            self.patient_counter += 1

            # Create a new patient - an instance of the Patient Class we
            # defined above. patient counter ID passed from above to patient
            # class.
            p = Patient(self.patient_counter)
            self.patient_objects.append(p)
            if self.env.now < g.warm_up_period:
                p.generated_during_warm_up = True
            else:
                p.generated_during_warm_up = False

            time_of_day = self.env.now % 1440

            if self.is_in_hours(time_of_day):
                # Change the Global Class variable
                g.patient_arrival_gen_1 = True
                g.patient_arrival_gen_2 = False

                p.onset_type = self.onset_type_distribution_in_hours.sample()

                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"☀️ IN-HOURS Patient {p.id} generated at {minutes_to_ampm(int(self.env.now % 1440))}. Diagnosis: {p.diagnosis}. MRS type: {p.mrs_type}.",
                    identifier=p.id,
                    config=g.trace_config,
                )

                p.arrived_ooh = False

            elif self.is_out_of_hours(time_of_day):
                # Change the Global Class variable
                g.patient_arrival_gen_1 = False
                g.patient_arrival_gen_2 = True

                p.onset_type = self.onset_type_distribution_out_of_hours.sample()

                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"🌙 OUT OF HOURS Patient {p.id} generated at {minutes_to_ampm(int(self.env.now % 1440))}. Diagnosis: {p.diagnosis}. MRS type: {p.mrs_type}.",
                    identifier=p.id,
                    config=g.trace_config,
                )

                p.arrived_ooh = True

            # Tell SimPy to start the stroke assessment function with
            # this patient (the generator function that will model the
            # patient's journey through the system)
            self.env.process(self.stroke_assessment(p))

    # MARK: M: Obstruct CTP
    def obstruct_ctp(self):
        """
        Simulates periodic CTP scanner unavailability (off time).

        This process acts as a "blocker" by requesting the CTP scanner resource
        with a priority of -1. Since patients typically have a priority of 1,
        this process effectively preempts the queue, preventing patients from
        using the scanners during this period.

        The scanner will not stop a scan that is already in progress;
        it waits for the current user to finish before taking the
        resource offline.

        Frequencies and durations are governed by `g.ctp_unav_freq`
        and `g.ctp_unav_time`.

        Yields
        ------
        simpy.events.Timeout
            Initial offset for opening hours and subsequent intervals
            between downtime events.
        simpy.events.ResourceRequest
            A high-priority request to seize the CTP scanner and take
            it "offline."

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.

        """
        # SR: Add initial offset
        # SR: Patient generators have also been updated
        # to match with how this is working
        yield self.env.timeout(g.ctp_opening_hour * 60)

        while True:
            yield self.env.timeout(g.ctp_unav_freq)
            # Once elapsed, this generator requests the ctp scanner with
            # a priority of -1. As the patient priority is set at 1
            # the scanner will take priority over any patients waiting.
            # This method also means that the scanner won't stop mid scan.
            g.ctp_unav = True
            with self.ctp_scanner.request(priority=-1) as req:
                yield req
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"🔬 CTP scanner OFFLINE at {minutes_to_ampm(int(self.env.now % 1440))}",
                    identifier=self.patient_counter,
                    config=g.trace_config,
                )
                # Freeze with the scanners held in place for the unavailability
                # time, in the model this means patients admitted in this time
                # will not have a ctp scan.
                # freq and unav times are set in the g class
                yield self.env.timeout(g.ctp_unav_time)
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"🔬 CTP scanner back ONLINE at {minutes_to_ampm(int(self.env.now % 1440))}",
                    identifier=self.patient_counter,
                    config=g.trace_config,
                )
                g.ctp_unav = False

    # MARK: M: Obstruct SDEC
    def obstruct_sdec(self):
        """
        Simulates the scheduled closure or unavailability of the SDEC unit.

        Similar to the CTP obstruction, this process seizes an SDEC bed
        at a high priority (-1) for a defined duration. This models the
        real-world scenario where the SDEC unit closes at night or
        during specific hours, forcing patients to bypass this pathway.

        If a closure occurs after the simulation warm-up period, the
        `sdec_freeze_counter` is incremented.

        Patients arriving while the SDEC is "obstructed" will be
        unable to access SDEC resources.

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.
        """
        # SR: Add initial offset
        # SR: Patient generators have also been updated
        # to match with how this is working
        yield self.env.timeout(g.sdec_opening_hour * 60)

        while True:
            yield self.env.timeout(g.sdec_unav_freq)
            g.sdec_unav = True

            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"🏥 SDEC CLOSES at {minutes_to_ampm(int(self.env.now % 1440))}. Occupancy at closure: {len(self.sdec_occupancy)} of {g.sdec_beds} beds.",
                identifier=self.patient_counter,
                config=g.trace_config,
            )

            # Freeze with the SDEC held in place for the unavailability
            # time, in the model this means patients admitted in this time
            # will not have passed through the SDEC.
            # freq and unav times are set in the g class
            yield self.env.timeout(g.sdec_unav_time)

            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"🏥 SDEC OPENS at {minutes_to_ampm(int(self.env.now % 1440))}. Occupancy at opening: {len(self.sdec_occupancy)} of {g.sdec_beds} beds.",
                identifier=self.patient_counter,
                config=g.trace_config,
            )

            g.sdec_unav = False

            if self.env.now > g.warm_up_period:
                self.sdec_freeze_counter += 1

    # MARK: M: Set patient attributes #
    def set_patient_attributes(self, patient):
        """
        Sets a series of randomised per-patient attributes

        Parameters
        ----------
        patient : Instance of class `Patient`
            One single unique patient object.
        """
        # For now, no-one gets thrombectomy
        patient.thrombectomy = False

        # Populate various patient attributes
        # patient.mrs_type = min(round(random.expovariate(1.0 / g.mean_mrs)), 5)
        patient.mrs_type = min(round(self.mrs_type_distribution.sample()), 5)
        # patient.diagnosis = random.randint(0, 100)
        patient.diagnosis = self.diagnosis_distribution.sample()
        # patient.non_admission = random.randint(0, 100)
        patient.non_admission = self.non_admission_distribution.sample()

        # Define threshold for admission for TIA + stroke mimic patients
        self.tia_admission_chance = self.tia_admission_chance_distribution.sample()

        self.stroke_mimic_admission_chance = (
            self.stroke_mimic_admission_chance_distribution.sample()
        )

        # This code introduces a slight element of randomness into the patient's
        # diagnosis.

        # self.ich_range = random.normalvariate(g.ich, 1)
        self.ich_range = self.ich_range_distribution.sample()
        # self.i_range = max(random.normalvariate(g.i, 1), self.ich_range)
        self.i_range = max(self.i_range_distribution.sample(), self.ich_range)
        # self.tia_range = max(random.normalvariate(g.tia, 1), self.i_range)
        self.tia_range = max(self.tia_range_distribution.sample(), self.i_range)
        # self.stroke_mimic_range = max(
        #     random.normalvariate(g.stroke_mimic, 1), self.tia_range
        # )
        self.stroke_mimic_range = max(
            self.stroke_mimic_range_distribution.sample(), self.tia_range
        )
        # self.non_stroke_range = max(
        #     random.normalvariate(g.stroke_mimic, 1), self.stroke_mimic_range
        # )
        self.non_stroke_range = max(
            self.non_stroke_range_distribution.sample(), self.stroke_mimic_range
        )

        if patient.diagnosis <= self.ich_range:
            patient.patient_diagnosis = 0
            patient.patient_diagnosis_type = "ICH"
            self.ich_patients_count += 1
        elif patient.diagnosis <= self.i_range:
            patient.patient_diagnosis = 1
            patient.patient_diagnosis_type = "I"
            self.i_patients_count += 1
        elif patient.diagnosis <= self.tia_range:
            patient.patient_diagnosis = 2
            patient.patient_diagnosis_type = "TIA"
            self.tia_patients_count += 1
        elif patient.diagnosis <= self.stroke_mimic_range:
            patient.patient_diagnosis = 3
            patient.patient_diagnosis_type = "Stroke Mimic"
            self.stroke_mimic_patient_count += 1
        # SR - this was changed from an elif as was resulting in patients in
        # between the two thresholds not getting allocated a diagnosis, which
        # causes errors elsewhere
        else:
            patient.patient_diagnosis = 4
            patient.patient_diagnosis_type = "Non Stroke"
            self.non_stroke_patient_count += 1

        # The below code records the patients diagnosis attribute, this is
        # added to the DF to check the diagnosis code is working correctly.
        # SR - refactored recording of diagnosis type in results df as that's
        # now recorded as a patient attribute earlier
        if self.env.now > g.warm_up_period:
            self.results_df.at[patient.id, "Diagnosis Type"] = (
                patient.patient_diagnosis_type
            )

            self.results_df.at[patient.id, "Onset Type"] = patient.onset_type

            # This code adds the Patient's MRS to the DF, this can be used to
            # check all code that interacts with this runs correctly.
            self.results_df.at[patient.id, "MRS Type"] = patient.mrs_type

    # MARK: M: Stroke assessment
    # A generator function that represents the pathway for a patient going
    # through the stroke assessment process.
    # The patient object is passed in to the generator function so we can
    # extract information from / record information to it
    def stroke_assessment(self, patient):
        """
        Simulates the full assessment and treatment pathway for patients
        in a stroke pathway.

        Parameters
        ----------
        patient : Instance of class `Patient`
            One single unique patient object.
        """
        self.set_patient_attributes(patient)

        trace(
            time=self.env.now,
            debug=g.show_trace,
            msg=f"Patient {patient.id} Patient Diagnosis (category 1-4): {patient.patient_diagnosis}.",
            identifier=patient.id,
            config=g.trace_config,
        )

        # Record the time the patient started queuing for a nurse
        start_q_nurse = self.env.now
        patient.nurse_q_start_time = self.env.now

        self.q_for_assessment.append(patient)

        # Add the arrival time to the main DF
        # This is partly to test if the
        # patient arrival times mirror the real world data
        # SR: this is also now used for animation generation

        patient.clock_start = self.env.now

        if self.env.now > g.warm_up_period:
            self.results_df.at[patient.id, "Arrival Time"] = patient.clock_start

            self.results_df.at[patient.id, "Patient Gen 1 Status"] = (
                g.patient_arrival_gen_1
            )

            self.results_df.at[patient.id, "Patient Gen 2 Status"] = (
                g.patient_arrival_gen_2
            )

        #######################################################################
        # MARK: Nurse triage
        # This code says request a nurse resource, and do all of the following
        # block of code with that nurse resource held in place (and therefore
        # not usable by another patient)
        ########################################################################
        with self.nurse.request() as req:
            # Freeze the function until the request for a nurse can be met.
            # The patient is currently queuing.
            nurse_attending = yield req
            # SR - have added recording of the resource ID that's possible as
            # it's now using vidigi resources
            patient.nurse_attending_id = nurse_attending.id_attribute
            patient.nurse_triage_start_time = self.env.now

            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"👩‍⚕️ Patient {patient.id} is being seen by a nurse at {minutes_to_ampm(int(self.env.now % 1440))}.",
                identifier=patient.id,
                config=g.trace_config,
            )

            # Control is passed back to the generator function once the request
            # is met for a nurse. As the queue for the nurse is finished
            # the patient then leaves the assessment queue list.

            end_q_nurse = self.env.now

            self.q_for_assessment.remove(patient)

            # The code below checks if the warm up period has passed before
            # entering data into the df, this code exists when ever data is
            # recorded

            if self.env.now > g.warm_up_period:
                self.nurse_q_graph_df.loc[len(self.nurse_q_graph_df)] = [
                    self.env.now,
                    len(self.q_for_assessment),
                ]

            # Calculate the time this patient was queuing for the nurse, and
            # record it in the patient's attribute
            patient.q_time_nurse = end_q_nurse - start_q_nurse

            # The below code creates a random action time for the nurse based
            # on the mean in g class, and assigns it ot a variable. Currently
            # using a Exponential distribution but might need to switch to
            # a Log normal one (though the intense variation in the real life
            # consult time might mean a exponetial distribution is better)
            # sampled_nurse_act_time = random.expovariate(1.0 / g.mean_n_consult_time)
            sampled_nurse_act_time = self.nurse_consult_time_dist.sample()

            # Freeze this function in place for the activity time we sampled
            # above.  This is the patient spending time with the nurse.
            yield self.env.timeout(sampled_nurse_act_time)

            patient.nurse_triage_end_time = self.env.now

            # In the .at function below, the first value is the row, the second
            # value is the column in which to add data. The final value is the
            # the data that is to be added to the DF, in this case the Nurse
            # Q time

            if self.env.now > g.warm_up_period:
                self.results_df.at[patient.id, "Q Time Nurse"] = patient.q_time_nurse
                self.results_df.at[patient.id, "Time with Nurse"] = (
                    sampled_nurse_act_time
                )

        # TIME WITH NURSE ENDS - NURSE RESOURCE RELEASED HERE FOR NEXT PATIENT

        # MARK: CT and CT Perfusion Scanner Use
        # The if formula below checks to see if the CTP scanner is active
        # and if it is the following code is followed including updating the
        # patient advanced CT pathway attribute

        if g.ctp_unav == False:
            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"➡️ Patient {patient.id} sent on CTP scanner pathway at {minutes_to_ampm(int(self.env.now % 1440))}.",
                identifier=patient.id,
                config=g.trace_config,
            )

            patient.ctp_scan_start_time = self.env.now

            patient.advanced_ct_pathway = True

            # Randomly sample the mean ct time, as with above this may need to
            # be updated to a log normal distribution

            # sampled_ctp_act_time = random.expovariate(1.0 / g.mean_n_ct_time)
            sampled_ctp_act_time = self.ct_time_dist.sample()
            patient.ctp_duration = sampled_ctp_act_time
            # Freeze this function in place for the activity time that was
            # sampled above.
            yield self.env.timeout(sampled_ctp_act_time)

            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"➡️ Patient {patient.id} finishes CTP scan at {minutes_to_ampm(int(self.env.now % 1440))} after {sampled_ctp_act_time:.1f} minutes.",
                identifier=patient.id,
                config=g.trace_config,
            )

            patient.ctp_scan_end_time = self.env.now

            # Add data to the DF afer the warm up period.

            if self.env.now > g.warm_up_period:
                self.results_df.at[patient.id, "Time with CTP"] = sampled_ctp_act_time

        # If the CTP pathway is not active the below code runs, it is the same
        # as the above however adds data to a different column and the patient
        # advanced CT pathway remains False.

        else:
            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"🚫 Patient {patient.id} NOT sent on CTP scanner pathway - normal CT scan commencing at {minutes_to_ampm(int(self.env.now % 1440))}.",
                identifier=patient.id,
                config=g.trace_config,
            )

            patient.advanced_ct_pathway = False

            patient.ct_scan_start_time = self.env.now

            # sampled_ct_act_time = random.expovariate(1.0 / g.mean_n_ct_time)
            sampled_ct_act_time = self.ct_time_dist.sample()
            patient.ct_duration = sampled_ct_act_time

            yield self.env.timeout(sampled_ct_act_time)

            trace(
                time=self.env.now,
                debug=g.show_trace,
                msg=f"🚫 Patient {patient.id} finishes normal CT scan at {minutes_to_ampm(int(self.env.now % 1440))} after {sampled_ct_act_time:.1f} minutes.",
                identifier=patient.id,
                config=g.trace_config,
            )

            patient.ct_scan_end_time = self.env.now

            if self.env.now > g.warm_up_period:
                self.results_df.at[patient.id, "Time with CT"] = sampled_ct_act_time

        # The below code records the status of both the CTP pathway.
        # Both exist as generators and this data is record to ensure they are
        # operating as expected.

        if self.env.now > g.warm_up_period:
            self.results_df.at[patient.id, "CTP Status"] = g.ctp_unav

        #############################
        # MARK: Thrombolysis
        #############################
        # The below code checks the patient's attributes to see if the
        # thrombolysis attribute should be changed to True, this is based off
        # the patient diagnosis, onset type and mrs type. There are different
        # conditions depending on if CTP is available or not.

        # If CTP scanner is not available, only patients who have a known stroke onset time
        # are eligible for thrombolysis. MRS must also be 1 or above (i.e. simplistically,
        # some disability must be present for risk/benefit of thrombolysis to be worthwhile.)
        if (
            patient.patient_diagnosis == 1
            and patient.onset_type == 0
            and patient.mrs_type > 0
        ):
            if (
                self.thrombolysis_contraindication_chance.sample()
                > g.probability_of_thrombolysis_contraindication
            ):
                patient.thrombolysis = True
            else:
                patient.thrombolysis = False
                patient.thrombolysis_contraindicated = True

        # If the CTP scanner is available, then patients with an unknown onset but within the thrombolysable
        # window are considered eligible for thrombolysis. The same rules apply to the disability.
        elif (
            patient.patient_diagnosis == 1
            and patient.onset_type == 1
            and patient.advanced_ct_pathway == True
            and patient.mrs_type > 0
        ):
            if (
                self.thrombolysis_contraindication_chance.sample()
                > g.probability_of_thrombolysis_contraindication
            ):
                patient.thrombolysis = True
                self.additional_thrombolysis_from_ctp += 1
                patient.thrombolysis_enabled_by_ctp = True
            else:
                patient.thrombolysis = False
                patient.thrombolysis_contraindicated = True

        else:
            patient.thrombolysis = False

        # Thrombolysis status is added to the DF, this is mainly used to check
        # if it is being applied correctly.

        if self.env.now > g.warm_up_period:
            self.results_df.at[patient.id, "Thrombolysis"] = patient.thrombolysis

        #########################
        # MARK: SDEC Admission
        #########################

        # The below code records the status of both the SDEC pathway.
        # Both exist as generators and this data is recorded to ensure they are
        # operating as expected.

        if self.env.now > g.warm_up_period:
            self.results_df.at[patient.id, "SDEC Status"] = g.sdec_unav

        # The if statement below checks if the SDEC pathway is active at this
        # given time and if there is space in the SDEC itself.

        if g.sdec_unav:
            patient.sdec_running_when_required = False
            patient.sdec_full_when_required = False
        else:
            patient.sdec_running_when_required = True

            if len(self.sdec_occupancy) < g.sdec_beds:
                patient.sdec_full_when_required = False
            else:
                patient.sdec_full_when_required = True

        # Branch for if SDEC is available
        # SR: Note that I have changed the check from <= to < (so that patients
        # are only allowed to request a bed when a bed is free)
        if g.sdec_unav == False and len(self.sdec_occupancy) < g.sdec_beds:
            # If the conditions above are met the patient attribute for the
            # SDEC are changed to True and the patient is added to the SDEC
            # occupancy list.

            # SR: The request is only necessary here for being able to
            # determine which bed ends up being used, which we require for
            # animating it correctly. However, we still need to hold it for the
            # duration of this code block so that someone else doesn't end up
            # in the same bed!
            with self.sdec_bed.request() as req:
                sdec_bed_used = yield req
                patient.sdec_bed_id = sdec_bed_used.id_attribute

                patient.sdec_admit_time = self.env.now

                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"🛏️🏎️ Patient {patient.id} admitted to SDEC (occupancy before admission: {len(self.sdec_occupancy)} of {g.sdec_beds} SDEC beds) at {minutes_to_ampm(int(self.env.now % 1440))}.",
                    identifier=patient.id,
                    config=g.trace_config,
                )

                self.sdec_occupancy.append(patient)

                # The below code record the SDEC Occupancy as the patient passes
                # this point to ensure it is working as expected.

                if self.env.now > g.warm_up_period:
                    self.results_df.at[patient.id, "SDEC Occupancy"] = len(
                        self.sdec_occupancy
                    )

                    self.sdec_occupancy_graph_df.loc[
                        len(self.sdec_occupancy_graph_df)
                    ] = [
                        self.env.now,
                        len(self.sdec_occupancy),
                        False,
                    ]
                else:
                    self.sdec_occupancy_graph_df.loc[
                        len(self.sdec_occupancy_graph_df)
                    ] = [
                        self.env.now,
                        len(self.sdec_occupancy),
                        True,
                    ]

                patient.sdec_pathway = True

                ###########################################################
                # ADMISSION AVOIDANCE
                # This code checks if the patient is eligible for admission
                # avoidance depending on if therapy support is enabled.
                ###########################################################
                if g.therapy_sdec == False:
                    if (
                        # patient.patient_diagnosis < 2 # SR: CHANGED THIS 17/3 PENDING CONFIRMATION
                        patient.patient_diagnosis == 1
                        and patient.mrs_type < 2
                        and patient.thrombolysis == False
                    ):
                        patient.admission_avoidance = True
                        patient.admission_avoidance_because_of_therapy = False

                elif g.therapy_sdec == True:
                    if (
                        # patient.patient_diagnosis < 2 # SR: CHANGED THIS 17/3 PENDING CONFIRMATION
                        patient.patient_diagnosis == 1
                        and patient.mrs_type <= 3
                        and patient.thrombolysis == False
                    ):
                        patient.admission_avoidance = True

                        if patient.mrs_type > 1:
                            patient.admission_avoidance_because_of_therapy = True
                        else:
                            patient.admission_avoidance_because_of_therapy = False
                else:
                    patient.admission_avoidance = False
                    patient.admission_avoidance_because_of_therapy = False

                ##########################################################
                # Non-admission - non-stroke, TIA and stroke mimic       #
                ##########################################################
                # For patients who have TIA, non-stroke or stroke mimic,
                # they have a high chance of avoiding admission, but this
                # is not counted in the same way

                if (
                    patient.non_admission >= self.tia_admission_chance
                    and patient.patient_diagnosis == 2
                ):
                    patient.admission_avoidance = False
                    patient.admission_avoidance_because_of_therapy = False
                    patient.non_admitted_tia_ns_sm = True

                    trace(
                        time=self.env.now,
                        debug=g.show_trace,
                        msg=f"↩️ TIA Patient {patient.id} avoided admission.",
                        identifier=patient.id,
                        config=g.trace_config,
                    )

                elif (
                    patient.non_admission >= self.stroke_mimic_admission_chance
                    and patient.patient_diagnosis > 2
                ):
                    patient.admission_avoidance = False
                    patient.admission_avoidance_because_of_therapy = False
                    patient.non_admitted_tia_ns_sm = True
                    trace(
                        time=self.env.now,
                        debug=g.show_trace,
                        msg=f"↩️ Stroke mimic or non-stroke Patient {patient.id} (diagnosis {patient.diagnosis}) avoided admission.",
                        identifier=patient.id,
                        config=g.trace_config,
                    )
                else:
                    patient.non_admitted_tia_ns_sm = False

                # Calculate SDEC stay time from exponential
                # sampled_sdec_stay_time = random.expovariate(1.0 / g.mean_n_sdec_time)
                sampled_sdec_stay_time = self.sdec_time_dist.sample()

                # Add patient SDEC LOS to their patient object
                patient.sdec_los = sampled_sdec_stay_time

                # Freeze this function in place for the activity time we sampled
                # above.
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"Patient {patient.id} (diagnosis {patient.diagnosis} ({patient.patient_diagnosis}), MRS type {patient.mrs_type}) will be in SDEC for {sampled_sdec_stay_time:.1f} minutes ({(sampled_sdec_stay_time / 60 / 24):.1f} days).",
                    identifier=patient.id,
                    config=g.trace_config,
                )

                yield self.env.timeout(sampled_sdec_stay_time)

                # This code checks if the ward is full, if this is the case the
                # patient will not be released from the SDEC, thus impeding it use

                if (
                    not patient.admission_avoidance
                    and not patient.non_admitted_tia_ns_sm
                ):
                    while len(self.ward_occupancy) >= g.number_of_ward_beds:
                        yield self.env.timeout(1)

                # Once the above code is complete the patient is removed from the
                # SDEC occupancy list.

                self.sdec_occupancy.remove(patient)
                patient.sdec_discharge_time = self.env.now

                # Code to record the SDEC stay time in the results DataFrame.
                if self.env.now > g.warm_up_period:
                    self.results_df.at[patient.id, "Time in SDEC"] = (
                        sampled_sdec_stay_time
                    )

                # MARK: Discharged from SDEC
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"🏎️ Patient {patient.id} discharged from SDEC at {minutes_to_ampm(int(self.env.now % 1440))} after {patient.sdec_los:.1f} minutes ({(patient.sdec_los / 60 / 24):.1f} days). Occupancy after discharge: {len(self.sdec_occupancy)} of {g.sdec_beds} SDEC beds",
                    identifier=patient.id,
                    config=g.trace_config,
                )

            ##########################################
            # MARK: Admission Avoidance cost savings
            ##########################################
            # This code add information regarding the patients admission avoidance.

            if patient.admission_avoidance == True and patient.patient_diagnosis < 2:
                # Regardless of whether the warm-up has passed, recording in
                # patient object that this patient's journey was completed
                patient.exit_time = self.env.now
                patient.journey_completed = True

                # Patients with a True admission avoidance are added to a list
                # that is used to calculate the savings from the avoided admissions
                # (only if outside of the warm-up period)
                if (
                    patient.admission_avoidance == True
                    and self.env.now > g.warm_up_period
                ):
                    self.admission_avoidance.append(patient)

                    # We also add their savings to the dataframe
                    self.results_df.at[patient.id, "SDEC Savings"] = (
                        g.inpatient_bed_cost * g.sdec_bed_day_saving
                    )

            # This code exists after the admission avoidance code so they
            # are not added to the admission avoidance list, as that should
            # only be for SDEC patients who avoid admission.
            # This code ensures that these patients get an exit time

            if patient.non_admitted_tia_ns_sm == True:
                patient.exit_time = self.env.now
                patient.journey_completed = True

        ###############################################
        # MARK: SDEC Full or closed
        # Branch of logic for if SDEC is not available
        ###############################################
        else:
            patient.sdec_pathway = False

            # If SDEC not available, we will see some % of TIA and ED patients be returned
            # to ED at this stage (i.e. outside of the modelled part of the system) and they
            # won't be seen again.
            if (
                patient.non_admission >= self.tia_admission_chance
                and patient.patient_diagnosis == 2
            ):
                patient.admission_avoidance = False
                patient.non_admitted_tia_ns_sm = True
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"↩️ TIA Patient {patient.id} avoided admission.",
                    identifier=patient.id,
                    config=g.trace_config,
                )

            elif (
                patient.non_admission >= self.stroke_mimic_admission_chance
                and patient.patient_diagnosis > 2
            ):
                patient.admission_avoidance = False
                patient.admission_avoidance_because_of_therapy = False
                patient.non_admitted_tia_ns_sm = True
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"↩️ Stroke mimic or non-stroke Patient {patient.id} (diagnosis {patient.diagnosis}) avoided admission.",
                    identifier=patient.id,
                    config=g.trace_config,
                )
            else:
                patient.non_admitted_tia_ns_sm = False

            if patient.non_admitted_tia_ns_sm == True:
                patient.exit_time = self.env.now
                patient.journey_completed = True

        #####################################################################
        # MARK: Ward Admission
        # once all the above code has been run all patients who will not admit
        # have a True admission avoidance attribute. For all the patients that
        # remain false, the below code will run simulating the admission to the
        # ward.
        ############################################################################

        # TODO: sampled ward activity time is done after a bed is obtained.
        # TODO: this is what is recorded as LOS within the model, but arguably
        # the 'TRUE' LOS is therefore longer in the model as
        # or is LOS in these cases sampled from stroke ward LOS only?
        # is LOS increased by spending time on an 'inappropriate' ward in the
        # real world, and if so, does this need to be reflected here?

        if not patient.admission_avoidance and not patient.non_admitted_tia_ns_sm:
            # Anyone who has made it to here has definitely not avoided admission
            patient.admission_avoidance = False
            patient.admission_avoidance_because_of_therapy = False

            # These code assigns a time to the start q variable. In stroke care
            # delays can have serious consequence so modeling this is very
            # important as flow disruption are a common issue.

            start_q_ward = self.env.now
            patient.ward_q_start_time = self.env.now

            # Request the ward bed and hold the patient in a queue until this
            # is met.

            with self.ward_bed.request() as req:
                ward_bed_used = yield req
                patient.ward_bed_id = ward_bed_used.id_attribute
                # Add patient to the ward list

                self.ward_occupancy.append(patient)
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"🛏️ Patient {patient.id} admitted to main ward at {minutes_to_ampm(int(self.env.now % 1440))}. Occupancy after admission: {len(self.ward_occupancy)} of {g.number_of_ward_beds} ward beds",
                    identifier=patient.id,
                    config=g.trace_config,
                )

                patient.ward_admit_time = self.env.now

                if self.env.now > g.warm_up_period:
                    self.results_df.at[patient.id, "Ward Occupancy"] = len(
                        self.ward_occupancy
                    )

                if self.env.now > g.warm_up_period:
                    self.ward_occupancy_graph_df.loc[
                        len(self.ward_occupancy_graph_df)
                    ] = [
                        self.env.now,
                        len(self.ward_occupancy),
                        False,
                    ]
                else:
                    self.ward_occupancy_graph_df.loc[
                        len(self.ward_occupancy_graph_df)
                    ] = [
                        self.env.now,
                        len(self.ward_occupancy),
                        True,
                    ]

                # The patient attribute for the queuing time in the ward is
                # assigned here.

                end_q_ward = self.env.now

                patient.q_time_ward = end_q_ward - start_q_ward

                if patient.patient_diagnosis_type in ["ICH", "I"]:
                    sampled_ward_act_time = getattr(
                        self,
                        f"{patient.patient_diagnosis_type.lower()}_ward_time_mrs_{patient.mrs_type}_dist",
                    ).sample_within_bounds(minimum=1)

                    # Determine MRS at discharge
                    if patient.mrs_type == 0:
                        patient.mrs_discharge = patient.mrs_type
                    elif patient.thrombolysis and patient.mrs_type >= 2:
                        patient.mrs_discharge = (
                            patient.mrs_type
                            - self.mrs_reduction_during_stay_thrombolysed.sample()
                        )
                    else:
                        patient.mrs_discharge = (
                            patient.mrs_type - self.mrs_reduction_during_stay.sample()
                        )

                    # Handle thrombolysis path for ischaemic stroke
                    if patient.thrombolysis:
                        sampled_ward_act_time_thrombolysis = (
                            sampled_ward_act_time * g.thrombolysis_los_save
                        )
                        trace(
                            time=self.env.now,
                            debug=g.show_trace,
                            msg=f"💉 Patient {patient.id} (diagnosis {patient.diagnosis} ({patient.patient_diagnosis_type}), MRS type {patient.mrs_type}) THROMBOLYSED. Will be in ward for {sampled_ward_act_time_thrombolysis:.1f} minutes ({(sampled_ward_act_time_thrombolysis / 24 / 60):.1f} days).",
                            identifier=patient.id,
                            config=g.trace_config,
                        )
                        patient.ward_los_thrombolysis = (
                            sampled_ward_act_time_thrombolysis
                        )
                        yield self.env.timeout(sampled_ward_act_time_thrombolysis)
                        if (
                            self.env.now > g.warm_up_period
                            and patient.thrombolysis_enabled_by_ctp
                        ):
                            if g.short_term_thrombolysis_savings:
                                self.results_df.at[
                                    patient.id, "Thrombolysis Savings"
                                ] = (
                                    (
                                        (
                                            sampled_ward_act_time
                                            - sampled_ward_act_time_thrombolysis
                                        )
                                        / 60
                                    )
                                    / 24
                                ) * g.inpatient_bed_cost_thrombolysis
                            else:
                                self.results_df.at[
                                    patient.id, "Thrombolysis Savings"
                                ] = g.fixed_thrombolysis_saving_amount_long_term
                    else:
                        trace(
                            time=self.env.now,
                            debug=g.show_trace,
                            msg=f"Patient {patient.id} (diagnosis {patient.diagnosis} ({patient.patient_diagnosis_type}), MRS type {patient.mrs_type}) will be in ward for {sampled_ward_act_time:.1f} minutes ({(sampled_ward_act_time / 60 / 24):.1f} days).",
                            identifier=patient.id,
                            config=g.trace_config,
                        )
                        patient.ward_los = sampled_ward_act_time
                        yield self.env.timeout(sampled_ward_act_time)

                elif patient.patient_diagnosis_type == "TIA":
                    sampled_ward_act_time = (
                        self.tia_ward_time_dist.sample_within_bounds(minimum=1)
                    )
                    trace(
                        time=self.env.now,
                        debug=g.show_trace,
                        msg=f"Patient {patient.id} (diagnosis {patient.diagnosis} ({patient.patient_diagnosis_type}), MRS type {patient.mrs_type}) will be in ward for {sampled_ward_act_time:.1f} minutes ({(sampled_ward_act_time / 60 / 24):.1f} days).",
                        identifier=patient.id,
                        config=g.trace_config,
                    )
                    patient.ward_los = sampled_ward_act_time
                    yield self.env.timeout(sampled_ward_act_time)

                else:  # diag > 2 — stroke mimic / non-stroke
                    sampled_ward_act_time = (
                        self.non_stroke_ward_time_dist.sample_within_bounds(minimum=1)
                    )
                    trace(
                        time=self.env.now,
                        debug=g.show_trace,
                        msg=f"Patient {patient.id} (diagnosis {patient.diagnosis} ({patient.patient_diagnosis_type}), MRS type {patient.mrs_type}) will be in ward for {sampled_ward_act_time:.1f} minutes ({(sampled_ward_act_time / 60 / 24):.1f} days).",
                        identifier=patient.id,
                        config=g.trace_config,
                    )
                    patient.ward_los = sampled_ward_act_time
                    yield self.env.timeout(sampled_ward_act_time)

                patient.ward_discharge_time = self.env.now
                self.ward_occupancy.remove(patient)

                # Relevent information is recorded in the results DataFrame.
                if self.env.now > g.warm_up_period:
                    self.results_df.at[patient.id, "Q Time Ward"] = patient.q_time_ward

                # TODO: SR: I've tweaked this to take whichever of the ward_los or thrombolysis los is generated
                # TODO SR: It would be better to take a more robust approach to this step.
                try:
                    final_ward_los = sampled_ward_act_time
                except:
                    final_ward_los = sampled_ward_act_time_thrombolysis

                if self.env.now > g.warm_up_period:
                    self.results_df.at[patient.id, "Ward LOS"] = final_ward_los

                    self.results_df.at[patient.id, "MRS DC"] = patient.mrs_discharge

                    self.results_df.at[patient.id, "MRS Change"] = (
                        patient.mrs_type - patient.mrs_discharge
                    )

                # MARK: Discharged from main ward
                trace(
                    time=self.env.now,
                    debug=g.show_trace,
                    msg=f"🚗 Patient {patient.id} discharged from main ward at {minutes_to_ampm(int(self.env.now % 1440))} after {final_ward_los:.1f} minutes ({(final_ward_los / 24 / 60):.1f} days). Occupancy after discharge: {len(self.ward_occupancy)} of {g.number_of_ward_beds} ward beds",
                    identifier=patient.id,
                    config=g.trace_config,
                )

                patient.exit_time = self.env.now
                patient.journey_completed = True

        # Record patients who exited at any remaining points
        patient.exit_time = self.env.now
        patient.journey_completed = True

    # MARK: M: Run result calculation
    # This method calculates results over a single run.
    def calculate_run_results(self):
        """
        Calculate summary statistics and financial metrics for a single
        simulation run.

        This method aggregates raw data collected throughout the simulation,
        performs unit conversions, and computes Key Performance Indicators
        (KPIs) related to clinical flow and financial impact. It cleans the
        results dataframe and updates class-level attributes for use in
        trial-level reporting.

        - **Data Cleaning**: Removes the initial dummy row (index label 1) used
          to initialize the `results_df`.
        - **Unit Conversions**: Automatically converts ward-related timings
          (Queue Time and Length of Stay) from minutes to hours for reporting.
        - **SDEC Logic**: Financial staff costs for SDEC are adjusted based on
          the `sdec_freeze_counter` to ensure costs are only incurred during
          active operational periods.
        - **Precision**:
            - Financial and time-based KPIs are rounded to 0 decimal places.
            - Clinical outcomes (MRS Change) are rounded to 2 decimal places.

        Calculated Attributes
        ---------------------
        mean_q_time_nurse : float
            Average wait time for a nurse in minutes.
        number_of_admissions_avoided : int
            Total count of patients diverted from inpatient wards via SDEC.
        mean_q_time_ward : float
            Average wait time for a ward bed in hours.
        mean_ward_occupancy : float
            The average number of beds occupied during the run.
        admission_delays : int
            Total number of patients who experienced any wait time for a ward
            bed.
        mean_los_ward : float
            Average inpatient length of stay in hours.
        sdec_financial_savings : float
            Gross savings based on avoided bed days.
        medical_staff_cost : float
            The net operational cost of SDEC staffing.
        savings_sdec : float
            Net financial impact (Savings - Costs) of the SDEC unit.
        total_savings : float
            Combined net impact of SDEC and thrombolysis-related savings.
        mean_mrs_change : float
            Average change in Modified Rankin Scale for the patient cohort.

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.
        """
        # Drop the first row of the results DataFrame, as this is just a dummy
        # and will take on the value of zero.
        self.results_df.drop([1], inplace=True)

        # The below code calculates the average or cumulative values the model
        # is concerned with.

        self.mean_q_time_nurse = round(self.results_df["Q Time Nurse"].mean(), 0)

        self.max_q_time_nurse = round(self.results_df["Q Time Nurse"].max(), 0)

        self.number_of_admissions_avoided = len(self.admission_avoidance)

        self.mean_q_time_ward = round(self.results_df["Q Time Ward"].mean() / 60, 0)

        self.max_q_time_ward = round(self.results_df["Q Time Ward"].max() / 60, 0)

        try:
            self.mean_ward_occupancy = round(self.results_df["Ward Occupancy"].mean())
        except ValueError:
            self.mean_ward_occupancy = np.NaN

        self.admission_delays = len(self.results_df[self.results_df["Q Time Ward"] > 0])

        self.mean_los_ward = round(self.results_df["Ward LOS"].mean() / 60, 0)

        # Note that this is using the admission avoidance MODEL attribute,
        # which is populated entirely separately from the patient-level
        # admission avoidance attributes and will ensure that only SDEC
        # patients who are explicitly benefitting from admission avoidance
        # via SDEC will be counted here
        # self.sdec_financial_savings = (
        #     len(self.admission_avoidance) * g.inpatient_bed_cost
        # )
        self.sdec_financial_savings = round(self.results_df["SDEC Savings"].sum(), 0)

        # The below code ensures that the SDEC incurs no cost if it is not
        # running at all in the model. This was introduced as a bug was causing
        # it to return small values even if the SDEC was not running. This is
        # now fixed, but the code works so I have left it in place.

        if g.sdec_unav_freq == 0:
            self.medical_staff_cost = 0
        else:
            self.medical_staff_cost = round(
                g.sdec_dr_cost_min * (g.sim_duration)
                - g.sdec_dr_cost_min * self.sdec_freeze_counter * g.sdec_unav_time,
                0,
            )

        self.savings_sdec = round(
            self.sdec_financial_savings - self.medical_staff_cost, 0
        )

        self.thrombolysis_savings = round(
            self.results_df["Thrombolysis Savings"].sum(), 0
        )
        self.total_savings = self.thrombolysis_savings + self.savings_sdec

        self.mean_mrs_change = round(self.results_df["MRS Change"].mean(), 2)

    # MARK: M: per-run plotting
    # This method plots the stroke nurse assessment queue graph, as it is after
    # the run method it will appear after the run has completed in the output.
    # Might need to change this...

    def plot_stroke_run_graphs(self, plot=True):
        """
        Generate and display time-series visualizations for the simulation run.

        This method creates a line plot of the Stroke Ward occupancy over the
        duration of the simulation. It includes both the raw occupancy data
        and a linear trend line to help identify long-term capacity issues.
        Execution is dependent on the global `g.gen_graph` toggle.

        - **Data Cleaning**: Automatically drops the first row (index 0) of
          `occupancy_graph_df`, which is typically used as a placeholder.
        - **Trend Analysis**: Uses a first-order polynomial fit
          (`numpy.polyfit`) to calculate and display a linear trend line over
          the occupancy data.
        - **Extensibility**: Contains placeholder (commented-out) logic for
          an additional "Nurse Assessment Queue" graph.
        - **Dependencies**: Requires `matplotlib.pyplot` as `plt` and
          `numpy` as `np`.

        Parameters
        ----------
        plot : bool, default True
            If True, the generated figure is displayed immediately using
            `plt.show()`. If False, the figure object is returned to the
            caller for further processing (e.g., aggregation in a Trial report).

        Returns
        -------
        matplotlib.figure.Figure or None
            Returns a Matplotlib Figure object if `plot` is False.
            Returns None if `plot` is True or if `g.gen_graph` is False.


        See Also
        --------
        Trial.run_trial : The method that may collect these figures for batch
        reporting.

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.
        """
        if g.gen_graph == True:
            # Queue for Nurse Assessment Graph (Currently Commented Out)

            # self.nurse_q_graph_df.drop([0], inplace=True)

            # fig, ax = plt.subplots()

            # ax.set_xlabel("Time")
            # ax.set_ylabel("Number of patients in Q for Assessment")
            # ax.set_title(f"Number of Patients in Nurse Assessment Queue \
            # Over Time "f"{self.run_number}")

            # ax.plot(self.nurse_q_graph_df["Time"],
            # self.nurse_q_graph_df["Patients in Assessment Queue"],
            # color="m",
            # linestyle="-",
            # label="Q for Stroke Nurse Assessment")

            # ax.legend(loc="upper right")

            # fig.show()

            # Ward Occupancy Graph

            self.ward_occupancy_graph_df.drop([0], inplace=True)

            occupancy_after_warm_up = self.ward_occupancy_graph_df[
                self.ward_occupancy_graph_df["After Warm-Up"] == True
            ]

            fig, ax = plt.subplots()

            ax.set_xlabel("Time")
            ax.set_ylabel("Stroke Ward Occupancy")
            ax.set_title(
                f"Trial "
                f"{g.trials_run_counter}\
                         Ward Occupancy Over Time "
                f"{self.run_number}"
            )

            ax.plot(
                occupancy_after_warm_up["Time"],
                occupancy_after_warm_up["Ward Occupancy"],
                color="b",
                linestyle="-",
                label="Ward Occupancy",
            )

            # Add trend line
            x = occupancy_after_warm_up["Time"]
            y = occupancy_after_warm_up["Ward Occupancy"]
            z = np.polyfit(x, y, 1)  # 1 = linear fit
            p = np.poly1d(z)
            ax.plot(x, p(x), color="b", linestyle="--", label="Trend Line")

            ax.legend(loc="upper right")

            if plot:
                fig.show()
            else:
                return fig

    def track_days(self):
        """
        A SimPy process that logs the progression of simulation days.

        This generator functions as a background 'clock' process. It wakes up
        at the start of every 1440-minute interval (24 hours) to output a
        formatted debug message indicating the current day of the simulation
        run. This helps track progress in the console during long-running
        simulations.

        - The day calculation is performed using floor division:
          `self.env.now // 1440`.
        - The trace message visibility depends on the `g.show_trace` flag and
          the `g.tracked_cases` configuration.
        - This process runs concurrently with patient arrivals and clinical
          obstructions without interfering with their logic.

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.
        """
        # Print a debugging message every day
        while self.env.now <= g.sim_duration:
            # TODO: this doesn't always reliably appear depending on number of tracked cases
            trace(
                msg=f"========= DAY {(self.env.now // 1440):.0f} ===============",
                time=self.env.now,
                debug=g.show_trace,
                identifier=max(g.tracked_cases),
                config=g.trace_config,
            )
            yield self.env.timeout(1440)

    # MARK: M: run model
    # The run method starts up the DES entity generators, runs the simulation,
    # and in turns calls anything we need to generate results for the run
    def run(self):
        """
        Execute the simulation run lifecycle.

        This method initializes the simulation by registering background
        processes, executes the SimPy event loop for a specified duration,
        and performs post-simulation data processing and export tasks.

        The execution sequence is as follows:
        1. Register time-tracking, patient arrival, and resource obstruction
           generators as SimPy processes.
        2. Execute the simulation engine until the combined limit of the
           warm-up period and active simulation duration is reached.
        3. Trigger final calculation of run-level results.
        4. (Optional) Export patient-level results to a CSV file.

        - **Warm-up Period**: The total runtime includes `g.warm_up_period`. This
          is crucial for allowing the model to reach a 'steady state' before
          results are recorded as valid.
        - **Concurrency**: All methods passed to `self.env.process()` run
          pseudo-parallelly, managed by the SimPy event scheduler.
        - **Post-Processing**: This method must be called for `results_df`
          and other KPIs to be populated with final values.

        See Also
        --------
        track_days : The background process that logs day transitions.

        generator_patient_arrivals: generates in-hours patients and sends them
            through the assessment pathway.

        obstruct_ctp: ensures the ctp scanner is only available for the
            specified times.

        obstruct_sdec: ensures the sdec is only available for the specified
            times.

        calculate_run_results : The method called to process data after the
            event loop finishes.

        Notes
        -----
        GENAI declaration (SR): this docstring has been generated with the aid
        of Google Gemini Flash.
        All generated content has been thoroughly reviewed.
        """
        # starts up the generators in the model, of which there are three.

        self.env.process(self.track_days())
        self.env.process(self.generator_patient_arrivals())
        self.env.process(self.obstruct_ctp())
        self.env.process(self.obstruct_sdec())

        # Run the model for the duration specified in g class
        self.env.run(until=(g.sim_duration + g.warm_up_period))

        # Check that all patient objects generated are valid
        # This can highlight errors with patients who don't get all of their attributes set,
        # which can indicate issues with logic branches
        # Only check for patients with a completed journey as those with incomplete journeys
        # may simply have not reached the point in the model where the relevant attribute was set
        [p.validate() for p in self.patient_objects if p.journey_completed]

        # Now the simulation run has finished, call the method that calculates
        # run results
        self.calculate_run_results()

        # Print the run number with the patient-level results from this run of
        # the model, this is commented out at the moment.

        # print (f"Run Number {self.run_number}")
        # print (self.results_df)

        if g.write_to_csv == True:
            self.results_df.to_csv(
                f"trial {g.trials_run_counter} output {self.run_number}.csv",
                index=False,
            )

        # TODO: SR: I have commented this out for now
        # self.plot_stroke_run_graphs()

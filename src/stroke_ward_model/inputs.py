"""
Defines global configuration parameters for the stroke ward simulation model.
"""


# MARK: g
# Global class to store parameters for the model.
class g:
    """
    Global simulation configuration parameters.

    This class stores all model-wide constants used in the discrete-event
    simulation, including runtime settings, resource capacities, operational
    constraints, diagnosis-based length-of-stay (LOS) values, cost parameters,
    and state flags modified during execution. All attributes are class
    variables and are intended to be accessed without instantiation.

    Attributes
    ----------
    sim_duration : int
        Total simulated time in minutes (default: 525600, one year).
    number_of_runs : int
        Number of simulation replications.
    warm_up_period : float
        Number of minutes considered warm-up (not included in statistics),
        defined as one-fifth of the total simulation time.
    patient_inter_day : int
        Interarrival time (minutes) for daytime patient generation.
        NOTE that this is not used in entirely the way that you might expect.
        This may be changed in future.
        NOTE that this has now been changed to be used directly as an average
        IAT, but this may change in future. This supersedes the previous note.
    patient_inter_night : int
        Interarrival time (minutes) for nighttime patient generation.
        NOTE that this is not used in entirely the way that you might expect.
        This may be changed in future.
        NOTE that this has now been changed to be used directly as an average
        IAT, but this may change in future. This supersedes the previous note.
    number_of_nurses : int
        Number of nurses available in the system.
    mean_n_consult_time : int
        Mean consultation time in minutes.
    mean_n_ct_time : int
        Mean CT processing time in minutes.
    number_of_ctp : int
        Number of CT processing units available.
    sdec_beds : int
        Number of SDEC (Same Day Emergency Care) beds.
    mean_n_sdec_time : int
        Mean SDEC stay duration in minutes.
    number_of_ward_beds : int
        Number of inpatient ward beds.
    mean_n_i_ward_time_mrs_0 : int
        Inpatient LOS (minutes) for ischemic stroke by modified Rankin Scale (0).
    mean_n_i_ward_time_mrs_1 : int
        Inpatient LOS (minutes) for ischemic stroke by modified Rankin Scale (1).
    mean_n_i_ward_time_mrs_2 : int
        Inpatient LOS (minutes) for ischemic stroke by modified Rankin Scale (2).
    mean_n_i_ward_time_mrs_3 : int
        Inpatient LOS (minutes) for ischemic stroke by modified Rankin Scale (3).
    mean_n_i_ward_time_mrs_4 : int
        Inpatient LOS (minutes) for ischemic stroke by modified Rankin Scale (4).
    mean_n_i_ward_time_mrs_5 : int
        Inpatient LOS (minutes) for ischemic stroke by modified Rankin Scale (5).
    mean_n_ich_ward_time_mrs_0 : int
        Inpatient LOS (minutes) for intracerebral hemorrhage by MRS score (0).
    mean_n_ich_ward_time_mrs_1 : int
        Inpatient LOS (minutes) for intracerebral hemorrhage by MRS score (1).
    mean_n_ich_ward_time_mrs_2 : int
        Inpatient LOS (minutes) for intracerebral hemorrhage by MRS score (2).
    mean_n_ich_ward_time_mrs_3 : int
        Inpatient LOS (minutes) for intracerebral hemorrhage by MRS score (3).
    mean_n_ich_ward_time_mrs_4 : int
        Inpatient LOS (minutes) for intracerebral hemorrhage by MRS score (4).
    mean_n_ich_ward_time_mrs_5 : int
        Inpatient LOS (minutes) for intracerebral hemorrhage by MRS score (5).
    mean_n_non_stroke_ward_time : int
        LOS (minutes) for non-stroke patients (TODO: CHECK INTERPRETATION).
    mean_n_tia_ward_time : int
        LOS (minutes) for TIA patients.
    thrombolysis_los_save : float
        Proportional reduction in LOS for thrombolysed patients.
        This is used as a multiplier with the sampled length of stay.
        For example, if a patient has a LOS of 10 days, and the value of
        `thrombolysis_los_save` was 0.75, the calculation would be 10 * 0.75,
        resulting in a LOS of 7.5 days.
    mean_mrs : int
        Default/mean modified Rankin Scale score used in the model.
    ich : int
        Percentage likelihood of intracerebral hemorrhage diagnosis
        (TODO: CHECK INTERPRETATION).
    i : int
        Percentage likelihood of ischemic stroke diagnosis.
    tia : int
        Percentage likelihood of TIA diagnosis.
    stroke_mimic : int
        Percentage likelihood of stroke mimic diagnosis.
    tia_admission : int
        Percentage chance that a TIA requires admission.
    stroke_mimic_admission : int
        Percentage chance that a stroke mimic requires admission.
    sdec_dr_cost_min : float
        Cost per minute for SDEC doctor time.
    sdec_bed_day_saving: float
        The number of bed days an SDEC admission is assumed to save. This is used in calculating
        the potential savings from SDEC usage.
    inpatient_bed_cost : float
        Cost of a standard inpatient bed stay, per day.
    inpatient_bed_cost_thrombolysis : float
        Cost of an inpatient stay following thrombolysis, per day.
    sdec_unav_time : int
        Operational unavailability duration of SDEC
    sdec_unav_freq : int
        How often SDEC unavailability duration occurs
    ctp_unav_time : int
        Operational unavailability duration of CT perfusion scanner
    ctp_unav_freq : int
        How often CT perfusion unavailability duration occurs
    sdec_unav : bool
        Indicates whether SDEC is unavailable.
    ctp_unav : bool
        Indicates whether CT processing is unavailable.
    write_to_csv : bool
        Whether the simulation should write results to CSV.
    gen_graph : bool
        Whether visualisation graphs should be generated.
    therapy_sdec : bool
        Whether therapy is delivered through SDEC.
    trials_run_counter : int
        Internal counter tracking completed simulation replications.
    patient_arrival_gen_1 : bool
        Flag used by the simulation to control one patient arrival stream.
    patient_arrival_gen_2 : bool
        Flag used by the simulation to control a second patient arrival stream.
    master_seed : int
        Master random seed used to adjust the underlying seeds used to populate
        the random number streams. Trials run without changing parameters or the
        master seed will be consistent.

    Notes
    -----
    GENAI declaration (SR): this docstring has been generated with the aid of
    ChatGPT 5.1.
    All generated content has been thoroughly reviewed.
    """

    # 525600 (Year of Minutes)
    sim_duration = 525600
    number_of_runs = 10
    # TODO - consider setting the default as a fixed number of minutes
    warm_up_period = sim_duration / 5

    patient_inter_day = 167.5  # 189.0
    patient_inter_night = 358.00  # 247.00

    number_of_nurses = 2
    number_of_ctp = 1
    sdec_beds = 5
    number_of_ward_beds = 1

    mean_n_consult_time = 60
    mean_n_ct_time = 20
    mean_n_sdec_time = 240

    # Different variables for ward stay based on diagnosis, thrombolysis and MRS
    mean_n_i_ward_time_mrs_0 = 1440 * 2.88
    mean_n_i_ward_time_mrs_1 = 1440 * 4.54
    mean_n_i_ward_time_mrs_2 = 1440 * 7.4
    mean_n_i_ward_time_mrs_3 = 1440 * 14.14
    mean_n_i_ward_time_mrs_4 = 1440 * 26.06
    mean_n_i_ward_time_mrs_5 = 1440 * 29.7

    mean_n_ich_ward_time_mrs_0 = 1440 * 2.62
    mean_n_ich_ward_time_mrs_1 = 1440 * 7.03
    mean_n_ich_ward_time_mrs_2 = 1440 * 12.15
    mean_n_ich_ward_time_mrs_3 = 1440 * 18.91
    mean_n_ich_ward_time_mrs_4 = 1440 * 32.45
    mean_n_ich_ward_time_mrs_5 = 1440 * 41.83

    # Set parameters for mild (TIA) and non-stroke stays
    mean_n_non_stroke_ward_time = 1440 * 3  # 4320
    mean_n_tia_ward_time = 1440 * 1

    # For each patient who is considered for thrombolysis (because onset window known, or because
    # onset window unknown but CTP scan is available and shows saveable brain), what is the chance
    # that they will not be treated with thrombolysis due to absolute or relative
    # contraindications (e.g. mild stroke symptoms and/or symptoms that are already improving,
    # previous stroke within a certain  time period, severe uncontrolled hypertension, dementia,
    # pregnancy, recently taken certain oral anticoagulants,
    # previous use of thrombolysis for other conditions within a given time period,
    # arriving later in thrombolysable window)
    # See https://pmc.ncbi.nlm.nih.gov/articles/PMC9323435/ which found that 47% of patients
    # who had a known onset <4.5 hours ago were not treated with thrombolysis, with 26% having
    # absolute contraindication and 74% having relative contraindication
    # and https://pmc.ncbi.nlm.nih.gov/articles/PMC9890612/
    # and https://www.ncbi.nlm.nih.gov/books/NBK557411/
    # This estimate may be updated if exact data is available, but is currently felt to be
    # a reasonable estimate for a high-thrombolysing hospital (who may be more likely to thrombolyse
    # in face of relative contraindications or may have patient mix with fewer absolute contraindications)
    probability_of_thrombolysis_contraindication = 0.4
    thrombolysis_los_save = 0.75

    sdec_dr_cost_min = 0.50
    # how many inpatient days an SDEC admission is assumed to save.
    sdec_bed_day_saving = 1.0

    # daily cost for bed days
    # taken from https://www.england.nhs.uk/london/wp-content/uploads/sites/8/2019/09/acute-commissioning-and-tariff-guidance.pdf
    # adjusted for inflation using bank of england calculator
    # This value will be used for SDEC savings
    inpatient_bed_cost = (
        819.53  # £633 HASU component in 2019 --> £818.53 in January 2026
    )
    # This value will be used for thrombolysis savings
    inpatient_bed_cost_thrombolysis = (
        491.38  # £380 less-acute bed day rate for 2019 --> £491.38 in January 2026
    )

    # Average modified rankin scale score for patients arriving
    mean_mrs = 2

    # Diagnosis % range
    ich = 10
    i = 60
    tia = 70
    stroke_mimic = 80

    # Admission Range (% Chance of Admission) for TIA and Stroke Mimic, non
    # stroke shares the range with stroke mimic in this model. (This is
    # reflected in our real data mainly because most non strokes are often
    # mimics that are not classified under the stroke mimic criteria in our
    # data collection)
    tia_admission = 10
    stroke_mimic_admission = 30

    # Operational hours of SDEC and CTP are set by the user and stored in the
    # variables below.

    sdec_unav_time = 0
    sdec_unav_freq = 0
    ctp_unav_time = 0
    ctp_unav_freq = 0

    sdec_value = 0
    ctp_value = 0

    sdec_opening_hour = 0
    ctp_opening_hour = 0

    in_hours_start = 7
    ooh_start = 0

    # Setting of relative frequencies of onsets
    # Approximation based on https://strokeaudit.org/SupportFiles/Documents/Posters-and-oral-presentations/2020/ESOC-2020-Onset-to-arrival-times_Poster.aspx#:~:text=Of%20433%2C209%20patients%20admitted%20to,75%5D%20(figure%202).
    in_hours_known_onset = 0.7
    in_hours_unknown_onset_inside_ctp = 0.15
    in_hours_unknown_onset_outside_ctp = 0.15
    # This is presumed to be lower due to wake-up strokes being the primary strokes occurring overnight
    # Awaiting better data at which point this should be reparameterised.
    out_of_hours_known_onset = 0.2
    out_of_hours_unknown_onset_inside_ctp = 0.4
    out_of_hours_unknown_onset_outside_ctp = 0.4

    # These values are changed by the model itself

    sdec_unav = False
    ctp_unav = False
    write_to_csv = False
    gen_graph = False
    therapy_sdec = False
    trials_run_counter = 1
    patient_arrival_gen_1 = False
    patient_arrival_gen_2 = False

    show_trace = False
    tracked_cases = list(range(1, 1500))
    trace_config = {"tracked": tracked_cases}

    master_seed = 42

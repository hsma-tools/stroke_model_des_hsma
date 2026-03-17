"""
Defines patient entities and their attributes for the stroke ward simulation.
"""

import numpy as np


# MARK: Patient
# Patient class to store patient attributes
class Patient:
    """
    Representation of an individual patient within the simulation.

    A `Patient` object stores all clinical, pathway, and state-related
    attributes required for modelling flow through the stroke care
    process.

    Several characteristics (onset type, MRS score, diagnosis
    category, admission likelihood) are randomly generated on creation
    (or at the start of assessment) using parameters defined in the global
    configuration class `g`.

    Parameters
    ----------
    p_id : int or str
        Unique identifier for the patient.

    Attributes
    ----------
    id : int or str
        Patient identifier.
    q_time_nurse : float
        Time spent waiting for nursing assessment or consultation.
    q_time_ward : float
        Time spent waiting for an inpatient ward bed.
    onset_type : int or float
        Categorisation of onset information (initialized as NaN):
        - 0 : Known onset
        - 1 : Unknown onset but within CTP window
        - 2 : Unknown onset and outside CTP window
    mrs_type : int or float
        Modified Rankin Scale score at presentation (0–5).
        Drawn from an exponential distribution and capped at 5.
    mrs_discharge : int or float
        Modified Rankin Scale score at discharge.
    diagnosis : int or float
        Raw randomised diagnostic value (0–100). Used to map to a clinical
        category based on thresholds defined in `g`.
    patient_diagnosis : int or float
        Encoded diagnosis category:
        - 0 : Intracerebral haemorrhage (ICH)
        - 1 : Ischaemic stroke (I)
        - 2 : Transient ischaemic attack (TIA)
        - 3 : Stroke mimic
        - 4 : Non-stroke
    patient_diagnosis_type : str or None
        String representation or specific subtype of the diagnosis.
    priority : int
        Triage priority level (used for queue ordering). Default is 1.
    non_admission : int or float
        Randomised admission likelihood score (0–100).
    advanced_ct_pathway : bool or None
        Whether the patient enters an advanced CT imaging pathway.
    sdec_pathway : bool or None
        Whether the patient is routed through SDEC.
    thrombolysis : bool or None
        Whether the patient receives thrombolysis.
    thrombolysis_contraindicated : bool or None
        Whether a patient who has a known onset within a thrombolysable period, or has a CTP scan
        that shows saveable brain tissue, is not treated with thrombolysis due to other
        contraindications.
    thrombectomy : bool or None
        Whether the patient receives thrombectomy.
    admission_avoidance : bool or None
        Whether the patient avoids an admission by being seen in SDEC instead.
    admission_avoidance_because_of_therapy : bool or None
        Whether the patient avoids an admission by being seen in SDEC instead and would
        not have avoided admission if therapy had not been available (True). Set to false
        if an avoided admission that still would have been avoided even if the therapy provision
        was not running.
    non_admitted_tia_ns_sm : bool or None
        Flag indicating if a TIA, Non-Stroke, or Stroke Mimic patient was
        not admitted.
    ward_los : float
        Total length of stay in the ward.
    ward_los_thrombolysis : float
        Specific length of stay component related to thrombolysis treatment.
    sdec_los : float
        Total length of stay in the Same Day Emergency Care (SDEC) unit.
    ctp_duration : float
        Time taken for CT Perfusion scan.
    ct_duration : float
        Time taken for standard CT scan.
    arrived_ooh : bool or None
        Flag indicating if the patient arrived Out of Hours.
    clock_start : float
        Simulation time of patient arrival.
    nurse_q_start_time : float
        Time patient joined the nurse queue.
    nurse_triage_start_time : float
        Time nurse triage began.
    nurse_triage_end_time : float
        Time nurse triage finished.
    ct_scan_start_time : float
        Time CT scan began.
    ctp_scan_start_time : float
        Time CTP scan began.
    ct_scan_end_time : float
        Time CT scan finished.
    ctp_scan_end_time : float
        Time CTP scan finished.
    sdec_admit_time : float
        Time admitted to SDEC.
    sdec_discharge_time : float
        Time discharged from SDEC.
    ward_q_start_time : float
        Time patient joined the ward bed queue.
    ward_admit_time : float
        Time admitted to the ward.
    ward_discharge_time : float
        Time discharged from the ward.
    exit_time : float
        Time the patient left the simulation entirely.
    nurse_attending_id : int or float
        ID of the specific nurse resource assigned.
    ct_scanner_id : int or float
        ID of the specific CT scanner resource assigned.
    sdec_bed_id : int or float
        ID of the specific SDEC bed/cubicle assigned.
    ward_bed_id : int or float
        ID of the specific ward bed assigned.
    sdec_running_when_required : bool or None
        State of SDEC availability when the patient needed it.
    sdec_full_when_required : bool or None
        State of SDEC capacity when the patient needed it.
    generated_during_warm_up : bool or None
        Flag indicating if the patient was generated during the model warm-up
        period.
    journey_completed : bool or None
        Flag indicating if the patient completed the full pathway or was
        removed/processed differently.

    Notes
    -----
    GENAI declaration (SR): this docstring has been generated with the aid
    of ChatGPT 5.1 and subsequently updated by Gemini to reflect code changes.
    All generated content has been thoroughly reviewed.
    """

    _required_fields = [
        "arrived_ooh",
        "advanced_ct_pathway",
        "sdec_pathway",
        "thrombolysis",
        "thrombectomy",
        "admission_avoidance",
        "non_admitted_tia_ns_sm",
        "sdec_running_when_required",
        "sdec_full_when_required",
        "generated_during_warm_up",
        # Numeric fields
        "clock_start",
        "exit_time",
    ]

    def __init__(self, p_id):
        self.id = p_id

        self.q_time_nurse = np.NaN  # SR NOTE - changed this to NaN by default
        self.q_time_ward = np.NaN  # SR NOTE - changed this to NaN by default

        # 0 = known onset, 1 = unknown onset (in ctp range),
        # 2 = unknown (out of ctp range)
        # SR NOTE: I've moved all random generation to the start of their
        # assessment to allow for reproducibility
        # self.onset_type = random.randint(0, 2)
        self.onset_type = np.NaN

        # Max MRS is set to 5
        # self.mrs_type = min(round(random.expovariate(1.0 / g.mean_mrs)), 5)
        self.mrs_type = np.NaN
        self.mrs_discharge = np.NaN  # SR NOTE - changed this to NaN by default

        # <=5 is ICH, <=55 is I, <= 70 is TIA, <=85 is Stroke Mimic, >85 is
        # non\stroke, this set in g class
        # TODO: SR: This comment does not appear to be in sync with actual
        # values seen in the g class
        # TODO: SR: Which is correct?
        # self.diagnosis = random.randint(0, 100)
        self.diagnosis = np.NaN
        # 0 = ICH, 1 = I, 2 = TIA, 3 = Stroke Mimic, 4 = non stroke
        self.patient_diagnosis = np.NaN  # SR NOTE - changed this to NaN by default
        self.patient_diagnosis_type = "None"

        self.priority = 1
        # self.non_admission = random.randint(0, 100)
        self.non_admission = np.NaN

        self.advanced_ct_pathway = None
        self.thrombolysis_enabled_by_ctp = None
        self.sdec_pathway = None

        self.thrombolysis = None
        self.thrombolysis_contraindicated = None
        self.thrombectomy = None

        self.admission_avoidance = None
        self.admission_avoided_because_of_therapy = None
        self.non_admitted_tia_ns_sm = None

        # NOTE: Additional items added by SR
        self.ward_los = np.NaN
        self.ward_los_thrombolysis = np.NaN
        self.sdec_los = np.NaN
        self.ctp_duration = np.NaN
        self.ct_duration = np.NaN

        self.arrived_ooh = None

        # Recording times of various events for animations and process logs
        self.clock_start = np.NaN  # This can be considered to be their arrival time

        self.nurse_q_start_time = np.NaN
        self.nurse_triage_start_time = np.NaN
        self.nurse_triage_end_time = np.NaN

        self.ct_scan_start_time = np.NaN
        self.ct_scan_end_time = np.NaN

        self.ctp_scan_start_time = np.NaN
        self.ctp_scan_end_time = np.NaN

        self.sdec_running_when_required = None
        self.sdec_full_when_required = None

        self.sdec_admit_time = np.NaN
        self.sdec_discharge_time = np.NaN

        self.ward_q_start_time = np.NaN
        self.ward_admit_time = np.NaN
        self.ward_discharge_time = np.NaN
        self.exit_time = np.NaN

        self.nurse_attending_id = np.NaN
        self.ct_scanner_id = np.NaN
        self.sdec_bed_id = np.NaN
        self.ward_bed_id = np.NaN

        self.generated_during_warm_up = None

        # Flag for optionally removing incomplete journeys or processing them
        # in a different way in results
        # Note that unlike other booleans defined in the patient object,
        # we have defaulted this to False intentionally
        self.journey_completed = False

    def _is_unset(self, value):
        if value is None:
            return True
        try:
            return np.isnan(value)
        except TypeError:
            return False

    def validate(self):
        missing = [
            field
            for field in self._required_fields
            if self._is_unset(getattr(self, field))
        ]

        if missing:
            raise ValueError(
                f"Patient validation failed.\n"
                f"Missing fields: {missing}\n\n"
                f"Full object state:\n{self}"
            )

    def __repr__(self):
        attrs = vars(self)
        return "\n".join(f"{k}: {v}" for k, v in attrs.items())

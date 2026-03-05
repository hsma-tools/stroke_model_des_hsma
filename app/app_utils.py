"""
App utilities
"""

from streamlit_extras.stylable_container import stylable_container
import streamlit as st
from stroke_ward_model.metrics import Metrics, MetricsSnapshot
import json

split_vars = {
    "Onset Type": "onset_type",
    "MRS Type": "mrs_type",
    "MRS on Discharge": "mrs_discharge",
    "Patient Diagnosis": "patient_diagnosis",
    "Priority": "priority",
    "Advanced CT Pathway": "advanced_ct_pathway",
    "SDEC Pathway": "sdec_pathway",
    "SDEC Running when Required": "sdec_running_when_required",
    "SDEC Full when Required": "sdec_full_when_required",
    "Thrombolysis": "thrombolysis",
    "Thrombectomy": "thrombectomy",
    "Admission Avoidance": "admission_avoidance",
    "Patient with TIA, stroke mimic or non-stroke not admitted": "non_admitted_tia_ns_sm",
    "Arrived OOH": "arrived_ooh",
    "Patient Diagnosis Type": "patient_diagnosis_type",
}

time_vars = {
    "Clock Start": "clock_start",
    "Nurse Queue Start": "nurse_q_start_time",
    "Nurse Triage Start": "nurse_triage_start_time",
    "Nurse Triage End": "nurse_triage_end_time",
    "CT Scan Start": "ct_scan_start_time",
    "CT Scan End": "ct_scan_end_time",
    "CTP Scan Start": "ctp_scan_start_time",
    "CTP Scan End": "ctp_scan_end_time",
    "SDEC Admit Time": "sdec_admit_time",
    "SDEC Discharge Time": "sdec_discharge_time",
    "Ward Queue Start": "ward_q_start_time",
    "Ward Admit Time": "ward_admit_time",
    "Ward Discharge Time": "ward_discharge_time",
    "Model Exit Time": "exit_time",
}


def iconMetricContainer(
    key, icon_unicode, css_style=None, icon_color="grey", family="filled", type="icons"
):
    """
    Create a CSS styled container that adds a Material icon to a Streamlit
    `st.metric` component.

    Adapted from:
    https://discuss.streamlit.io/t/adding-an-icon-to-a-st-metric-easily/59140

    Parameters
    ----------
    key : str
        Unique key for the component.
    iconUnicode : str
        Unicode code point for the Material Icon, (e.g., "e8b6" used as
        "\\e8b6"). You can find them here: https://fonts.google.com/icons.
    css_style : str, optional
        Additional CSS to apply.
    icon_color : str, optional
        CSS color for the icon. Defaults to "grey".
    family : str, optional
        Icon family to use when type = "icons". Should be either "filled" or
        "outline".
    type : str, optional
        Icon font type: either "icons" (Material Icons) or "symbols" (Material
        Symbols Outlined).

    Returns
    -------
    DeltaGenerator
        A stylable container. Elements can be add to the container using "with"
        or by calling methods directly on the returned object.
    """
    # Choose the correct font-family for the icon
    if (family == "filled") and (type == "icons"):
        font_family = "Material Icons"
    elif (family == "outline") and (type == "icons"):
        font_family = "Material Icons Outlined"
    elif type == "symbols":
        font_family = "Material Symbols Outlined"
    else:
        print("ERROR - Check Params for iconMetricContainer")
        font_family = "Material Icons"

    # Base CSS that injects the icon before the st.metric value
    css_style_icon = f"""
                    div[data-testid="stMetricValue"]>div::before
                    {{
                        font-family: {font_family};
                        content: "\\{icon_unicode}";
                        vertical-align: -20%;
                        color: {icon_color};
                    }}
                    """

    # Optionally append user-provided extra CSS
    if css_style is not None:
        css_style_icon += f"\n{css_style}"

    # Create the stylable container with the assembled CSS
    iconMetric = stylable_container(key=key, css_styles=css_style_icon)
    return iconMetric


def read_file_contents(file_name):
    """
    Read the entire contents of a text file.

    Parameters
    ----------
    file_name : str
        Path to file.

    Returns:
    -------
    str
        File contents as a single string.
    """
    with open(file_name, encoding="utf-8") as f:
        return f.read()


def save_run(metrics: Metrics, label: str = None):
    """Call this after each simulation run to persist the Metrics object."""
    label = label or f"Run {len(st.session_state.metrics_runs) + 1}"
    st.session_state.metrics_runs.append({"label": label, "metrics": metrics})
    # Auto-set first run as baseline
    if len(st.session_state.metrics_runs) == 1:
        st.session_state.baseline_index = 0


def save_state_to_json() -> str:
    snapshots = []
    for r in st.session_state.metrics_runs:
        metrics = r["metrics"]
        if isinstance(metrics, Metrics):
            snapshot = MetricsSnapshot.from_metrics(metrics, r["label"])
        elif isinstance(metrics, MetricsSnapshot):
            snapshot = metrics
        else:
            raise TypeError(
                f"Unexpected metrics type in session state: {type(metrics)}"
            )
        snapshots.append(snapshot.to_dict())

    data = {
        "baseline_index": st.session_state.baseline_index,
        "runs": snapshots,
    }
    return json.dumps(data, indent=2)


def load_state_from_json(json_str: str):
    """Deserialise and reinitialise session state from a JSON string."""
    data = json.loads(json_str)
    st.session_state.metrics_runs = [
        {"label": r["label"], "metrics": MetricsSnapshot.from_dict(r)}
        for r in data["runs"]
    ]
    st.session_state.baseline_index = data["baseline_index"]


@st.fragment
def download_state_button():
    if st.session_state.metrics_runs:
        # Pre-compute once into session state so it's ready for download
        # but only regenerated when runs actually change
        if st.button("📦 Prepare save file"):
            st.session_state.saved_json = save_state_to_json()

        if "saved_json" in st.session_state:
            st.download_button(
                label="💾 Download JSON",
                data=st.session_state.saved_json,
                file_name="simulation_runs.json",
                mime="application/json",
            )
    else:
        st.button(
            "📦 Prepare save file",
            disabled=True,
            help="Run at least one simulation before saving",
        )


def render_state_io():
    st.subheader("Load a previous session")

    uploaded = st.file_uploader(
        "📂 Load runs from JSON",
        type="json",
        key="json_uploader",
        label_visibility="collapsed",
    )

    if uploaded is not None:
        # Use the file's id to track if we've already processed this specific upload
        file_id = uploaded.file_id
        if st.session_state.get("last_loaded_file_id") != file_id:
            load_state_from_json(uploaded.read().decode("utf-8"))
            st.session_state.last_loaded_file_id = file_id
            st.toast(
                f"✅ Loaded {len(st.session_state.metrics_runs)} run(s) successfully."
            )

        labels = [f"- {r['label']}" for r in st.session_state.get("metrics_runs", [])]
        st.write("The following runs are currently stored in memory:")
        st.write("\n".join(labels))

    st.subheader("Save your current session to a file")
    download_state_button()

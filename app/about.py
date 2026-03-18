"""
About page
"""

import streamlit_mermaid as stmd
import streamlit as st

from app_utils import read_file_contents


# Page configuration
st.set_page_config(layout="wide")

# Load custom CSS
with open("app/resources/style.css", encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

# Tabs
tab_diagram, tab_pathway, tab_model = st.tabs(
    ["Model Diagram", "About the Stroke Pathway", "About the Model"]
)

# Tab 1: Model diagram
with tab_diagram:
    stmd.st_mermaid(read_file_contents("docs/diagrams/pathway_diagram.mmd"))

# Tab 2: Pathway information
with tab_pathway:
    st.header("Key Stroke Pathway Information")

    st.subheader(
        "What is the difference between CT scanning and CT perfusion scanning?"
    )

    st.write(
        """
CT perfusion (CTP) scanning is an advanced technique that allows stroke
clinicians to identify areas of brain tissue that is irreversibly injured and
that which has the potential for salvage if treated promptly with thrombolysis
(clot-busting drugs) or thrombectomy (mechanical clot removal).

CTP scanning is particularly useful in cases of unknown stroke onset, which is
more common at night or in the early hours of the morning when patients display
stroke symptoms on waking. CTP scans allow clinicians to make their decisions
based on the salvageable brain tissue rather than purely on a standard time
based criteria. This potentially leads to much improved outcomes for
individuals, reducing the level of disability they experience after their
stroke. It can also extend the window for thrombectomy and thrombolysis even
when the onset time is known.

Overall, the use of CTP scanning can improve outcomes and lead to shortened
stays for a range of patients. However, CTP scanning is not always available as
it requires additional software, a modern scanner with a high number of slices,
and people trained in the interpretation of the scans. It also results in a
higher dose of radiation being applied to patients, so its usage needs to be
considered carefully.
        """
    )

    st.subheader("What is the modified Rankin scale (mRS)?")
    st.write("Coming Soon!")

    st.subheader(
        """
        Why can't thrombolysed patients be considered for admission avoidance?
        """
    )
    st.write("Coming Soon!")

# Tab 3: Model information
with tab_model:
    st.header("Where can I find technical details about the model?")
    st.markdown(
        "Additional details can be found on the documentation site: [http://sammirosser.com/jw_hsma_des_stroke_project/](http://sammirosser.com/jw_hsma_des_stroke_project/)"
    )
    # TODO: Link to the documentation and STRESS guidance within documentation

    st.header("What assumptions and simplifications have been made in the model?")

    st.markdown("### Assumptions")
    st.write("""
- If demand increases, it will increase equally across all patient types (ischaemic stroke,
intracerebral haemhorrhage, transient ischaemic attack, stroke mimics, non-stroke).
- Stroke type (I/ICH/TIA/mimic/non) and severity (MRS score) does not vary with time of day.
- Stroke demand does not exhibit weekly or yearly seasonality (i.e. incidence does not change across
the days of the week or the months of the year).
- By default, each SDEC admission avoidance is assumed to avoid a LOS of 1.5 days, though this
is a parameter which can be adjusted in the web app
- By default, thrombolysis is assumed to reduce a patient's stay to 75% of what it would have been.
This parameter can be adjusted in the model code, but is not settable via the web app.
- Patients admitted to a ward are assumed to have a minimum stay of 0.5 days
""")

    st.markdown("### Simplifications")
    st.write("""
- Patients will queue indefinitely for a stroke bed in the stroke ward (and their expected LoS will
not count down during this time).
- Thrombectomy (mechanical clot removal) is not offered.
- All patients meeting the criteria for admission avoidance will avoid admission (i.e. no contraindications are modelled).
- The severity of strokes (in terms of MRS on admission) does not vary by the type of stroke.
- While the onset type of strokes can vary across the course of the day, this cannot be set
independently of the times considered to be in-hours and out-of-hours demand (i.e. they are
effectively linked in the model).
- Patients can be discharged at any time of day.
- If the SDEC is full when a patient requires it, they will move straight to queueing or getting
a bed in the main ward (as opposed to entering the SDEC if space becomes available shortly after
they first attempt to enter it).
- If the stroke ward is full and there are patients either waiting to move from the SDEC to the main
ward or queuing directly for entry to the main ward, patients will be allocated a bed in the main
ward in the order they first requested a bed in the main ward. Patients in the SDEC will request
a bed in the main ward once their sampled time in the SDEC ward has elapsed, but will continue to
occupy an SDEC bed in the meantime until a space is available and they are at the front of the queue.
                          """)

    st.header("Can I adapt and use the model with my own trust?")
    st.write("Coming Soon!")

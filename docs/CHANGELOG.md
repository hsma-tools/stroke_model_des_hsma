# v1.0.0

The main focus of this release is adding an interactive web app frontend to the model.

Where possible, the fundamental structure of the model code has been left unchanged.

Some unavoidable changes to support front end result display, reproducibility, or flexibility of parameter input.

Various bugfixes have also been introduced after discussion with the primary contributor.

Additional comments and docstrings have also been added for readability, and the code has been linted.

However, changes for aesthetic reasons, or where the change would reduce the readability/understandability
of the code for contributors with less experience in coding, have been avoided.

## Summary of key changes to model logic

- Thrombolysis rate was too high as all patients meeting onset time criteria (or eligible if CTP scanned) would then be thrombolysed. Added a contraindication chance parameter to reflect common contraindications like mild stroke symptoms and/or symptoms that are already improving, previous stroke within a certain  time period, severe uncontrolled hypertension, dementia, pregnancy, recently taken certain oral anticoagulants, previous use of thrombolysis for other conditions within a given time period, arriving later in thrombolysable window.
- Interarrival times for day and night were updated to reflect updated data
- Model time 0 reconceptualised as midnight on first day, with SDEC opening hours, CTP opening hours and in-hour/out-of-hour patient arrival generator times all now able to be set independently of each other
- Updated assumptions of % of patients falling into each onset time category (in thrombolysable window - only ct scan required, outside standard thrombolysable window or unknown onset but thrombolysable if ctp scan, not thrombolysable) from 33/33/33 to a split reflective of literature. Also allowed these probabilities to be set independently for in hour and out of hour arrivals to reflect change in number of patients with an unknown onset in out-of-hours.
- Updated counting of thrombolysis savings to ensure that patients were not counted as benefitting from the CTP scanner purely because they had a CTP scan and were then thrombolysed; this incorrectly attributed a benefit of CTP scanning to the patients who would have been thrombolysed even if only a CT scanner had been available (due to known onset).
- Adjusted patient pathways to ensure TIA, stroke mimic and non-stroke patients won't risk bypassing the SDEC if they are not
- Switched from two separate arrival generators for day and night to a single generator using a modified version of the NSPP Thinning distribution from sim-tools, avoiding arrivals exhibiting significant peaks at changeover times between the two generators (which was exacerbated by a bug that led to individuals often being generated at the exact changeover times).
- Adjusted the logic for SDEC admission avoidance eligibility for ICH patients to reflect the lower % of ICH patients avoiding admission compared to ischaemic stroke patients. This is due to the higher clinical risk of ICH patients being discharged that may lead to clinician reluctance or more stringent requirements, which also are not captured well by MRS on arrival, unlike for ischaemic strokes.
- Updated LOS distributions to reflect updated data.
- Adjusted queueing approach for patients moving from SDEC to ward to ensure they do not wait indefinitely in a scenario where the ward is running at full capacity and there is also a queue of patients waiting for direct admission to the ward, which led to a situation where the SDEC patients would never move out of the SDEC as the direct admissions would always being prioritised, blocking SDEC completely as those patients journies would effectively become stuck.
- Adjusted capacity checks for SDEC to ensure capacity was as intended, not 1 bed higher
- Adjusted resource allocation logic for SDEC to ensure patients couldn't be admitted to it during closed hours due to the way the obstruction logic was handled
- Switched distributions to use sim-tools and numpy's seed sequence, allowing for fully reproducible outputs and tests
- Allowed assumption of 1 day bed day saving per avoided admission to be varied

## New features

### Web App

- Built first draft of web app in Streamlit
![](/docs/assets/app_preview.png)
    - Display key metrics relating to model function (e.g. number of patients generated), and model outputs (e.g. money saved)
        - Tracked and displayed new metrics, including
            - thrombolysis rate of eligible patients (per SSNAP definition), separated out by the rate with and without CTP scanned patients
            - extra patients thrombolysed per year
            - Number of patient sper day and year
    - Allow setting of various parameters, including
        - Beds available in ward
        - Beds available in SDEC
        - SDEC and CTP operational hours
        - Default in and out of hour arrival rates (as well as definition of in and out of hours)
        - Uplift in arrival rates
        - Whether SDEC runs with therapy support
        - Cost of beds
            - method of cost calculation for thrombolysis
            - estimated bed day saving per patient of SDEC ([Click here to view commit](https://github.com/hsma-tools/stroke_model_des_hsma/commit/48d0fc409065d6b47a88e0b0b9e85cf7cf433098))
        - Thrombolysis contraindication rate for ischaemic stroke patients
        - Number of runs
        - Run and warm-up duration
        - Random seed
        - Debug message generation (sent to console)
    - Added vidigi animation
    - Added vidigi process maps
        - Allow faceting by two separate variables
    - Added ward and SDEC occupancy plots
        - Added warm-up duration line to ward plot to allow visual assessment of whether warm-up period is appropriate
    - Added debugging plot for all patient attributes
    - Added about page with process diagram and placeholders for pathway and model FAQs, including list of assumptions and simplifications in the model
    - Added ability to compare previously run scenarios in app interface against a selectable 'baseline' run
    - Added ability to save and load previous runs into app for easy access in the scenario comparison tab

### Documentation

- Add numpydoc-style docstrings to all core model features
- Wrote comprehensive README
- Set up documentation site using mkdocs, mkdocs-material and mkdocstrings
    - Set up automatic building and publishing of site with GitHub action
    - Added .nojekyll file to ensure GitHub doesn't try to post-process the built site
- Built model flow diagram with Mermaid (/docs/diagrams/pathway_diagram.mmd)
    - This is also available to view in the 'About' page of the Streamlit app
- Added first draft of STRESS DES model documentation
    - This can be viewed as part of the documentation site

### Automated Tests

- Added
    - backtest (test against a known 'good' set of results)
    - test for the same results being generated when the same paramaters and seed are used
    - test for **different** results being generated when the same parameters and a **different** seed are used
    - various additional tests (see tests/ folder)
- Incorporated test output into documentation site

### Other

- Added devcontainer to allow running of code in web browser (via GitHub codespaces) without requiring local Python install

## Enhancements

### Unavailability times for CTP and SDEC

- Adjusted how ctp_value and sdec_value are set up and used across the model, making it consistent across the script running and app methods and more consistent with how other variables are managed (i.e. using g class)
- Allow independent setting of the start hour for CTP and SDEC
    - Previously, the CTP and SDEC would always have their first period of availability commencing at sim time 0.
    - Sim time 0 has been reconceptualised to be midnight on the first simulated day.
    - Users can now provide separate offsets to separate the start time of CTP and SDEC
    - This also makes conversion of sim time to clock time more intuitive
    - This also allows the start of the in/out of hours patient arrivals to be defined separately (and more intuitively) to the first period of scanning or SDEC availability

### Patient Arrivals

- Significantly adjusted how the inter-arrival time parameter is handled in the app to allow for demand adjustment via the web app interface (as the way it was being done meant a denominator was used that did not intuitively map back to the inter-arrival time)
    - this new approach more closely matches how inter-arrival time is defined in resources like HSMA's 'the little book of DES'
    - calculations were adjusted so that the average inter-arrival time passed through to the distribution **did not change**
- Allowed setting the start and end times of the arrival time periods
    - Previously, the start time of the first frequent arrival (daytime) period would be at sim time 0
    - Sim time 0 has been reconceptualised to be midnight on the first simulated day.
    - The start time and duration of the high/low arrival periods can now be set
    - As mentioned in the CTP/SDEC section, this means that the arrival time periods can be decoupled from the CTP and SDEC availability times if desired
- Switched to a single patient generator that uses the non-stationary poisson process thinning algorithm.
    - This avoids arrivals being higher at the start of the changeover to the lower rate period and gradually declining.
    - This was done after several other approaches
    - This currently uses a custom modified version of the NSPPThinning distribution from sim-tools as it appears there is a bug in the sim-tools implementation, which led to unexpected peaks still being present.
- Updated IAT defaults to reflect updated real-world data

### Patient object

- Switched
    - float and integer defaults from 0 to np.NaN.
    - boolean defaults from False to None (with the exception of 'journey_complete').
    - This all helps to avoid masking subtle bugs arising from attributes not getting set, as well as the possibility of metric calculations being influenced by incorrect 0 values.
- Added method that tests that all patient attributes that should always have a value set during the course of the model display this behaviour
- Recorded various additional attributes in patient object for easier referencing later
- Split joint CT/CTP scanning attributes into separate attributes for easier debugging and pathway tracking
- Adjust setting of onset type so that it can vary for patients generated in hours and out-of-hours
    - set default so that slightly more patients will arrive with an unknown onset time during out-of-hours (which defaults to overnight period from midnight to 7am) than daytime hours
        - this has had preliminary values set based on https://strokeaudit.org/SupportFiles/Documents/Posters-and-oral-presentations/2020/ESOC-2020-Onset-to-arrival-times_Poster.aspx but will need replacing with more accurate values
    - may wish to decouple the time boundaries for this from the time boundaries for arrival rate in the future
- Created a new attribute for tracking when patients with TIA, stroke-mimic or non-stroke are avoiding admission due to admission % chance check versus when ICH and I patients avoid admission in the 'true' sense (the sense that this model is primarily interested in)
    - this reduces the complexity around ensuring that patients leave the model at the point they should be eligible to, making it easier to follow what is going on for different patient groups

### Animation and generated pathway diagrams

- Switched from simpy resources to equivalent vidigi resources to support the recording of resource IDs in logs
- Added function to convert produced log into vidigi-style event log (`app/convert_event_log.py`)
- Animation and pathway diagrams added to web app interface

### Patient Pathways

- Generally reviewed patient pathways to check behaviour for each subgroup of patients is correct, based on revised understanding of pathways from conversations with original model builder.
    - Checked subgroups by
        - SDEC being open
        - SDEC being full/having capacity
        - CT/CTP scanner availability
        - Patient diagnosis type
        - Admission avoidance flag
        - Thrombolysis
- Refine admission avoidance criteria to better reflect real-world patterns; reduce the number of ICH patients eligible for admission avoidance

### Reproducibility

- Enhanced controllable randomness and reproducibility
    - Set up distinct random number streams per generator and activity using sim-tools distributions
    - Set up uncorrelated random number streams using np.seedsequence
    - Allowed user control of 'master' random seed used by np.seedsequence in g class and web frontend
    - This makes it easier to confirm whether changes are materially affecting the outcome, assisting debugging and testing efforts

### Other

- Added logging of model steps using the sim-tools trace function
    - Rich logging of individual steps enhances debugging and understanding of the model for those who are less familiar with its structure
    - Clock-time aware logging (i.e. using 'real' time with am/pm, rather than just sim-start relative time) used to make logs easier to interpret
    - This can be toggled in the web app interface
- Added patient objects to a list in the model, allowing for easy individual post-hoc querying of all recorded patient attributes
- Recorded various additional attributes in trial object for easier referencing later

## Bugfixes

### SDEC

- Fixed typo in conditional check where it was accidentally looking at the sdec_value in the case where sdec_value was 100, where instead it should have been checking for ctp_value == 100 in that branch ([Click here to view commit, though note it's not showing the original code properly](https://github.com/hsma-tools/stroke_model_des_hsma/commit/e5f653217ba40c3364cefcbad21dfb7951dc7eec))
- Swapped SDEC fullness check from <= to < (as previously may have allowed patients in if SDEC at capacity)
    - **note that this has also been added into the original repository** (https://github.com/jfwilliams4/des_stroke_project/commit/d68374d3b24ab28609f63eb4eb2019ac0d7faf85)
- Remove resource check from SDEC admission code as this was seemingly sometimes causing delayed arrivals ([Click here to view commit](https://github.com/hsma-tools/stroke_model_des_hsma/commit/aedd7cd5555424984c63becc2d95ef548974956e)) where the patient would enter SDEC during a period where SDEC should be closed
- Refactored SDEC savings code to ensure that savings are calculated intuitively/consistently across different parts of the model ([Click here to view commit](https://github.com/hsma-tools/stroke_model_des_hsma/commit/dc675eab495cd1d9641ead67c897eb0bfdecc71f))

### Patient Pathways

- Adjust admission avoidance code to ensure that non-stroke/TIA/stroke mimics patients never incorrectly jump from CT/CTP scan to discharge when the SDEC is open, and will always spend time in the SDEC at least
- Adjust prioritisation of patients in the situation where the ward is full, ensuring SDEC patients will eventually move out of the SDEC (whereas previously patients waiting directly for a ward bed would always be prioritised, meaning that patients waiting to move from SDEC to ward could never progress their journey)

### Thrombolysis

- Added a new flag to differentiate between patients for whom the CTP enables their thrombolysis treatment (i.e. those with an onset type of 1 - unknown but inside thrombolysable window or known and inside extended thrombolysable window with CTP).
    - this has replaced the logic check used to determine whether patients' savings should be counted, so fewer patients now meet the threshold for being counted as a thrombolysis saving ([Click here to view commit](https://github.com/hsma-tools/stroke_model_des_hsma/commit/94e0303f2ec5a9642dbbc298f050a40fe89f2e0b))
- Added an additional step in thrombolysis to reflect the fact that not all patients who are eligible for thrombolysis on the basis of their arrival time will be eligible for thrombolysis in reality due to factors such as absolute or relative contraindications (e.g. mild stroke symptoms and/or symptoms that are already improving, previous stroke within a certain  time period, severe uncontrolled hypertension, dementia, pregnancy, recently taken certain oral anticoagulants, previous use of thrombolysis for other conditions within a given time period, arriving later in thrombolysable window). See https://pmc.ncbi.nlm.nih.gov/articles/PMC9323435/ which found that 47% of patients who had a known onset <4.5 hours ago were not treated with thrombolysis, with 26% having absolute contraindication and 74% having relative contraindication, as well as https://pmc.ncbi.nlm.nih.gov/articles/PMC9890612/ and https://www.ncbi.nlm.nih.gov/books/NBK557411/.
    - Before applying this, thrombolysis rates in the model were unreasonably high once the onset time ratio had been moved from placeholder defaults (33/33/33 split of known, thrombolysable if CTPd, not thrombolysable) to more realistic defaults informed by literature
    - See [commit](https://github.com/hsma-tools/stroke_model_des_hsma/commit/94e0303f2ec5a9642dbbc298f050a40fe89f2e0b)

### Patients

- Fixed bug in patient diagnosis allocation where a diagnosis between the stroke mimic and non-stroke threshold would not get allocated any diagnosis ([Click here to view commit](https://github.com/hsma-tools/stroke_model_des_hsma/commit/ccecec1b5c6c1239b43951265a8ef72dbf1cc319))
    - note that this has also been added into the original repository (https://github.com/jfwilliams4/des_stroke_project/commit/d68374d3b24ab28609f63eb4eb2019ac0d7faf85)
- Ensured ward LOS was recorded in patient object for both thrombolysed and non-thrombolysed patients ([Click here to view commit](https://github.com/hsma-tools/stroke_model_des_hsma/commit/874069fcf5081925f7f460f7caf2ba9f570b440b))

## Code Admin and Structure Changes

- Updated structure of code to package structure to support better long-term development and use of additional documentation tools
    - Model classes split into separate file to model running code
    - All code moved into src/stroke_ward_model
    - Classes split into separate files as some had become very long after adding docstrings
    - Added pyproject.toml file
- Added "MARK" comments as markers to enable richer code minimap in core classes.
    - These will appear if you are using the VSCode minimap
- Updated gitignore with wildcards to make matching of additional results files more robust
- Added a minimal requirements.txt and environment.yml files to replace strongly specified win_environment and mac_environment folders
    - Added new requirements including streamlit, mkdocs, mkdocs-material, mkdocstrings, vidigi, pytest
- Added a separate requirements.txt file for web app
    - This removes the requirements that are not required for the web app, such as mkdocs and pytest
    - This will be picked up by Streamlit community cloud, and shortens the load time for container reloads
- Refactored ward admission code to reduce the number of conditional blocks required for ward stays

# v0.1.0

Initial model release (Considered JW original model).

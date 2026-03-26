# Running the model locally

## Environment setup

Install the environment using `requirements.txt` or `environment.yml` (tested with Python 3.12.10), found in the `environment/` folder.

This should automatically install the model code. If you receive errors about `stroke_ward_model` not being found in the environment you created then run: `pip install -e .`

**Note:** Legacy environments are also available in `win_environment/` and `mac_environment/`, but it is recommended that you use those provided in `environment/`.

## Running the model

To run the model via a script, with prompts for input variables, run the file `scripts/run_stroke_admission_model.py`.

## Web app

It is possible to run the model via a script, but for easy access to model parameters and all results tables and outputs, it is recommended to use the web app interface.

The hosted web app is available at [stroke-model-des.streamlit.app/](https://stroke-model-des.streamlit.app/).

If you are unable to install Python code locally, you can use this free hosted version of the app, though note it may run more slowly.

[Click here to access the hosted version of the web app](app.md){.md-button}

To run the web app locally, you will need to install a separate environment provided in the `app/` folder. This is a reduced environment used by the hosted version of the web app on Streamlit Community Cloud. It does not install `mkdocs`, `pytest`, and other packages needed only for wider repository tasks. This `app/` environment must be manually updated whenever changes are made to the files in `environment/`.

Once the environment is installed, open a terminal in the root of the repository and run:

```
streamlit run app/streamlit_app.py
```

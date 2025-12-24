import marimo

# TODO: pagination?! https://docs.dune.com/api-reference/overview/sdks#filtering-and-pagination

__generated_with = "0.18.4"
app = marimo.App(width="medium", auto_download=["ipynb"])


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    from dune_client.client import DuneClient

    return (DuneClient,)


@app.cell
def _(mo):
    from dotenv import load_dotenv, find_dotenv
    import os

    load_dotenv(find_dotenv())
    DUNE_API_KEY = os.getenv("DUNE_API_KEY")
    mo.stop(not DUNE_API_KEY, mo.md("DUNE_API_KEY not found in environment variables."))
    return (DUNE_API_KEY,)


@app.cell
def _(DUNE_API_KEY, DuneClient):
    dune = DuneClient(api_key=DUNE_API_KEY)
    return (dune,)


@app.cell
def _(mo):
    qid_text = mo.ui.text(label="Query ID", value="6356226")
    qid_text
    return (qid_text,)


@app.cell
def _(mo):
    get_result_btn = mo.ui.run_button()
    get_result_btn
    return (get_result_btn,)


@app.cell
def _(get_result_btn, mo):
    mo.stop(not get_result_btn.value, mo.md("Click run button first."))
    return


@app.cell
def _(dune, qid_text):
    df = dune.get_latest_result_dataframe(qid_text.value)
    df
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()

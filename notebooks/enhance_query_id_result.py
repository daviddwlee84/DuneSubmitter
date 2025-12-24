import marimo

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
def _(DUNE_API_KEY, mo, qid_text):
    # Preview query metadata to understand data size
    import requests

    try:
        response = requests.get(
            f"https://api.dune.com/api/v1/query/{qid_text.value}/results?limit=1",
            headers={"x-dune-api-key": DUNE_API_KEY},
        )
        response.raise_for_status()
        data = response.json()
        meta = data["result"]["metadata"]

        rows = meta["total_row_count"]
        cols = len(meta["column_names"])
        size_mb = meta["total_result_set_bytes"] / 1024 / 1024
        datapoints = rows * cols
        max_rows_free = 250_000 // cols if cols > 0 else 0
        needs_batching = datapoints > 250_000

        status = (
            "⚠️ **需要分批下載** (SDK 會自動分批，但 batch_size 需調低)"
            if needs_batching
            else "✅ 可以直接下載"
        )
        column_preview = ", ".join(meta["column_names"][:5]) + (
            "..." if cols > 5 else ""
        )

        mo.output.replace(
            mo.md(
                f"""
    ### 📊 Query Metadata

    | 屬性 | 值 |
    |------|-----|
    | Total Rows | **{rows:,}** |
    | Columns | **{cols}** ({column_preview}) |
    | Data Size | **{size_mb:.2f} MB** |
    | Total Datapoints | **{datapoints:,}** |
    | Free Tier Limit | 250,000 datapoints |
    | Max Rows (Free) | **{max_rows_free:,}** rows |

    {status}
    """
            )
        )
    except Exception as e:
        mo.output.replace(mo.md(f"⚠️ 無法獲取 metadata: {e}"))
    return


@app.cell
def _(mo):
    # Free tier has 250,000 datapoint limit per request
    # datapoints = rows × columns
    # For queries with many columns, we need smaller batch_size
    batch_size_input = mo.ui.number(
        label="Batch size (rows per request, lower for wide tables)",
        value=10000,
        start=100,
        stop=32000,
        step=100,
    )
    batch_size_input
    return (batch_size_input,)


@app.cell
def _(batch_size_input, dune, mo, qid_text):
    try:
        df = dune.get_latest_result_dataframe(
            qid_text.value,
            batch_size=batch_size_input.value,
        )
        mo.output.replace(df)
    except Exception as e:
        error_msg = str(e)
        if "402" in error_msg or "Payment Required" in error_msg:
            if "billing cycle" in error_msg.lower():
                # Monthly limit exceeded
                mo.output.replace(
                    mo.md(
                        f"""
    ## ❌ Monthly Billing Cycle Limit Exceeded

    **Error:** {error_msg}

    **原因：** 您的 Dune 帳戶本月 datapoint 配額已用完。

    **解決方法：**
    1. 等待下個月配額重置
    2. 升級 Dune 訂閱計劃
    3. 使用 JSON API 替代（見下方範例）

    **JSON API 替代方案：**
    ```bash
    curl -H "x-dune-api-key: $DUNE_API_KEY" \\
     "https://api.dune.com/api/v1/query/{qid_text.value}/results?limit=1000"
    ```
    """
                    )
                )
            else:
                # Per-request limit exceeded
                mo.output.replace(
                    mo.md(
                        f"""
    ## ❌ Per-Request Datapoint Limit Exceeded

    **Error:** {error_msg}

    **原因：** 單次請求 datapoints 超過 250,000 限制。

    **解決方法：**
    1. 降低 batch_size（當前: {batch_size_input.value}）
    2. Dune Free tier 限制每次請求 250,000 datapoints（rows × columns）
    3. 如果資料有 10 列，最多只能請求 ~25,000 rows

    **建議：** 嘗試將 batch_size 設為 5000 或更低
    """
                    )
                )
        else:
            mo.output.replace(mo.md(f"**Error:** {e}"))
    return


@app.cell
def _(dune, mo):
    # Display API usage information
    try:
        usage = dune.get_usage()
        if usage.billing_periods:
            bp = usage.billing_periods[0]
            remaining = bp.credits_included - bp.credits_used
            pct_used = (bp.credits_used / bp.credits_included) * 100

            status_emoji = "🟢" if pct_used < 80 else "🟡" if pct_used < 95 else "🔴"

            mo.output.replace(
                mo.md(
                    f"""
    ### 💳 API Usage ({bp.start_date} ~ {bp.end_date})

    | 項目 | 值 |
    |------|-----|
    | Credits 已用 | {bp.credits_used:,.2f} / {bp.credits_included:,.0f} ({pct_used:.1f}%) |
    | Credits 剩餘 | {remaining:,.2f} {status_emoji} |
    """
                )
            )
    except Exception as e:
        mo.output.replace(mo.md(f"⚠️ 無法獲取使用量: {e}"))
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()

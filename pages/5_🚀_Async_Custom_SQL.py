import re
import time
import streamlit as st
import pandas as pd
from dune_client.models import ExecutionState
from shared_components import (
    set_api_key_and_get_dune_client,
    display_results,
    display_download_buttons,
    display_column_info,
    render_sidebar_settings,
    MAX_DISPLAY_ROWS,
    DEFAULT_CACHE_TTL,
)

# Page configuration
st.set_page_config(
    page_title="Async Custom SQL - Dune",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 Async Custom SQL Execution")
st.markdown("""
Write arbitrary SQL and execute it asynchronously using the `execute_sql` endpoint.
This uses the direct SQL execution API which may be available without a Plus subscription.

**Flow:** Submit SQL → Get Execution ID → Poll Status → Fetch Results
""")

# Sidebar
with st.sidebar:
    dune_client = set_api_key_and_get_dune_client()
    if dune_client:
        st.success("✓ Dune client initialized")
    else:
        st.warning("⚠️ Enter your Dune API key to continue")
        st.stop()

    _, max_display_rows = render_sidebar_settings()

    st.divider()
    st.markdown("### Polling Settings")
    poll_interval = st.slider(
        "Poll interval (seconds)",
        min_value=1,
        max_value=30,
        value=3,
        help="How often to check execution status",
    )
    max_wait_time = st.number_input(
        "Max wait time (seconds)",
        min_value=30,
        max_value=3600,
        value=300,
        help="Maximum time to wait for query completion",
    )


def parse_parameters(sql: str) -> list[str]:
    """
    Extract {{parameter_name}} patterns from SQL query.
    Returns a list of unique parameter names in order of appearance.
    """
    pattern = r"\{\{(\w+)\}\}"
    matches = re.findall(pattern, sql)
    seen = set()
    unique_params = []
    for param in matches:
        if param not in seen:
            seen.add(param)
            unique_params.append(param)
    return unique_params


def substitute_parameters(sql: str, param_values: dict[str, str]) -> str:
    """
    Replace {{parameter_name}} placeholders with actual values.
    """
    result = sql
    for param_name, value in param_values.items():
        escaped_value = value.replace("'", "''")
        result = result.replace(f"{{{{{param_name}}}}}", escaped_value)
    return result


# Initialize session state
if "async_sql_execution_id" not in st.session_state:
    st.session_state.async_sql_execution_id = None

# Main content - Two tabs
tab1, tab2 = st.tabs(["🚀 Execute SQL", "📋 Check Execution"])

with tab1:
    st.markdown("### Write Your SQL Query")

    # Example query
    with st.expander("📖 Example Query with Parameters"):
        st.code(
            """SELECT 
    blockchain,
    block_date,
    COUNT(*) as trade_count
FROM dex.trades 
WHERE blockchain = '{{blockchain}}'
    AND block_date >= DATE '{{start_date}}'
GROUP BY 1, 2
ORDER BY 2 DESC
LIMIT 100""",
            language="sql",
        )
        st.caption(
            "Parameters like `{{blockchain}}` will be detected and substituted before execution."
        )

    # SQL Query input
    sql_query = st.text_area(
        "SQL Query",
        height=200,
        placeholder="SELECT * FROM dex.trades WHERE blockchain = '{{blockchain}}' LIMIT 10",
        help="Use {{parameter_name}} syntax for dynamic parameters.",
        key="async_sql_query",
    )

    # Parse parameters
    detected_params = parse_parameters(sql_query)

    if detected_params:
        st.info(
            f"🔍 Detected parameters: {', '.join([f'`{{{{{p}}}}}`' for p in detected_params])}"
        )

    # Parameter inputs
    param_values = {}
    if detected_params:
        st.markdown("#### Parameters")
        cols = st.columns(min(len(detected_params), 3))
        for i, param in enumerate(detected_params):
            col_idx = i % 3
            with cols[col_idx]:
                param_values[param] = st.text_input(
                    f"{param}",
                    key=f"async_sql_param_{param}",
                    placeholder=f"Enter value for {param}",
                )

    # Performance selection
    performance = st.selectbox(
        "Performance Level",
        options=["medium", "large"],
        index=0,
        help="'medium' is faster and cheaper. 'large' for complex queries.",
        key="async_sql_performance",
    )

    # Submit button
    if st.button(
        "🚀 Start Execution", use_container_width=True, type="primary", key="start_sql_exec"
    ):
        if not sql_query.strip():
            st.error("Please enter a SQL query.")
        else:
            # Check all parameters have values
            missing_params = [
                p for p in detected_params if not param_values.get(p, "").strip()
            ]
            if missing_params:
                st.error(f"Please provide values for: {', '.join(missing_params)}")
            else:
                # Substitute parameters
                final_sql = substitute_parameters(sql_query, param_values)

                with st.expander("📝 Final SQL Query", expanded=False):
                    st.code(final_sql, language="sql")

                try:
                    with st.spinner("Starting execution..."):
                        # Use execute_sql directly from ExecutionAPI
                        response = dune_client.execute_sql(
                            query_sql=final_sql, performance=performance
                        )

                    st.session_state.async_sql_execution_id = response.execution_id

                    st.success(f"✅ Execution started!")
                    st.info(f"Execution ID: `{response.execution_id}`")
                    st.caption(
                        "Switch to the 'Check Execution' tab to monitor progress and get results."
                    )

                except Exception as e:
                    st.error(f"❌ Failed to start execution: {e}")

                    # Check for subscription error
                    error_msg = str(e).lower()
                    if "plus" in error_msg or "subscription" in error_msg or "upgrade" in error_msg:
                        st.warning(
                            "💡 This endpoint may require a Dune Plus subscription. "
                            "Try using the **Sync Query** page to execute existing queries instead."
                        )

with tab2:
    st.markdown("### Check Execution Status")

    # Execution ID input
    col1, col2 = st.columns([3, 1])
    with col1:
        execution_id_input = st.text_input(
            "Execution ID",
            value=st.session_state.async_sql_execution_id or "",
            placeholder="Enter execution ID or use the one from 'Execute SQL'",
            help="The execution ID returned when starting a query",
            key="async_sql_exec_id_input",
        )
    with col2:
        if st.session_state.async_sql_execution_id:
            st.caption("From last execution:")
            exec_id = st.session_state.async_sql_execution_id
            st.code(exec_id[:20] + "..." if len(exec_id) > 20 else exec_id)

    execution_id = execution_id_input.strip()

    col1, col2, col3 = st.columns(3)

    with col1:
        check_status = st.button(
            "🔄 Check Status", use_container_width=True, key="check_sql_status"
        )

    with col2:
        poll_and_wait = st.button(
            "⏳ Poll Until Complete", use_container_width=True, key="poll_sql_wait"
        )

    with col3:
        cancel_exec = st.button(
            "❌ Cancel Execution", use_container_width=True, key="cancel_sql_exec"
        )

    if execution_id:
        # Check status
        if check_status:
            try:
                status = dune_client.get_execution_status(execution_id)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("State", status.state.value)
                with col2:
                    if status.queue_position:
                        st.metric("Queue Position", status.queue_position)

                if status.state == ExecutionState.COMPLETED:
                    st.success("Query execution completed! Click 'Get Results' below.")
                elif status.state == ExecutionState.EXECUTING:
                    st.info("Query is still executing...")
                elif status.state == ExecutionState.PENDING:
                    st.info("Query is pending in queue...")
                elif status.state == ExecutionState.FAILED:
                    st.error("Query execution failed!")
                    if status.error:
                        st.error(f"Error: {status.error.message}")

            except Exception as e:
                st.error(f"❌ Failed to get status: {e}")

        # Poll until complete
        if poll_and_wait:
            progress_bar = st.progress(0)
            status_text = st.empty()
            start_time = time.time()

            try:
                while True:
                    elapsed = time.time() - start_time
                    progress = min(elapsed / max_wait_time, 1.0)
                    progress_bar.progress(progress)

                    if elapsed > max_wait_time:
                        st.warning(
                            f"⏰ Max wait time ({max_wait_time}s) exceeded. "
                            "Query may still be running."
                        )
                        break

                    status = dune_client.get_execution_status(execution_id)
                    status_text.write(
                        f"Status: **{status.state.value}** | Elapsed: {elapsed:.1f}s"
                    )

                    if status.state == ExecutionState.COMPLETED:
                        progress_bar.progress(1.0)
                        st.success("✅ Query execution completed!")
                        break
                    elif status.state == ExecutionState.FAILED:
                        st.error("❌ Query execution failed!")
                        if status.error:
                            st.error(f"Error: {status.error.message}")
                        break
                    elif status.state in [
                        ExecutionState.CANCELLED,
                        ExecutionState.EXPIRED,
                    ]:
                        st.warning(f"Query execution {status.state.value}")
                        break

                    time.sleep(poll_interval)

            except Exception as e:
                st.error(f"❌ Error during polling: {e}")

        # Cancel execution
        if cancel_exec:
            try:
                success = dune_client.cancel_execution(execution_id)
                if success:
                    st.success("✅ Execution cancelled successfully!")
                else:
                    st.warning("Cancellation request sent, but may not have succeeded.")
            except Exception as e:
                st.error(f"❌ Failed to cancel execution: {e}")

        # Get results button
        st.divider()
        st.markdown("### Get Results")

        if st.button(
            "📥 Get Results", use_container_width=True, type="primary", key="get_sql_results"
        ):
            try:
                with st.spinner("Fetching results..."):
                    results = dune_client.get_execution_results(execution_id)

                if results.state != ExecutionState.COMPLETED:
                    st.warning(
                        f"Query is not complete. Current state: {results.state.value}"
                    )
                else:
                    rows = results.result.rows if results.result else []
                    df = pd.DataFrame(rows) if rows else pd.DataFrame()

                    if df.empty:
                        st.info("Query returned no results.")
                    else:
                        # Display execution info
                        with st.expander("🔍 Execution Info", expanded=False):
                            st.write(f"**Execution ID:** `{results.execution_id}`")
                            st.write(
                                f"**State:** {results.state.value if results.state else 'N/A'}"
                            )
                            if results.times:
                                st.write(f"**Submitted:** {results.times.submitted_at}")
                                st.write(
                                    f"**Started:** {results.times.execution_started_at}"
                                )
                                st.write(f"**Ended:** {results.times.execution_ended_at}")

                        # Display results
                        display_results(df, max_display_rows)

                        # Download buttons
                        display_download_buttons(df, f"async_sql_{execution_id[:8]}")

                        # Column info
                        display_column_info(df)

            except Exception as e:
                st.error(f"❌ Failed to get results: {e}")
    else:
        st.info("Enter an execution ID to check status or get results.")


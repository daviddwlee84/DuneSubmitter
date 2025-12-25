import streamlit as st
import pandas as pd
import time
from dune_client.query import QueryBase
from dune_client.models import ExecutionState
from shared_components import (
    set_api_key_and_get_dune_client,
    display_results,
    display_download_buttons,
    display_column_info,
    render_sidebar_settings,
    MAX_DISPLAY_ROWS,
)

# Page configuration
st.set_page_config(
    page_title="Async Query - Dune",
    page_icon="⏳",
    layout="wide",
)

st.title("⏳ Async Query Execution")
st.markdown(
    """
Start a query execution asynchronously, monitor its progress, and retrieve results 
when complete. This is useful for long-running queries.

**Note:** This uses execution credits from your Dune account.
"""
)

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

# Initialize session state for async execution
if "execution_id" not in st.session_state:
    st.session_state.execution_id = None
if "execution_status" not in st.session_state:
    st.session_state.execution_status = None

# Main content
tab1, tab2 = st.tabs(["🚀 Start Execution", "📋 Check Existing Execution"])

with tab1:
    st.markdown("### Start New Query Execution")

    # Query ID input
    query_id = st.number_input(
        "Query ID",
        min_value=1,
        value=None,
        placeholder="Enter Dune Query ID",
        help="Find this in the Dune query URL: https://dune.com/queries/[QUERY_ID]",
        key="new_query_id",
    )

    # Parameters section
    st.markdown("### Query Parameters (Optional)")

    if "async_param_count" not in st.session_state:
        st.session_state.async_param_count = 1

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Add Parameter", key="add_async_param"):
            st.session_state.async_param_count += 1
            st.rerun()

    # Collect parameters
    params_list = []
    for i in range(st.session_state.async_param_count):
        col1, col2, col3 = st.columns([2, 3, 1])
        with col1:
            param_name = st.text_input(
                "Name",
                key=f"async_param_name_{i}",
                placeholder="blockchain",
                label_visibility="collapsed" if i > 0 else "visible",
            )
        with col2:
            param_value = st.text_input(
                "Value",
                key=f"async_param_value_{i}",
                placeholder="ethereum",
                label_visibility="collapsed" if i > 0 else "visible",
            )
        with col3:
            if i > 0 and st.button("🗑️", key=f"async_remove_{i}"):
                st.session_state.async_param_count = max(
                    1, st.session_state.async_param_count - 1
                )
                st.rerun()

        if param_name.strip() and param_value.strip():
            params_list.append(
                {"name": param_name.strip(), "value": param_value.strip()}
            )

    # Performance selection
    performance = st.selectbox(
        "Performance Level",
        options=["medium", "large"],
        index=0,
        help="'medium' is faster and cheaper. 'large' for complex queries.",
        key="async_performance",
    )

    # Start execution button
    if st.button(
        "🚀 Start Execution", width="stretch", type="primary", key="start_exec"
    ):
        if not query_id:
            st.error("Please enter a Query ID.")
        else:
            try:
                from dune_client.types import QueryParameter

                # Build parameters
                params = [
                    QueryParameter.text_type(name=p["name"], value=p["value"])
                    for p in params_list
                ]

                # Create query object
                query = QueryBase(
                    query_id=query_id,
                    params=params if params else None,
                )

                # Start execution
                with st.spinner("Starting execution..."):
                    response = dune_client.execute_query(query, performance=performance)

                st.session_state.execution_id = response.execution_id
                st.session_state.execution_status = response.state.value

                st.success(f"✅ Execution started!")
                st.info(f"Execution ID: `{response.execution_id}`")
                st.caption(
                    "Switch to the 'Check Existing Execution' tab to monitor progress."
                )

            except Exception as e:
                st.error(f"❌ Failed to start execution: {e}")

with tab2:
    st.markdown("### Check Execution Status")

    # Execution ID input
    col1, col2 = st.columns([3, 1])
    with col1:
        execution_id_input = st.text_input(
            "Execution ID",
            value=st.session_state.execution_id or "",
            placeholder="Enter execution ID or use the one from 'Start Execution'",
            help="The execution ID returned when starting a query",
        )
    with col2:
        if st.session_state.execution_id:
            st.caption("From last execution:")
            st.code(st.session_state.execution_id[:20] + "...")

    execution_id = execution_id_input.strip()

    col1, col2, col3 = st.columns(3)

    with col1:
        check_status = st.button("🔄 Check Status", width="stretch", key="check_status")

    with col2:
        poll_and_wait = st.button(
            "⏳ Poll Until Complete", width="stretch", key="poll_wait"
        )

    with col3:
        cancel_exec = st.button(
            "❌ Cancel Execution", width="stretch", key="cancel_exec"
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
                        f"Status: **{status.state.value}** | "
                        f"Elapsed: {elapsed:.1f}s"
                    )

                    if status.state == ExecutionState.COMPLETED:
                        progress_bar.progress(1.0)
                        st.success("✅ Query execution completed!")
                        break
                    elif status.state == ExecutionState.FAILED:
                        st.error("❌ Query execution failed!")
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
            "📥 Get Results", width="stretch", type="primary", key="get_results"
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
                                st.write(
                                    f"**Ended:** {results.times.execution_ended_at}"
                                )

                        # Display results
                        display_results(df, max_display_rows)

                        # Download buttons
                        display_download_buttons(
                            df, f"execution_{execution_id}_results"
                        )

                        # Column info
                        display_column_info(df)

            except Exception as e:
                st.error(f"❌ Failed to get results: {e}")
    else:
        st.info("Enter an execution ID to check status or get results.")

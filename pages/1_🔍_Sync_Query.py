import streamlit as st
import pandas as pd
from dune_client.query import QueryBase
from shared_components import (
    set_api_key_and_get_dune_client,
    build_query_parameters,
    display_results,
    display_download_buttons,
    display_column_info,
    display_execution_metadata,
    results_to_dataframe,
    render_sidebar_settings,
    MAX_DISPLAY_ROWS,
    DEFAULT_CACHE_TTL,
)

# Page configuration
st.set_page_config(
    page_title="Sync Query - Dune",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Sync Query Execution")
st.markdown("""
Execute an existing Dune query by its Query ID. The execution will wait until 
the query completes and return the results.

**Note:** This uses execution credits from your Dune account.
""")

# Sidebar
with st.sidebar:
    dune_client = set_api_key_and_get_dune_client()
    if dune_client:
        st.success("✓ Dune client initialized")
    else:
        st.warning("⚠️ Enter your Dune API key to continue")
        st.stop()

    cache_ttl, max_display_rows = render_sidebar_settings()


# Cached query execution
@st.cache_data(ttl=DEFAULT_CACHE_TTL, show_spinner="Executing query on Dune...")
def execute_query_cached(
    query_id: int,
    params_json: str,  # JSON string for cache key
    performance: str,
    api_key: str,
) -> tuple[dict | None, str | None]:
    """
    Execute the query on Dune and return results.
    Uses api_key and params_json as cache key dependencies.
    Returns (result_dict, error_message) tuple.
    """
    import json
    from dune_client.client import DuneClient
    from dune_client.types import QueryParameter

    try:
        client = DuneClient(api_key=api_key)

        # Parse parameters from JSON
        params_list = json.loads(params_json) if params_json else []
        params = [
            QueryParameter.text_type(name=p["name"], value=p["value"])
            for p in params_list
        ]

        # Create query object
        query = QueryBase(
            query_id=query_id,
            params=params if params else None,
        )

        # Execute query
        results = client.run_query(query, performance=performance)

        # Convert to serializable format for caching
        rows = results.result.rows if results.result else []
        return {
            "rows": rows,
            "execution_id": results.execution_id,
            "state": results.state.value if results.state else None,
        }, None

    except Exception as e:
        return None, str(e)


# Main content
st.markdown("### Query Configuration")

# Query ID input
query_id = st.number_input(
    "Query ID",
    min_value=1,
    value=None,
    placeholder="Enter Dune Query ID (e.g., 1215383)",
    help="Find this in the Dune query URL: https://dune.com/queries/[QUERY_ID]",
)

# Parameters section
st.markdown("### Query Parameters (Optional)")
st.caption(
    "Add parameters if the query requires them. "
    "Parameter names should match those defined in the Dune query."
)

# Dynamic parameter input
if "param_count" not in st.session_state:
    st.session_state.param_count = 1

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("➕ Add Parameter"):
        st.session_state.param_count += 1
        st.rerun()

# Collect parameters
params_list = []
for i in range(st.session_state.param_count):
    col1, col2, col3 = st.columns([2, 3, 1])
    with col1:
        param_name = st.text_input(
            "Name",
            key=f"param_name_{i}",
            placeholder="blockchain",
            label_visibility="collapsed" if i > 0 else "visible",
        )
    with col2:
        param_value = st.text_input(
            "Value",
            key=f"param_value_{i}",
            placeholder="ethereum",
            label_visibility="collapsed" if i > 0 else "visible",
        )
    with col3:
        if i > 0 and st.button("🗑️", key=f"remove_{i}"):
            st.session_state.param_count = max(1, st.session_state.param_count - 1)
            st.rerun()

    if param_name.strip() and param_value.strip():
        params_list.append({"name": param_name.strip(), "value": param_value.strip()})

# Execution settings
st.markdown("### Execution Settings")
col1, col2 = st.columns(2)
with col1:
    performance = st.selectbox(
        "Performance Level",
        options=["medium", "large"],
        index=0,
        help="'medium' is faster and cheaper. 'large' for complex queries.",
    )

with col2:
    force_refresh = st.checkbox(
        "Force refresh (bypass cache)",
        value=False,
        help="Ignore cached results and execute a fresh query.",
    )

# Execute button
submitted = st.button("🚀 Execute Query", use_container_width=True, type="primary")

# Handle execution
if submitted:
    if not query_id:
        st.error("Please enter a Query ID.")
        st.stop()

    # Prepare parameters for caching
    import json

    params_json = json.dumps(params_list) if params_list else ""

    # Show query info
    with st.expander("📝 Query Details", expanded=False):
        st.write(f"**Query ID:** {query_id}")
        st.write(f"**Query URL:** https://dune.com/queries/{query_id}")
        if params_list:
            st.write("**Parameters:**")
            for p in params_list:
                st.write(f"  - `{p['name']}` = `{p['value']}`")

    # Clear cache if force refresh
    if force_refresh:
        execute_query_cached.clear()
        st.toast("Cache cleared!")

    # Execute
    api_key = st.session_state.get("dune_api_key", "")
    result_dict, error = execute_query_cached(
        query_id, params_json, performance, api_key
    )

    if error:
        st.error(f"❌ Query execution failed: {error}")

        if st.button("🔄 Clear cache and retry"):
            execute_query_cached.clear()
            st.rerun()
    elif result_dict:
        st.success("✅ Query completed successfully!")

        # Convert to DataFrame
        rows = result_dict.get("rows", [])
        df = pd.DataFrame(rows) if rows else pd.DataFrame()

        if df.empty:
            st.info("Query returned no results.")
        else:
            # Display execution info
            with st.expander("🔍 Execution Info", expanded=False):
                st.write(f"**Execution ID:** `{result_dict.get('execution_id')}`")
                st.write(f"**State:** {result_dict.get('state')}")

            # Display results
            display_results(df, max_display_rows)

            # Download buttons
            display_download_buttons(df, f"query_{query_id}_results")

            # Column info
            display_column_info(df)


import streamlit as st
import pandas as pd
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
    page_title="Latest Results - Dune",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Latest Results")
st.markdown(
    """
Get the most recent cached results for a query **without re-executing it**.

**This does NOT use execution credits!** Perfect for frequently checking query results
or retrieving data from queries that are scheduled to run periodically.
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

    cache_ttl, max_display_rows = render_sidebar_settings()


# Cached function for getting latest results
@st.cache_data(ttl=DEFAULT_CACHE_TTL, show_spinner="Fetching latest results...")
def get_latest_results_cached(
    query_id: int,
    max_age_hours: int | None,
    api_key: str,
) -> tuple[dict | None, str | None]:
    """
    Get the latest results for a query.
    Returns (result_dict, error_message) tuple.
    """
    from dune_client.client import DuneClient

    try:
        client = DuneClient(api_key=api_key)

        # Get latest results
        # If max_age_hours is set, it may trigger a re-execution if results are too old
        if max_age_hours:
            results = client.get_latest_result(query_id, max_age_hours=max_age_hours)
        else:
            # Use a very large value to always get cached results without re-executing
            results = client.get_latest_result(
                query_id, max_age_hours=2191
            )  # ~3 months

        rows = results.result.rows if results.result else []
        return {
            "rows": rows,
            "execution_id": results.execution_id,
            "state": results.state.value if results.state else None,
            "submitted_at": (
                str(results.times.submitted_at)
                if results.times and results.times.submitted_at
                else None
            ),
            "execution_ended_at": (
                str(results.times.execution_ended_at)
                if results.times and results.times.execution_ended_at
                else None
            ),
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
    placeholder="Enter Dune Query ID",
    help="Find this in the Dune query URL: https://dune.com/queries/[QUERY_ID]",
)

# Staleness settings
st.markdown("### Staleness Settings")
st.caption(
    "Control how fresh the results should be. If results are older than the threshold, "
    "a new execution will be triggered (which uses credits)."
)

col1, col2 = st.columns(2)
with col1:
    enforce_freshness = st.checkbox(
        "Enforce freshness threshold",
        value=False,
        help="If enabled, re-execute query if results are too old (uses credits!)",
    )

with col2:
    if enforce_freshness:
        max_age_hours = st.number_input(
            "Max age (hours)",
            min_value=1,
            max_value=2191,  # ~3 months
            value=24,
            help="Re-execute if results are older than this",
        )
    else:
        max_age_hours = None

if enforce_freshness:
    st.warning(
        "⚠️ With freshness enforcement enabled, this may use execution credits "
        "if cached results are too old!"
    )

# Force refresh
force_refresh = st.checkbox(
    "Force refresh (bypass local cache)",
    value=False,
    help="Ignore locally cached results and fetch from Dune API.",
)

# Fetch button
if st.button("📥 Get Latest Results", width="stretch", type="primary"):
    if not query_id:
        st.error("Please enter a Query ID.")
        st.stop()

    # Show query info
    with st.expander("📝 Query Details", expanded=False):
        st.write(f"**Query ID:** {query_id}")
        st.write(f"**Query URL:** https://dune.com/queries/{query_id}")
        st.write(f"**Freshness Enforcement:** {'Yes' if enforce_freshness else 'No'}")
        if enforce_freshness:
            st.write(f"**Max Age:** {max_age_hours} hours")

    # Clear cache if force refresh
    if force_refresh:
        get_latest_results_cached.clear()
        st.toast("Local cache cleared!")

    # Fetch results
    api_key = st.session_state.get("dune_api_key", "")
    result_dict, error = get_latest_results_cached(query_id, max_age_hours, api_key)

    if error:
        st.error(f"❌ Failed to get results: {error}")

        # Common error hints
        if "not found" in error.lower():
            st.info(
                "💡 Make sure the Query ID exists and has been executed at least once."
            )
        elif "authentication" in error.lower() or "unauthorized" in error.lower():
            st.info("💡 Check that your API key is valid.")

        if st.button("🔄 Clear cache and retry"):
            get_latest_results_cached.clear()
            st.rerun()

    elif result_dict:
        st.success("✅ Results retrieved successfully!")

        # Show execution metadata
        with st.expander("🔍 Execution Metadata", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Execution ID:** `{result_dict.get('execution_id')}`")
                st.write(f"**State:** {result_dict.get('state')}")
            with col2:
                if result_dict.get("submitted_at"):
                    st.write(f"**Submitted:** {result_dict.get('submitted_at')}")
                if result_dict.get("execution_ended_at"):
                    st.write(f"**Completed:** {result_dict.get('execution_ended_at')}")

        # Convert to DataFrame
        rows = result_dict.get("rows", [])
        df = pd.DataFrame(rows) if rows else pd.DataFrame()

        if df.empty:
            st.info("Query has no results or has not been executed yet.")
        else:
            # Display results
            display_results(df, max_display_rows)

            # Download buttons
            display_download_buttons(df, f"query_{query_id}_latest")

            # Column info
            display_column_info(df)

import re
import streamlit as st
import pandas as pd
from io import StringIO
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
    page_title="Custom SQL - Dune",
    page_icon="✍️",
    layout="wide",
)

st.title("✍️ Custom SQL Execution")
st.markdown("""
Write and execute arbitrary SQL queries directly on Dune. Parameters like `{{blockchain}}` 
will be detected and input fields will be generated automatically.

⚠️ **Note:** This feature uses the `run_sql` API which requires a **Dune Plus subscription**.
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


def parse_parameters(sql: str) -> list[str]:
    """
    Extract {{parameter_name}} patterns from SQL query.
    Returns a list of unique parameter names in order of appearance.
    """
    pattern = r"\{\{(\w+)\}\}"
    matches = re.findall(pattern, sql)
    # Preserve order while removing duplicates
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
        # Escape the value to prevent SQL injection (basic quoting)
        escaped_value = value.replace("'", "''")  # Escape single quotes
        result = result.replace(f"{{{{{param_name}}}}}", escaped_value)
    return result


@st.cache_data(ttl=DEFAULT_CACHE_TTL, show_spinner="Executing query on Dune...")
def execute_sql_cached(
    final_sql: str, performance: str, api_key: str
) -> tuple[pd.DataFrame | None, str | None]:
    """
    Execute the SQL query on Dune and return results as DataFrame.
    Uses api_key as cache key dependency instead of client object.
    Returns (dataframe, error_message) tuple.
    """
    from dune_client.client import DuneClient

    try:
        client = DuneClient(api_key=api_key)
        results = client.run_sql(query_sql=final_sql, performance=performance)

        # Convert results to DataFrame
        rows = results.result.rows if results.result else []
        if not rows:
            return pd.DataFrame(), None

        df = pd.DataFrame(rows)
        return df, None

    except Exception as e:
        return None, str(e)


# Main content area
st.markdown("### Write Your Query")

# Example query for reference
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
        "Parameters like `{{blockchain}}` will be detected and input fields will be generated."
    )

# SQL Query input
sql_query = st.text_area(
    "SQL Query",
    height=200,
    placeholder="SELECT * FROM dex.trades WHERE blockchain = '{{blockchain}}' LIMIT 10",
    help="Use {{parameter_name}} syntax for dynamic parameters. Press Ctrl+Enter or click outside to update.",
)

# Parse parameters from the query
detected_params = parse_parameters(sql_query)

# Display detected parameters info
if detected_params:
    st.info(
        f"🔍 Detected parameters: {', '.join([f'`{{{{{p}}}}}`' for p in detected_params])}"
    )

# Configuration section
st.markdown("### Query Configuration")

# Dynamic parameter inputs
param_values = {}
if detected_params:
    st.markdown("#### Parameters")
    cols = st.columns(min(len(detected_params), 3))
    for i, param in enumerate(detected_params):
        col_idx = i % 3
        with cols[col_idx]:
            param_values[param] = st.text_input(
                f"{param}",
                key=f"custom_sql_param_{param}",
                placeholder=f"Enter value for {param}",
            )

# Execution settings
st.markdown("#### Execution Settings")
col1, col2 = st.columns(2)
with col1:
    performance = st.selectbox(
        "Performance Level",
        options=["medium", "large"],
        index=0,
        help="'medium' is faster and cheaper. 'large' for complex queries.",
        key="custom_sql_performance",
    )

with col2:
    force_refresh = st.checkbox(
        "Force refresh (bypass cache)",
        value=False,
        help="Ignore cached results and execute a fresh query.",
        key="custom_sql_force_refresh",
    )

# Execute button
submitted = st.button(
    "🚀 Execute Query", width="stretch", type="primary", key="custom_sql_submit"
)

# Handle form submission
if submitted:
    # Validation
    if not sql_query.strip():
        st.error("Please enter a SQL query.")
        st.stop()

    # Check all parameters have values
    missing_params = [p for p in detected_params if not param_values.get(p, "").strip()]
    if missing_params:
        st.error(f"Please provide values for: {', '.join(missing_params)}")
        st.stop()

    # Substitute parameters
    final_sql = substitute_parameters(sql_query, param_values)

    # Show the final query
    with st.expander("📝 Final SQL Query", expanded=False):
        st.code(final_sql, language="sql")

    # Clear cache if force refresh is selected
    if force_refresh:
        execute_sql_cached.clear()
        st.toast("Cache cleared!")

    # Execute the query
    api_key = st.session_state.get("dune_api_key", "")
    df, error = execute_sql_cached(final_sql, performance, api_key)

    if error:
        st.error(f"❌ Query execution failed: {error}")

        # Check for Plus subscription error
        if "plus" in error.lower() or "subscription" in error.lower():
            st.info(
                "💡 The `run_sql` API requires a Dune Plus subscription. "
                "Consider using the **Sync Query** page to execute existing queries instead."
            )

        # Offer to clear cache for this failed query
        if st.button("🔄 Clear cache and retry"):
            execute_sql_cached.clear()
            st.rerun()

    elif df is not None:
        st.success("✅ Query completed successfully!")

        if df.empty:
            st.info("Query returned no results.")
        else:
            # Display results using shared component
            display_results(df, max_display_rows)

            # Download buttons
            display_download_buttons(df, "custom_sql_results")

            # Column information
            display_column_info(df)


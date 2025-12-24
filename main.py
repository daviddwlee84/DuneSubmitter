import re
import streamlit as st
import pandas as pd
from io import StringIO
from shared_components import set_api_key_and_get_dune_client

# Configuration
MAX_DISPLAY_ROWS = 1000
DEFAULT_CACHE_TTL = 3600  # 1 hour


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
def execute_query_cached(
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


# Page configuration
st.set_page_config(
    page_title="Dune Query Executor",
    page_icon="🔮",
    layout="wide",
)

st.title("🔮 Dune Query Executor")

# Sidebar for API key
with st.sidebar:
    dune_client = set_api_key_and_get_dune_client()
    if dune_client:
        st.success("✓ Dune client initialized")
    else:
        st.info("Set your Dune API key to continue")
        st.stop()

    st.divider()
    st.markdown("### Settings")
    cache_ttl = st.number_input(
        "Cache TTL (seconds)",
        min_value=0,
        max_value=86400,
        value=DEFAULT_CACHE_TTL,
        help="How long to cache query results. Set to 0 to disable caching.",
    )
    max_display_rows = st.number_input(
        "Max display rows",
        min_value=100,
        max_value=100000,
        value=MAX_DISPLAY_ROWS,
        help="Maximum rows to display in the table (for performance).",
    )

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

# Configuration section (not in a form for dynamic updates)
st.markdown("### Query Configuration")

# Dynamic parameter inputs (outside form for immediate feedback)
param_values = {}
if detected_params:
    st.markdown("#### Parameters")
    cols = st.columns(min(len(detected_params), 3))
    for i, param in enumerate(detected_params):
        col_idx = i % 3
        with cols[col_idx]:
            param_values[param] = st.text_input(
                f"{param}",
                key=f"param_{param}",
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
    )

with col2:
    force_refresh = st.checkbox(
        "Force refresh (bypass cache)",
        value=False,
        help="Ignore cached results and execute a fresh query.",
    )

# Execute button
submitted = st.button("🚀 Execute Query", use_container_width=True, type="primary")

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
        execute_query_cached.clear()
        st.toast("Cache cleared!")

    # Execute the query
    api_key = st.session_state.get("dune_api_key", "")
    df, error = execute_query_cached(final_sql, performance, api_key)

    if error:
        st.error(f"❌ Query execution failed: {error}")

        # Offer to clear cache for this failed query
        if st.button("🔄 Clear cache and retry"):
            execute_query_cached.clear()
            st.rerun()
    elif df is not None:
        st.success("✅ Query completed successfully!")

        # Results statistics
        total_rows = len(df)
        total_cols = len(df.columns)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", f"{total_rows:,}")
        with col2:
            st.metric("Columns", total_cols)
        with col3:
            display_rows = min(total_rows, max_display_rows)
            st.metric("Displaying", f"{display_rows:,}")

        # Display DataFrame with protection for large results
        st.markdown("### Results")

        if total_rows > max_display_rows:
            st.warning(
                f"⚠️ Showing first {max_display_rows:,} of {total_rows:,} rows. "
                f"Download the full CSV to access all data."
            )
            display_df = df.head(max_display_rows)
        else:
            display_df = df

        # Interactive dataframe display
        st.dataframe(
            display_df,
            use_container_width=True,
            height=min(400, 35 * len(display_df) + 38),  # Dynamic height
        )

        # Download section
        st.markdown("### Download Results")
        col1, col2 = st.columns(2)

        with col1:
            # Full CSV download
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()

            st.download_button(
                label=f"📥 Download Full CSV ({total_rows:,} rows)",
                data=csv_data,
                file_name="dune_query_results.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col2:
            # JSON download option
            json_data = df.to_json(orient="records", indent=2)
            st.download_button(
                label=f"📥 Download JSON ({total_rows:,} rows)",
                data=json_data,
                file_name="dune_query_results.json",
                mime="application/json",
                use_container_width=True,
            )

        # Column information
        with st.expander("📊 Column Information"):
            col_info = pd.DataFrame(
                {
                    "Column": df.columns,
                    "Type": df.dtypes.astype(str),
                    "Non-Null Count": df.count().values,
                    "Sample Value": [
                        str(df[col].iloc[0]) if len(df) > 0 else "N/A"
                        for col in df.columns
                    ],
                }
            )
            st.dataframe(col_info, use_container_width=True, hide_index=True)

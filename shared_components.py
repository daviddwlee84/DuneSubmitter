import re
import streamlit as st
import pandas as pd
from io import StringIO
from dune_client.client import DuneClient
from dune_client.query import QueryBase
from dune_client.types import QueryParameter
import os
from typing import Optional, Any
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

# Configuration defaults
MAX_DISPLAY_ROWS = 1000
DEFAULT_CACHE_TTL = 3600  # 1 hour


@st.cache_resource
def get_dune_client(api_key: str) -> DuneClient:
    """Get or create a cached DuneClient instance."""
    return DuneClient(api_key=api_key)


def set_api_key_and_get_dune_client() -> Optional[DuneClient]:
    """
    Sidebar component for API key input and client initialization.
    Returns DuneClient if API key is set, None otherwise.
    """
    # Initialize session state with env var if not set
    if "dune_api_key" not in st.session_state:
        st.session_state["dune_api_key"] = os.getenv("DUNE_API_KEY", "")

    api_key = st.text_input(
        "Dune API key",
        type="password",
        value=st.session_state.get("dune_api_key", os.getenv("DUNE_API_KEY")),
        help="https://dune.com/apis?tab=keys",
    )
    st.session_state["dune_api_key"] = api_key
    if not api_key:
        return None
    return get_dune_client(api_key)


def parse_parameters_from_sql(sql: str) -> list[str]:
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


def create_query_parameter_widgets(
    detected_params: list[str],
    key_prefix: str = "param",
) -> dict[str, str]:
    """
    Create input widgets for detected parameters.
    Returns a dictionary of parameter name -> value.
    """
    param_values = {}
    if detected_params:
        st.markdown("#### Parameters")
        cols = st.columns(min(len(detected_params), 3))
        for i, param in enumerate(detected_params):
            col_idx = i % 3
            with cols[col_idx]:
                param_values[param] = st.text_input(
                    f"{param}",
                    key=f"{key_prefix}_{param}",
                    placeholder=f"Enter value for {param}",
                )
    return param_values


def build_query_parameters(param_values: dict[str, str]) -> list[QueryParameter]:
    """
    Convert parameter values dict to list of QueryParameter objects.
    All parameters are treated as text type by default.
    """
    return [
        QueryParameter.text_type(name=name, value=value)
        for name, value in param_values.items()
        if value.strip()  # Only include non-empty values
    ]


def display_results(
    df: pd.DataFrame,
    max_display_rows: int = MAX_DISPLAY_ROWS,
) -> None:
    """
    Display query results as a DataFrame with protection for large results.
    """
    total_rows = len(df)
    total_cols = len(df.columns)

    # Results statistics
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


def display_download_buttons(
    df: pd.DataFrame, filename_prefix: str = "dune_results"
) -> None:
    """
    Display download buttons for CSV and JSON formats.
    """
    total_rows = len(df)
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
            file_name=f"{filename_prefix}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        # JSON download option
        json_data = df.to_json(orient="records", indent=2)
        st.download_button(
            label=f"📥 Download JSON ({total_rows:,} rows)",
            data=json_data,
            file_name=f"{filename_prefix}.json",
            mime="application/json",
            use_container_width=True,
        )


def display_column_info(df: pd.DataFrame) -> None:
    """
    Display column information in an expander.
    """
    with st.expander("📊 Column Information"):
        col_info = pd.DataFrame(
            {
                "Column": df.columns,
                "Type": df.dtypes.astype(str),
                "Non-Null Count": df.count().values,
                "Sample Value": [
                    str(df[col].iloc[0]) if len(df) > 0 else "N/A" for col in df.columns
                ],
            }
        )
        st.dataframe(col_info, use_container_width=True, hide_index=True)


def results_to_dataframe(results: Any) -> pd.DataFrame:
    """
    Convert Dune ResultsResponse to pandas DataFrame.
    """
    rows = results.result.rows if results.result else []
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def display_execution_metadata(results: Any) -> None:
    """
    Display execution metadata (execution ID, state, times, etc.)
    """
    with st.expander("🔍 Execution Metadata", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Execution ID:** `{results.execution_id}`")
            st.write(f"**State:** {results.state.value if results.state else 'N/A'}")
        with col2:
            if results.times:
                if results.times.submitted_at:
                    st.write(f"**Submitted:** {results.times.submitted_at}")
                if results.times.execution_started_at:
                    st.write(f"**Started:** {results.times.execution_started_at}")
                if results.times.execution_ended_at:
                    st.write(f"**Ended:** {results.times.execution_ended_at}")


def render_sidebar_settings(
    default_cache_ttl: int = DEFAULT_CACHE_TTL,
    default_max_rows: int = MAX_DISPLAY_ROWS,
) -> tuple[int, int]:
    """
    Render common sidebar settings.
    Returns (cache_ttl, max_display_rows).
    """
    st.divider()
    st.markdown("### Settings")
    cache_ttl = st.number_input(
        "Cache TTL (seconds)",
        min_value=0,
        max_value=86400,
        value=default_cache_ttl,
        help="How long to cache query results. Set to 0 to disable caching.",
    )
    max_display_rows = st.number_input(
        "Max display rows",
        min_value=100,
        max_value=100000,
        value=default_max_rows,
        help="Maximum rows to display in the table (for performance).",
    )
    return cache_ttl, max_display_rows

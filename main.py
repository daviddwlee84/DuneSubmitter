import streamlit as st
from shared_components import set_api_key_and_get_dune_client

# Page configuration
st.set_page_config(
    page_title="Dune Query Tool",
    page_icon="🔮",
    layout="wide",
)

st.title("🔮 Dune Query Tool")

# Sidebar for API key
with st.sidebar:
    dune_client = set_api_key_and_get_dune_client()
    if dune_client:
        st.success("✓ Dune client initialized")
    else:
        st.info("Enter your Dune API key to continue")

# Main content
st.markdown(
    """
Welcome to the **Dune Query Tool** - a Streamlit-based interface for interacting with 
[Dune Analytics](https://dune.com/) through their official Python client.

## Features

This tool provides multiple ways to work with Dune queries:
"""
)

# Feature cards
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
    ### 🔍 Sync Query
    Execute existing Dune queries by their Query ID. 
    
    - Run queries synchronously
    - Pass custom parameters
    - Get results immediately
    - Uses execution credits
    
    **Best for:** Running queries and waiting for results
    """
    )

with col2:
    st.markdown(
        """
    ### ⏳ Async Query
    Start query execution and poll for results.
    
    - Non-blocking execution
    - Monitor execution status
    - Cancel running queries
    - Efficient for long queries
    
    **Best for:** Long-running queries or batch processing
    """
    )

with col3:
    st.markdown(
        """
    ### 📊 Latest Results
    Get the most recent cached results without re-executing.
    
    - No execution credits used
    - Fast retrieval
    - Configurable staleness threshold
    - Great for frequently updated queries
    
    **Best for:** Reading cached data without using credits
    """
    )

st.divider()

st.markdown(
    """
## Getting Started

1. **Get an API Key**: Visit [Dune API Keys](https://dune.com/apis?tab=keys) to get your API key
2. **Enter your API key** in the sidebar
3. **Navigate** to one of the pages using the sidebar navigation
4. **Find a Query ID**: Copy the ID from any Dune query URL (e.g., `https://dune.com/queries/1234567`)

## API Usage Notes

| Feature | Credits | Subscription |
|---------|---------|--------------|
| Sync Query (`run_query`) | Uses credits | Free tier available |
| Async Query (`execute_query`) | Uses credits | Free tier available |
| Latest Results (`get_latest_result`) | **No credits** | Free tier available |
| Custom SQL (`run_sql`) | Uses credits | **Plus required** |
| Create/Update Query | N/A | **Plus required** |

## Resources

- [Dune Analytics](https://dune.com/)
- [Dune API Documentation](https://docs.dune.com/)
- [dune-client Python Package](https://github.com/duneanalytics/dune-client)
"""
)

# Display version info
st.divider()
col1, col2 = st.columns(2)
with col1:
    st.caption("Built with Streamlit + dune-client")
with col2:
    try:
        import dune_client

        st.caption(f"dune-client version: {dune_client.__version__}")
    except (ImportError, AttributeError):
        st.caption("dune-client installed")

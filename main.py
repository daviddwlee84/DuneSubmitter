import streamlit as st
from shared_components import set_api_key_and_get_dune_client

st.title("Dune Submitter")

with st.sidebar:
    dune_client = set_api_key_and_get_dune_client()
    if dune_client:
        st.success("Dune client initialized")
    else:
        st.info("Set your Dune API key to continue")
        st.stop()

import streamlit as st
from dune_client.client import DuneClient
import os
from typing import Optional
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())


@st.cache_resource
def get_dune_client(api_key: str):
    return DuneClient(api_key=api_key)


def set_api_key_and_get_dune_client() -> Optional[DuneClient]:
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

import os

import streamlit as st
import streamlit_antd_components as sac

from layout import GeoApp, page_config

script_dir = os.path.dirname(__file__)
sitelist_mcom = os.path.join(script_dir, "test_geocell.csv")
sitelist_driveless = os.path.join(script_dir, "test_driveless.csv")


def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None


def run_app():
    page_config()
    tab_idx = sac.tabs(
        items=[
            sac.TabsItem("MR, MDT, Driveless", icon="globe-asia-australia"),
            sac.TabsItem("Code", icon="journal-code"),
        ],
        align="center",
        return_index=True,
        color="cyan",
        use_container_width=True,
    )

    if tab_idx == 0:
        app = GeoApp(sitelist_mcom, sitelist_driveless)
        app.run_geo_app()
    elif tab_idx == 1:
        st.write("A")

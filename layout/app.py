import os

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac

from layout import GeoApp, page_config, print_code, set_page_width, styling

script_dir = os.path.dirname(__file__)
sitelist_mcom = os.path.join(script_dir, "test_geocell.csv")
sitelist_driveless = os.path.join(script_dir, "test_driveless.csv")
mcom = pd.read_csv(sitelist_mcom)
dt = pd.read_csv(sitelist_driveless)


def init_session_state():
    if "selected_functionality" not in st.session_state:
        st.session_state["selected_functionality"] = None


def run_app():
    page_config()
    tab_idx = sac.tabs(
        items=[
            sac.TabsItem("Geo Plotting", icon="globe-asia-australia"),
            sac.TabsItem("Code", icon="journal-code"),
        ],
        align="center",
        return_index=True,
        color="cyan",
        use_container_width=True,
    )

    if tab_idx == 0:
        set_page_width(1300)
        app = GeoApp(sitelist_mcom, sitelist_driveless)
        app.run_geo_app()
    elif tab_idx == 1:
        st.markdown(*styling("Cells Data", tag="h6", font_size=18, text_align="left"))
        st.write(mcom)
        st.markdown(
            *styling("Geographic Data", tag="h6", font_size=18, text_align="left")
        )
        st.write(dt)
        st.markdown(*styling("Full Code", tag="h6", font_size=18, text_align="left"))
        print_code()

import streamlit as st


def page_config():
    st.set_page_config(
        page_title="Geocell Visualization",
        layout="wide",
        page_icon="☢️",
    )
    st.markdown(
        """
        <style>
        [data-testid="collapsedControl"] {
            display: none;
        }
        #MainMenu, header, footer {visibility: hidden;}
        .appview-container .main .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            padding-bottom: 1rem;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def set_page_width(width: int):
    """Set the page width for a Streamlit app with custom CSS.

    Args:
    ----
        width (int): The maximum width in pixels for the content area.
    """
    style = f"""
    <style>
    .main .block-container {{
        max-width: {width}px;
        padding-left: 1rem;
        padding-right: 1rem;
    }}
    </style>
    """
    st.markdown(style, unsafe_allow_html=True)

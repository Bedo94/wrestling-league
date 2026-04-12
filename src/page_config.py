import streamlit as st

APP_TITLE = "Wrestling League"
APP_ICON = "🤼"


def apply_page_config(page_title: str | None = None) -> None:
    st.set_page_config(
        page_title=page_title or APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
    )

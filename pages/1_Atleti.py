from src.page_config import apply_page_config
from src.db_runtime import bootstrap_database_from_state
from src.athletes_page_ui import render_athletes_page

apply_page_config("Atleti | Wrestling League")

bootstrap_database_from_state()

render_athletes_page()

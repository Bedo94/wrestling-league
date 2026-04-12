from src.page_config import apply_page_config
from src.database_page_ui import render_database_page
from src.db_runtime import bootstrap_database_from_state

apply_page_config("Database | Wrestling League")

bootstrap_database_from_state()
render_database_page()

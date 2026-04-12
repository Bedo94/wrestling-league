from src.page_config import apply_page_config
from src.admin_formulas_page_ui import render_admin_formulas_page
from src.db_runtime import bootstrap_database_from_state

apply_page_config("Admin Formule | Wrestling League")

bootstrap_database_from_state()
render_admin_formulas_page()

from .dashboard import dashboard as ds_
from .login_control import login_view as liv_, logout_view as lov_
from .my_sims import get_sims as gs_, get_sims_data as gsd_, assign_sims as as_,  update_sim_state as uss_
from .details import order_details as od_, sim_details as sd_, update_label as usl_, send_sms as ss_, user_details as ud_, update_user_account as uua_, update_user as uu_, api_get_sim_location as agsl_
from .refresh import refresh_sim as rsim_, refresh_monthly as rm_, refresh_orders as ro_, refresh_status as rsta_, refresh_sms_quota as rsq_, refresh_data_quota as rdq_, refresh_sms as rsms_
from .users import get_users as gu_, create_distribuidor as cd_, create_revendedor as cr_, create_cliente as cc_
from .configuration import config as co_, update_limits as gl_
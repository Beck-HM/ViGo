from .mathlib import register as register_math
from .iolib import register as register_io
from .cryptolib import register as register_crypto
from .netlib import register as register_net
from .datalib import register as register_data
from .syslib import register as register_sys
from .dblib import register as register_db
from .loglib import register as register_log
from .colorlib import register as register_color
from .inilib import register as register_ini
from .guilib import register as register_gui
from .ailib import register as register_ai
from .raglib import register as register_rag
from .imagelib import register as register_image
from .promptlib import register as register_prompt
from .emaillib import register as register_email
from .workflowlib import register as register_workflow
from .i18nlib import register as register_i18n
from .chartlib import register as register_chart
from .kglib import register as register_kg
from .typelib import register as register_type
from .modulelib import register as register_module
from .cronlib import register as register_cron
from .wslib import register as register_ws
from .trainlib import register as register_train


def register_all(env):
    register_math(env)
    register_io(env)
    register_crypto(env)
    register_net(env)
    register_data(env)
    register_sys(env)
    register_db(env)
    register_log(env)
    register_color(env)
    register_ini(env)
    register_gui(env)
    register_ai(env)
    register_rag(env)
    register_image(env)
    register_prompt(env)
    register_email(env)
    register_workflow(env)
    register_i18n(env)
    register_chart(env)
    register_kg(env)
    register_type(env)
    register_module(env)
    register_cron(env)
    register_ws(env)
    register_train(env)
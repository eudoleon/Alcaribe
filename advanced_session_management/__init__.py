from . import controllers
from . import models
from . import wizard


from odoo.api import Environment, SUPERUSER_ID
import odoo
from odoo import http
import re
import os
from datetime import datetime
from odoo.http import request
import json
import requests
from user_agents import parse

def getting_ip(row):
    """This function calls the api and return the response"""
    url = f"https://freegeoip.app/json/{row}"       # getting records from getting ip address
    headers = {
        'accept': "application/json",
        'content-type': "application/json"
        }
    response = requests.request("GET", url, headers=headers)
    respond = json.loads(response.text)
    return respond

def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    user_ids = []
    for user in env['res.users'].search([]):
        if user.has_group('base.group_user'):
            user_ids.append(user.id)
    env.ref('advanced_session_management.group_login_log_user_ah').users = [(6,0,user_ids)]
    session_store = http.root.session_store
    for ses in os.listdir(odoo.tools.config.session_dir):
        try:
            session = session_store.get(os.listdir(odoo.tools.config.session_dir + '/' + ses)[0])
            if session.db and session.uid:
                session_store.delete(session)
        except:
            pass
#     http.root.session_store.list()
#     for fname in os.listdir(odoo.tools.config.session_dir):
# #        print('\n\n fname',fname)
#         path = os.path.join(odoo.tools.config.session_dir, fname)
# #        print('\n\n path',path)
#         name = re.split('_|\\.', fname)
# #        print('\n\n name',name)
#         session_store = http.root.session_store
#         get_session = session_store.get(name[0])
#         if get_session.db:
#             if get_session.uid:
#                 os.unlink(path)
#                 get_session.logout(keep_db=True)

def uninstall_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].search([('key','=','advanced_session_management.send_mail')]).unlink()

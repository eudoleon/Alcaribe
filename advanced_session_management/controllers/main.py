from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import requests
import json

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

class Controller(http.Controller):

    @http.route('/post/action_data', type='json', auth='public')
    def _get_action_data(self, data='',api=''):
        try:
            # original_url = data
            activity_log_obj = request.env['activity.log'].sudo()
            menu_obj = request.env['ir.ui.menu'].sudo()
            config_parameter_obj = request.env['ir.config_parameter'].sudo()
            login_log = request.env['login.log'].sudo().search([('session_id','=',request.session.sid)],limit=1)
            if not login_log.ip and api:
                login_log.ip = api
                try:
                    
                    value = getting_ip(api)
                    country = value['country_name'] or ''
                    city = value['city'] or ''
                    state = value['region_name'] or ''
                except:
                    country = ''
                    state = ''
                    city = ''
                login_log.sudo().write({
                    'ip':api,
                    'country':country,
                    'loc_state':state,
                    'city':city
                })
            url = config_parameter_obj.get_param('web.base.url')
            active_timeout = config_parameter_obj.get_param('advanced_session_management.session_timeout_active') or 'none'
            if active_timeout == 'active':
                interval_number = int(config_parameter_obj.get_param('advanced_session_management.session_timeout_interval_number'))
                if interval_number > 0:
                    login_log.timeout_date = datetime.now() + timedelta(hours=interval_number)
            
            full_url = url + '/web#'
            for record in data:
                full_url +=  record + '=' + str(data[record]) + '&'
            
            full_url = full_url[:len(full_url)-1]

            
            if 'action' in data.keys() and data['action'] == 'menu':
                activity_log_obj.create({
                    'name':"Open Home Screen",
                    'action':'read',
                    'login_log_id':login_log.id,
                    'user_id':login_log.user_id.id,
                    'url':full_url,
                    'model':'n/a',
                    'view':'n/a',
                })
            else:
                name = ''
                if data.get('id'):
                    record = request.env[data.get('model')].search([('id','=',data.get('id'))],limit=1)
                    if record:
                        try:
                            if record.name:
                                name = record.name
                            else:
                                name = record.display_name
                        except:
                            name = record.display_name
                if not name:
                    menu = menu_obj.search([('id','=',data.get('menu_id'))],limit=1)
                    if menu:
                        name = menu.name
                if name:
                    activity_log_obj.create({
                        'name':name,
                        'model':data.get('model') or 'n/a',
                        'res_id':data.get('id') or 'n/a',
                        'action':'read',
                        'view':data.get('view_type') or 'n/a',
                        'login_log_id':login_log.id,
                        'user_id':login_log.user_id.id,
                        'url':full_url,
                        'view':'n/a',
                    })
        except:
            pass
        
        return 

    @http.route('/get/ip_params', type='json', auth='public')
    def _get_ip_params(self):
        vals = {}
        config_parameter_obj = request.env['ir.config_parameter'].sudo()
        ip_url = config_parameter_obj.get_param('advanced_session_management.ip_url') or 'none'
        ip_key = config_parameter_obj.get_param('advanced_session_management.ip_key') or 'none'
        vals['ip_url'] = ip_url
        vals['ip_key'] = ip_key
        return vals

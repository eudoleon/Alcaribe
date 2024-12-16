from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.session import Session
from odoo.addons.web.controllers.home import Home
from datetime import datetime, timedelta
import json
import requests
from user_agents import parse
from odoo.addons.web.controllers.utils import ensure_db
import logging
_logger = logging.getLogger(__name__)
# from odoo.http import Session, get_default_session
from odoo.addons.base_sparse_field.models.fields import monkey_patch
from odoo.addons.auth_oauth.controllers.main import OAuthController, fragment_to_query_string


# @monkey_patch(Session)
# def logout(self, keep_db=False):
#     # response = super(erp_session, self).logout(keep_db=keep_db)
#     if 'login.log' in request.env:
#         login_log = request.env['login.log'].search([('session_id','=',self.sid)])
#         if login_log:
#             login_log.sudo().write({'state':'close','logout_date':datetime.now()})
#             login_log._cr.commit()
#     # for k in list(self):
#     #     if not (keep_db and k == 'db') and k != 'debug':
#     #         del self[k]
#     # self._default_values()
#     # self.rotate = True
#     db = self.db if keep_db else get_default_session()['db']  # None
#     debug = self.debug
#     self.clear()
#     self.update(get_default_session(), db=db, debug=debug)
#     self.context['lang'] = request.default_lang() if request else DEFAULT_LANG
#     self.should_rotate = True

class user_login(Home):

    @http.route()
    def web_login(self, redirect=None, **kw):
        ensure_db()
        response = super(user_login, self).web_login(redirect, **kw)
        if request.params['login_success']:
            
            # try:
            #     ip = ''
            #     print(request.httprequest.environ)
            #     if 'HTTP_X_REAL_IP' in request.httprequest.environ.keys():
            #         ip = request.httprequest.environ['HTTP_X_REAL_IP']
            #     value = getting_ip(ip)
            #     _logger.info('\nIP : %s\n' % (ip))
            #     # value = json.loads(loc_res.text)
            #     country = value['country_name'] or ''
            #     city = value['city'] or ''
            #     state = value['region_name'] or ''
            # except:
            #     country = ''
            #     state = ''
            #     city = ''
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if not request.env['res.users'].sudo().browse(uid).has_group('base.group_portal'):
                user_agent = parse(request.httprequest.environ.get('HTTP_USER_AGENT', ''))
                device = user_agent.device.family
                if user_agent.device.family == 'Other':
                    if user_agent.is_pc:
                        device = 'PC'
                    elif user_agent.is_mobile:
                        device = 'Mobile'
                    elif user_agent.is_tablet:
                        device = 'Tablet'
                    
                login_log = request.env['login.log'].sudo().create({
                    'login_date':datetime.now(),
                    'user_id':uid,
                    'user_agent':user_agent,
                    'state':'active',
                    # 'ip':ip,
                    'browser':user_agent.browser.family,
                    # 'session_id':request.session.sid,
                    'device':device,
                    'os':user_agent.os.family,
                    # 'country':country,
                    # 'loc_state':state,
                    # 'city':city
                })
                config_parameter_obj = request.env['ir.config_parameter'].sudo()
                active_timeout = config_parameter_obj.get_param('advanced_session_management.session_timeout_active') or 'none'
                if active_timeout != 'none':
                    interval_number = int(config_parameter_obj.get_param('advanced_session_management.session_timeout_interval_number')) or 48
                    if interval_number:
                        login_log.timeout_date = datetime.now() + timedelta(hours=interval_number)
        return response

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        response = super(user_login, self).web_client(s_action, **kw)
        login_log = request.env['login.log'].sudo().search([('user_id','=',request.uid),('session_id','=',False)], order='id desc',limit=1)
        if login_log:
            login_log.session_id = request.session.sid
        return response

class user_logout(Session):

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        uid = request.session['uid']
        login_log = request.env['login.log'].sudo().search([('user_id', '=', uid),('session_id', '=',request.session.sid)],limit=1)
        login_log.write({
            'state':'close',
            'logout_date':datetime.now(),
        })
        
        return super(user_logout, self).logout(redirect)

class OAuthControllerExt(OAuthController):

    @http.route('/auth_oauth/signin', type='http', auth='none')
    @fragment_to_query_string
    def signin(self, **kw):
        response = super(OAuthControllerExt, self).signin(**kw)
        if response.status_code == 303:
            # try:
            #     ip = ''
            #     if 'HTTP_X_REAL_IP' in request.httprequest.environ.keys():
            #         ip = request.httprequest.environ['HTTP_X_REAL_IP']
            #     value = getting_ip(ip)
            #     _logger.info('\nIP : %s\n' % (ip))
            #     # value = json.loads(loc_res.text)
            #     country = value['country_name'] or ''
            #     city = value['city'] or ''
            #     state = value['region_name'] or ''
            # except:
            #     country = ''
            #     state = ''
            #     city = ''

            if not request.env.user.has_group('base.group_portal'):
                user_agent = parse(request.httprequest.environ.get('HTTP_USER_AGENT', ''))
                device = user_agent.device.family
                if user_agent.device.family == 'Other':
                    if user_agent.is_pc:
                        device = 'PC'
                    elif user_agent.is_mobile:
                        device = 'Mobile'
                    elif user_agent.is_tablet:
                        device = 'Tablet'
                    
                login_log = request.env['login.log'].sudo().create({
                    'login_date':datetime.now(),
                    'user_id':request.env.user.id,
                    'user_agent':user_agent,
                    'state':'active',
                    # 'ip':ip,
                    'browser':user_agent.browser.family,
                    # 'session_id':request.session.sid,
                    'device':device,
                    'os':user_agent.os.family,
                    # 'country':country,
                    # 'loc_state':state,
                    # 'city':city
                })
                config_parameter_obj = request.env['ir.config_parameter'].sudo()
                active_timeout = config_parameter_obj.get_param('advanced_session_management.session_timeout_active') or 'none'
                if active_timeout != 'none':
                    interval_number = int(request.env['ir.config_parameter'].sudo().get_param('advanced_session_management.session_timeout_interval_number')) or 48
                    if interval_number:
                        login_log.timeout_date = datetime.now() + timedelta(hours=interval_number)
        return response

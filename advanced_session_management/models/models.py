from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.http import request

from . import exclude_models

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def write(self, vals):
        try:
            moduel_state = self.env['ir.module.module'].sudo().search([('name','=','advanced_session_management')]).state
            if self._name not in exclude_models.ignore_model and moduel_state == 'installed':
                config_parameter_obj = self.env['ir.config_parameter'].sudo()
                field_obj = self.env['ir.model.fields'].sudo()
                for record in self:
                
                    activity_log_obj = self.env['activity.log'].sudo()

                    login_log = record.env['login.log'].sudo().search([('session_id','=',request.session.sid)],limit=1)
                    if login_log and not self._transient:
                        disable = str(config_parameter_obj.get_param('disable_log'))
                        if disable == 'False':
                            value = ''
                            view_changes = []
                            for val in vals:
                                if str(record[val]) != str(vals[val]):
                                    field_name = field_obj.search([('name','=',val),('model','=',record._name)],limit=1)
                                    
                                    if field_name.ttype not in ['binary','many2many','one2many','many2one','html','text']:
                                        if not record[val] and vals[val]:
                                            value = value + """ New value <b>%s</b> was added for the field <b>%s</b>. <br/>""" % (vals[val],field_name.field_description)
                                        if not vals[val] and record[val]:
                                            value = value + """ The value is set to blank from <b>%s</b> for the <b>%s</b>. <br/>""" % (record[val],field_name.field_description)
                                        if vals[val] and record[val]:
                                            value = value + """ The value of the <b>%s</b> was updated from <b>%s</b> to <b>%s</b>. <br/>""" % (field_name.field_description,record[val],vals[val])
                                    elif field_name.ttype in ['html','binary','text']:
                                        value = value + """ <b>%s</b> is Changed. <br/>""" % (field_name.field_description)
                                        view_changes.append((0,0,{
                                            'name':field_name.field_description,
                                            'old':record[val],
                                            'new':vals[val],
                                        }))
                                    elif field_name.ttype in ['many2one']:
                                        if record[val].id != vals[val]:
                                            obj = record.env[field_name.relation].sudo()
                                            if not record[val] and vals[val]:
                                                new_value = obj.browse(vals[val]).display_name
                                                value = value + """ New value <b>%s</b> was added for the field <b>%s</b>. <br/>""" % (new_value,field_name.field_description)
                                            if not vals[val] and record[val]:
                                                old_value = obj.browse(record[val].id).display_name
                                                value = value + """ The value is set to blank from <b>%s</b> for the <b>%s</b>. <br/>""" % (old_value,field_name.field_description)
                                            if vals[val] and record[val]:
                                                old_value = obj.browse(record[val].id).display_name
                                                new_value = obj.browse(vals[val]).display_name
                                                value = value + """ The value of the <b>%s</b> was updated from <b>%s</b> to <b>%s</b>. <br/>""" % (field_name.field_description,old_value,new_value)

                                    elif field_name.ttype in ['many2many']:
                                        obj = record.env[field_name.relation].sudo()
                                        # if record._name != 'res.users' and field_name.name in ['groups_id','']:
                                        if len(vals[val][0]) == 3:
                                            
                                            old_value = ''
                                            new_value = ''
                                            if not record[val] and vals[val][0][2]:
                                                for new_id in vals[val][0][2]:
                                                    new_value = new_value + obj.browse(new_id).display_name + '|'
                                                value = value + """ New value <b>%s</b> was added for the field <b>%s</b>. <br/>""" % (new_value,field_name.field_description)
                                            elif not vals[val][0][2] and record[val]:
                                                for new_id in record[val].ids:
                                                    old_value = old_value + obj.browse(new_id).display_name + '|'
                                                value = value + """ The value is set to blank from <b>%s</b> for the <b>%s</b>. <br/>""" % (old_value,field_name.field_description)
                                            elif vals[val][0][2] and record[val]:
                                                for new_id in vals[val][0][2]:
                                                    new_value = new_value + obj.browse(new_id).display_name + '|'
                                                for new_id in record[val].ids:
                                                    old_value = old_value + obj.browse(new_id).display_name + '|'
                                                value = value + """ The value of the <b>%s</b> was updated from <b>%s</b> to <b>%s</b>. <br/>""" % (field_name.field_description,old_value,new_value)
                                        elif len(vals[val][0]) == 2:
                                            if not request.session.temp:
                                                for m2m_rec in vals[val]:
                                                    browse_rec = obj.browse(m2m_rec[1])
                                                    categ_name = ''
                                                    if record._name == 'res.users' and field_name.name == 'groups_id':
                                                        categ_name = browse_rec.category_id.name + '/'
                                                    if m2m_rec[1] in record[val].ids:
                                                        value = value + """ <b>%s</b> is removed in <b>%s</b>. <br/>""" % (categ_name+browse_rec.name,field_name.field_description)
                                                    else:
                                                        value = value + """ <b>%s</b> is added in <b>%s</b>. <br/>""" % (categ_name+browse_rec.name,field_name.field_description)
                                                request.session.temp = True
                                            else:
                                                request.session.temp = False
                            if value:
                                activity_log_obj.create({
                                    'name':record.display_name,
                                    'model':record._name,
                                    'res_id':str(record.id),
                                    'action':'edit',
                                    'login_log_id':login_log.id,
                                    'user_id':login_log.user_id.id,
                                    # 'edit_value_id':edit_value.id,
                                    'value':value,
                                    'view':'n/a',
                                    'edit_value_ids':view_changes,
                                })
        except:
            pass
        return super().write(vals)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        res = super().create(vals_list)
        moduel_state = self.env['ir.module.module'].sudo().search([('name','=','advanced_session_management')]).state
        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        
        for record in res:
            if record._name not in exclude_models.ignore_model and moduel_state == 'installed':
                activity_log_obj = self.env['activity.log'].sudo()
                login_log = self.env['login.log'].sudo().search([('session_id','=',request.session.sid)],limit=1)
                if login_log and not self._transient:
                    disable = str(config_parameter_obj.get_param('disable_log'))
                    if disable == 'False':
                        
                        activity_log_obj.create({
                            'name':record.display_name or record.name or '',
                            'model':record._name,
                            'res_id':str(record.id),
                            'action':'create',
                            'login_log_id':login_log.id,
                            'user_id':login_log.user_id.id,
                            'view':'n/a',
                        })
        return res
    
    def unlink(self):
        moduel_state = self.env['ir.module.module'].sudo().search([('name','=','advanced_session_management')]).state
        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        
        for record in self:
            try:
                if record._name not in exclude_models.ignore_model and moduel_state == 'installed':
                    activity_log_obj = self.env['activity.log'].sudo()
                    login_log = record.env['login.log'].sudo().search([('session_id','=',request.session.sid)],limit=1)
                    if login_log and not self._transient:
                        disable = str(config_parameter_obj.get_param('disable_log'))
                        if disable == 'False':
                            activity_log_obj.create({
                                'name':record.display_name,
                                'model':record._name,
                                'res_id':str(record.id),
                                'action':'delete',
                                'login_log_id':login_log.id,
                                'user_id':login_log.user_id.id,
                                'view':'n/a',
                            })
            except:
                pass
        return super().unlink()

class ir_module_module(models.Model):
    _inherit = 'ir.module.module'


    def _button_immediate_function(self, function):
        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        value = config_parameter_obj.search([('key','=','disable_log')],limit=1)
        
        if value:
            value.value = 'True'
        else:
            config_parameter_obj.create({'key':'disable_log','value':'True'})
        res = super(ir_module_module, self)._button_immediate_function(function)
        for record in self:
            if record.name != 'advanced_session_management':
                login_log = record.env['login.log'].sudo().search([('session_id','=',request.session.sid)],limit=1)
                if login_log:
                    value = ''
                    if function.__name__ == 'button_install':
                        value = ' installed'
                    if function.__name__ == 'button_uninstall':
                        value = ' uninstalled'
                    if function.__name__ == 'button_upgrade':
                        value = ' upgrade'
                    if function.__name__ == 'install_or_upgrade':
                        value = ' install or upgrade'
                    
                    record.env['activity.log'].sudo().create({
                        'name':record.display_name,
                        'model':record._name,
                        'res_id':str(record.id),
                        'action':'edit',
                        'login_log_id':login_log.id,
                        'user_id':login_log.user_id.id,
                        # 'edit_value_id':edit_value.id,
                        'view':'n/a',
                        'value':""" <b>%s</b> app is %s. <br/>""" % (record.display_name, value)
                    })
            config_parameter_obj.search([('key','=','disable_log')],limit=1).unlink()
        return res
    

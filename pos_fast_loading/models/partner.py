# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models
from odoo.exceptions import Warning, ValidationError
import json
import base64
import logging
from odoo.http import request
_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")
from datetime import datetime



class ResPartner(models.Model):
    _inherit = "res.partner"


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        try:
            _logger.info("############# customer search read start#############")
            mongo_server_rec = self.env['mongo.server.config'].search([('active_record','=',True)],limit=1)
            is_indexed_updated = self._context.get('is_indexed_updated')
            if (self._context.get('sync_from_mongo')) and mongo_server_rec:
                request.session['partner_loaded_details'] = ''
                load_pos_data_type = mongo_server_rec.load_pos_data_from
                if is_indexed_updated and is_indexed_updated[0] and not is_indexed_updated[0].get('time') and mongo_server_rec.is_ordinary_loading  and mongo_server_rec.is_updated:
                    return []
                if mongo_server_rec.cache_last_update_time and mongo_server_rec.is_pos_data_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    if mongo_server_rec.pos_live_sync == 'reload' and not mongo_server_rec.is_ordinary_loading:
                        self.env['common.cache.notification'].get_common_changes()
                    if load_pos_data_type == 'mongo':
                        if mongo_server_rec.is_updated and is_indexed_updated and is_indexed_updated[0] and is_indexed_updated[0].get("time") and is_indexed_updated[0].get("time") >= mongo_server_rec.cache_last_update_time.strftime("%Y-%m-%d %H:%M:%S"):
                            return []
                        else:
                            client = mongo_server_rec.get_client()
                            info = client.server_info()
                            data = self.env['mongo.server.config'].get_customer_data_from_mongo(fields=fields,client=client)
                            if data:
                                return data
                    else:
                        # ****************decode data************************
                        if mongo_server_rec.is_updated and is_indexed_updated and is_indexed_updated[0] and is_indexed_updated[0].get("time") and  is_indexed_updated[0].get("time") >= mongo_server_rec.cache_last_update_time.strftime("%Y-%m-%d %H:%M:%S"):
                            return []
                        else:
                            if mongo_server_rec.pos_live_sync == 'reload':
                                self.env['common.cache.notification'].get_common_changes()
                            binary_data_rec = mongo_server_rec.collection_data.filtered(lambda x: x.model_name == 'res.partner')
                            if binary_data_rec:
                                if not request.session['partner_loaded_details']:
                                    request.session['partner_loaded_details'] = str(binary_data_rec[0].id)+','
                                json_data = json.loads(base64.decodebytes(binary_data_rec[0].server_data_cache).decode('utf-8'))
                                data = json_data.values()
                                return list(data)
                else:
                    mongo_server_rec.is_ordinary_loading = True
                    return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
                    # *******************************************************
        except Exception as e:
            _logger.info("*****************Exception******************:%r",e)
            return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)





    def write(self, vals):
        res = super(ResPartner,self).write(vals)
        vals_keys = set(vals.keys())
        change_vals = ','.join(vals_keys)
        fields = set(['name','street','city','state_id','country_id','vat','phone','zip','mobile','email','barcode','write_date','property_account_position_id', 'active'])
        common_fields = fields.intersection(vals_keys)
        if len(common_fields):
            for record in self:
                partner_operations = self.env['common.cache.notification'].search([('model_name','=',"res.partner"),('record_id','=',record.id),('state','in',['error','draft'])],order="id desc")
                if not len(partner_operations):
                    self.env['common.cache.notification'].create({
                        'record_id': record.id,
                        'operation': 'UPDATE',
                        'model_name': "res.partner",
                        'change_vals': change_vals,
                        'state':'draft'
                    })
        return res

    @api.model_create_multi
    def create(self, vals):
        res = super(ResPartner,self).create(vals)
        for rec in res:
            if rec:
                self.env['common.cache.notification'].create({
                    'record_id': rec.id,
                    'operation': 'CREATE',
                    'model_name': "res.partner",
                    'change_vals': 'New Partner Created',
                    'state':'draft'
                })
        return res


    def unlink(self):
        for record in self:
            self.env['common.cache.notification'].create({
                'record_id': record.id,
                'operation': 'DELETE',
                'model_name': "res.partner",
                'change_vals': 'Partner Deleted',
                'state':'draft'
            })
        return super(ResPartner,self).unlink()

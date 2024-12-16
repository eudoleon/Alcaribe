# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError
import json
import base64
import math
from datetime import datetime, timedelta
from odoo.tools import date_utils
import time
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")


class ModelDataRecord(models.Model):
    _name = 'model.data.record'
    _description = "Model Data Record"

    model_name = fields.Selection(
        [('product.product', 'Product'), ('res.partner', 'Partner')], string='Model Name')

    mongo_config = fields.Many2one(
        string='Mongo Config',
        comodel_name='mongo.server.config',
        ondelete='restrict',
    )
    server_data_cache = fields.Binary(string="Server Data Cache")
    min_id = fields.Integer("Min Id")
    max_id = fields.Integer("Max Id")
    offset_start = fields.Integer("Offset Start")
    offset_end = fields.Integer("Offset end")


class PosFastLoadingMessage(models.TransientModel):
    _name = "pos.fast.loading.message"
    _description = "Pos Fast Loading Message"

    text = fields.Text('Message')


class MongoServerConfig(models.Model):
    _name = 'mongo.server.config'
    _description = "Mongo Server Config"
    _rec_name = 'load_pos_data_from'

    mongo_host = fields.Char(string="Host")
    active_record = fields.Boolean(default=False, readonly=True)
    mongo_port = fields.Char(string="Port")
    product_field_ids = fields.Many2many('ir.model.fields', 'product_mapping_with_mongo', string="Additional Product Fields",
                                         domain="[('model_id.model','=','product.product'),('name','not in',['display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id','barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description','product_tmpl_id','tracking'])]")
    partner_field_ids = fields.Many2many('ir.model.fields', 'customer_mapping_with_mongo', string="Additional Partner Fields",
                                         domain="[('model_id.model','=','res.partner'),('name','not in',['name','street','city','state_id','country_id','vat','phone','zip','mobile','email','barcode','write_date','property_account_position_id','property_product_pricelist'])]")
    collection_data = fields.One2many(
        string='Loaded Record',
        comodel_name='model.data.record',
        inverse_name='mongo_config',
    )
    limit = fields.Integer(
        'Limit', default=1000, help="Limit to load the first time records. Remaining will load in the background")
    product_last_update_time = fields.Datetime('Product Last Sync Time')
    cache_last_update_time = fields.Datetime('Cache Last Sync Time')
    price_last_update_time = fields.Datetime('Price Last Sync Time')
    partner_last_update_time = fields.Datetime('Customer Last Sync Time')
    is_updated = fields.Boolean("Is updated", default=False)
    partner_all_fields = fields.Boolean('All Partner Fields', default=False)
    product_all_fields = fields.Boolean('All Products Fields', default=False)

    is_product_synced = fields.Boolean('Is Product Synced', default=False)
    is_partner_synced = fields.Boolean('Is Partner Synced', default=False)
    is_pricelist_synced = fields.Boolean('Is Pricelist Synced', default=False)

    pos_pricelist_cache = fields.Binary(string="Pos Pricelist Cache")

    is_ordinary_loading = fields.Boolean(
        string="Is Loaded Ordinary", default=False)
    is_pos_data_synced = fields.Boolean(
        string="Is All Data Synced", default=False)

    load_pos_data_from = fields.Selection(string="Load Pos Data From", selection=[
                                          ('postgres', 'Postgres'), ('mongo', 'Mongo')], default="postgres")
    pos_live_sync = fields.Selection(string="Pos Syncing", selection=[('realtime', 'Real Time Update'), (
        'notify', 'Only notify when Changes Occur'), ('reload', 'Apply changes on reloading')], default="notify")

    def write(self, vals):
        for obj in self:
            if obj.load_pos_data_from != vals.get('load_pos_data_from') and vals.get('load_pos_data_from'):
                vals.update({
                    'product_last_update_time': False,
                    'cache_last_update_time': False,
                    'price_last_update_time': False,
                    'partner_last_update_time': False,
                    'is_ordinary_loading': True,
                    'is_product_synced': False,
                    'is_pricelist_synced': False,
                    'is_partner_synced': False
                })
        res = super(MongoServerConfig, self).write(vals)
        return res

    @api.constrains('active_record')
    def validate_mongo_server_active_records(self):
        records = self.search([])
        count = 0
        for record in records:
            if record.active_record == True:
                count += 1
        if(count > 1):
            raise ValidationError("You can't have two active mongo configs.")

    def toggle_active_record(self):
        if self.active_record:
            self.active_record = False
        else:
            self.active_record = True

    def check_connection(self):
        client = self.get_client()
        try:
            info = client.server_info()  # Forces a call.
            raise ValidationError("login successfully")
        except ServerSelectionTimeoutError:
            raise ValidationError("server is down.")

    def get_client(self):
        host = self.mongo_host
        port = self.mongo_port
        url = "mongodb://%s:%s" % (host, port)
        try:
            return MongoClient(url)
        except Exception as e:
            raise ValidationError("Exception Occurred : {}".format(e))

    @api.model
    def get_products_from_mongo(self, **kwargs):
        mongo_server_rec = self.search([], limit=1)
        client = mongo_server_rec.get_client()
        fields = kwargs.get('fields')
        if mongo_server_rec.product_field_ids:
            fields = fields + [str(data.name)
                               for data in self.product_field_ids]
        product_operations = self.env['common.cache.notification'].search(
            [('state', '=', 'draft')], order="id asc")
        try:
            info = client.server_info()
            if client:
                database = self._cr.dbname
                if database in client.list_database_names():
                    db = client[database]
                    products_col = db.products
                    product_cur = products_col.find()
                    res = []
                    for record in product_cur:
                        if record.get('id'):
                            if(record.get('_id')):
                                del record['_id']
                            res.append(record)
                    return res
        except Exception as e:
            _logger.info("____________Exception__________:%r", e)
            return False
        return False
    
    def find_related_product_file(self, product_id, create = False):
        if self.collection_data:
            if create:
                bin_file_data = self.collection_data.filtered(lambda x: x.model_name == 'product.product' and x.min_id<=product_id and x.offset_end <= self.limit)
            else:
                bin_file_data = self.collection_data.filtered(lambda x: x.model_name == 'product.product' and x.min_id<=product_id and x.max_id >= product_id)
            if bin_file_data:
                return bin_file_data[0]
            else:
                return False
        else:
            return False
        
    def find_related_partner_file(self, partner_id, create= False):
        if self.collection_data:
            if create:
                bin_file_data = self.collection_data.filtered(lambda x: x.model_name == 'res.partner' and x.min_id<=partner_id and x.offset_end <= self.limit)
            else:
                bin_file_data = self.collection_data.filtered(lambda x: x.model_name == 'res.partner' and x.min_id<=partner_id and x.max_id >= partner_id)
            if bin_file_data:
                return bin_file_data[0]
            else:
                return False
        else:
            return False

    def load_rem_product(self, custom_search_params):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        _logger.info(f"####### loading remaining product  page - {custom_search_params.get('page')} ############")
        
        temp = request.session.get('product_loaded_details', '')
        col_ids = [int(i) for i in temp.split(',') if i.isdigit()]
        binary_data_rec = mongo_server_rec.collection_data.filtered(
            lambda x: x.model_name == 'product.product' and x.id not in col_ids)
        if binary_data_rec and mongo_server_rec and mongo_server_rec.load_pos_data_from == 'postgres':
            temp += str(binary_data_rec[0].id)+','
            json_data = json.loads(base64.decodebytes(
                binary_data_rec[0].server_data_cache).decode('utf-8'))
            data = json_data.values()
            request.session['product_loaded_details'] = temp
            return list(data)
        else:
            _logger.info("####### remaining product loaded ############")
            return []

    def load_rem_customer(self, custom_search_params):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        _logger.info(f"####### loading remaining customers  page - {custom_search_params.get('page')} ############")
        temp = request.session.get('partner_loaded_details', '')
        col_ids = [int(i) for i in temp.split(',') if i.isdigit()]
        binary_data_rec = mongo_server_rec.collection_data.filtered(
            lambda x: x.model_name == 'res.partner' and x.id not in col_ids)
        if binary_data_rec and mongo_server_rec and mongo_server_rec.load_pos_data_from == 'postgres':
            temp += str(binary_data_rec[0].id)+','
            json_data = json.loads(base64.decodebytes(
                binary_data_rec[0].server_data_cache).decode('utf-8'))
            data = json_data.values()
            request.session['partner_loaded_details'] = temp
            return list(data)
        else:
            _logger.info("####### remaining partner loaded ############")
            return []

    @api.model
    def get_data_on_sync(self, kwargs):
        pos_mongo_config = kwargs.get('mongo_cache_last_update_time')
        config_id = False
        if kwargs.get('config_id'):
            config_id = self.env['pos.config'].browse(kwargs.get('config_id'))
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            data_dict = {
                'products': [],
                'pricelist_items': [],
                'partners': [],
                'mongo_config': mongo_server_rec.cache_last_update_time,
                'price_deleted_record_ids': [],
                # 'price_deleted_records':[],
                'partner_deleted_record_ids': [],
                'product_deleted_record_ids': [],
                'sync_method': mongo_server_rec.pos_live_sync
            }
            try:
                self.env['common.cache.notification'].with_context(
                    coming_from_pos=True, company_id=config_id.company_id if config_id else False).get_common_changes()
                product_data = []
                pricelist_item_data = []
                new_cache_records = self.env['common.cache.notification'].search(
                    [('create_date', '>=', pos_mongo_config)])

                if new_cache_records:
                    product_record_ids = []
                    price_record_ids = []
                    partner_record_ids = []
                    partner_deleted_record_ids = []
                    price_deleted_record_ids = []
                    product_deleted_record_ids = []
                    price_res = []
                    product_res = []
                    partner_res = []
                    for record in new_cache_records:
                        if record.model_name == 'product.product':
                            if record.operation == 'DELETE':
                                product_deleted_record_ids.append(
                                    record.record_id)
                            else:
                                product_record_ids.append(record.record_id)
                        elif record.model_name == 'res.partner':
                            if record.operation == 'DELETE':
                                partner_deleted_record_ids.append(
                                    record.record_id)
                            else:
                                partner_record_ids.append(record.record_id)
                        elif record.model_name == 'product.pricelist.item':
                            if record.operation == 'DELETE':
                                price_deleted_record_ids.append(
                                    record.record_id)
                            elif record.operation == 'UPDATE':
                                price_record_ids.append(record.record_id)
                                price_deleted_record_ids.append(
                                    record.record_id)
                            else:
                                price_record_ids.append(record.record_id)

                    load_pos_data_type = mongo_server_rec.load_pos_data_from
                    if load_pos_data_type == 'mongo':
                        client = mongo_server_rec.get_client()
                        if client:
                            database = self._cr.dbname
                            if database in client.list_database_names():
                                db = client[database]
                                if len(price_record_ids):
                                    pricelist_items_col = db.pricelist_items
                                    pricelist_item_data = pricelist_items_col.find(
                                        {'id': {'$in': price_record_ids}})
                                    for record in pricelist_item_data:
                                        if record.get('id'):
                                            if(record.get('_id')):
                                                del record['_id']
                                            price_res.append(record)
                                    pricelist_item_deleted_data = pricelist_items_col.find(
                                        {'id': {'$in': price_deleted_record_ids}})
                                if len(product_record_ids):
                                    products_col = db.products
                                    product_data = products_col.find(
                                        {'id': {'$in': product_record_ids}})
                                    for record in product_data:
                                        if record.get('id'):
                                            if(record.get('_id')):
                                                del record['_id']
                                            product_res.append(record)
                                if len(partner_record_ids):
                                    partners_col = db.partners
                                    partner_data = partners_col.find(
                                        {'id': {'$in': partner_record_ids}})
                                    for record in partner_data:
                                        if record.get('id'):
                                            if(record.get('_id')):
                                                del record['_id']
                                            partner_res.append(record)
                    else:
                        if len(price_record_ids):
                            binary_data = mongo_server_rec.pos_pricelist_cache
                            json_data = json.loads(
                                base64.decodebytes(binary_data).decode('utf-8'))
                            for obj in json_data:
                                if int(obj) in price_record_ids:
                                    price_res.append(json_data.get(obj))

                        if len(product_record_ids) and config_id:
                            product_res = self.env['product.product'].with_company(
                            config_id.company_id.id).search_read([('id', 'in', product_record_ids)], fields= self.return_product_fields(mongo_server_rec))

                        if len(partner_record_ids) and config_id:
                            partner_res = self.env['res.partner'].with_company(
                            config_id.company_id.id ).search_read([('id', 'in', partner_record_ids)], fields= self.return_partner_fields(mongo_server_rec))

                    data_dict.update({
                        'products': product_res,
                        'pricelist_items': price_res,
                        'partners': partner_res,
                        'mongo_config': mongo_server_rec.cache_last_update_time,
                        'price_deleted_record_ids': price_deleted_record_ids,
                        'partner_deleted_record_ids': partner_deleted_record_ids,
                        'product_deleted_record_ids': product_deleted_record_ids
                    })
                return data_dict
            except Exception as e:
                return data_dict
                _logger.info("**********Exception*****************:%r", e)

    def return_partner_fields(self, mongo_server_rec):
        fields = ['name', 'street', 'city', 'country_id', 'state_id', 'vat', 'color', 'phone', 'zip', 'mobile', 'email', 'barcode', 'write_date',
                  'property_account_position_id', 'property_product_pricelist', 'company_name', 'property_supplier_payment_term_id', 'active']
        if self.partner_field_ids:
            fields = fields + [str(data.name)
                               for data in self.partner_field_ids]
        if self.partner_all_fields:
            if mongo_server_rec.load_pos_data_from == 'postgres':
                customer_fields = self.env['ir.model'].sudo().search(
                    [('model', '=', 'res.partner')]).field_id
                new_fields = [
                    i.name for i in customer_fields if i.ttype != 'binary']
                temp_fields = set(fields).union(set(new_fields))
                fields = list(temp_fields)
            else:
                fields = []
        return fields

    def return_product_fields(self, mongo_server_rec):
        fields = ['active', 'display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                  'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
                  'product_tmpl_id', 'tracking', 'available_in_pos', 'optional_product_ids']
        if mongo_server_rec.product_field_ids:
            fields = list(set(fields + [str(data.name)
                                        for data in self.product_field_ids]))
        if self.product_all_fields:
            if mongo_server_rec.load_pos_data_from == 'postgres':
                product_fields = self.env['ir.model'].sudo().search(
                    [('model', '=', 'product.product')]).field_id
                new_fields = [
                    i.name for i in product_fields if i.ttype != 'binary']
                temp_fields = set(fields).union(set(new_fields))
                fields = list(temp_fields)
            else:
                fields = []
        return fields

    def load_partner_data_mongo(self, p_data, partner_fields):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            client = mongo_server_rec.get_client()
            databases = client.list_database_names()
            database = self._cr.dbname
            if database in databases:
                db = client[database]
                db.partners.drop()
                partners_col = db.partners

                for count in range(math.ceil(len(p_data)/1000)):
                    partners_data = []
                    data_to_add = p_data[count*1000:(count+1)*1000]
                    for record in range(math.ceil(len(data_to_add)/100)):
                        data_to_find = data_to_add[record *
                                                100:(record+1)*100]
                        pro_data = data_to_find.read(partner_fields)
                        if len(pro_data):
                            partners_data.extend(pro_data)
                    partners_col.insert_many(partners_data)
                partners_synced = len(p_data)
            else:
                db = client[database]
                partners_col = db.partners
                for count in range(math.ceil(len(p_data)/1000)):
                    partners_data = []
                    data_to_add = p_data[count*1000:(count+1)*1000]
                    for record in range(math.ceil(len(data_to_add)/100)):
                        data_to_find = data_to_add[record *
                                                100:(record+1)*100]
                        pro_data = data_to_find.read(partner_fields)
                        if len(pro_data):
                            partners_data.extend(pro_data)
                    partners_col.insert_many(partners_data)
            return partners_data

    def load_partner_data_postgres(self, p_data, partner_fields):
        partner_data = {}
        partner_dict = {}
        # for count in range(math.ceil(len(p_data)/1000)):
        #     partner_dict = {}
        #     data_to_add = p_data[count*1000:(count+1)*1000]
        #     for record in range(math.ceil(len(data_to_add)/100)):
        #         data_to_find = data_to_add[record*100:(record+1)*100]
        pro_data = p_data.read(partner_fields)
        for partner_conv_data in pro_data:
            partner_dict[partner_conv_data.get(
                'id')] = partner_conv_data
            partner_data.update(partner_dict)
        return partner_data

    def delete_common_cache(self, model_name):
        records_to_delete = self.env['common.cache.notification'].search(
            [('model_name', '=', model_name)])
        if len(records_to_delete):
            records_to_delete.unlink()

    def delete_server_cache(self, model_name, mongo_server_rec):
        server_rec = self.env['model.data.record'].search(
            [('mongo_config', '=', mongo_server_rec.id), ('model_name', '=', model_name)])
        if len(server_rec):
            server_rec.unlink()

    def load_product_data_mongo(self, p_data, product_fields):
        try:
            mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
            client = mongo_server_rec.get_client()
            databases = client.list_database_names()
            database = self._cr.dbname
            if database in databases:
                db = client[database]
                db.products.drop()
                products_col = db.products
                for count in range(math.ceil(len(p_data)/1000)):
                    product_data = []
                    data_to_add = p_data[count*1000:(count+1)*1000]
                    for record in range(math.ceil(len(data_to_add)/100)):
                        data_to_find = data_to_add[record *
                                                   100:(record+1)*100]
                        pro_data = data_to_find.read(product_fields)
                        if len(pro_data):
                            product_data.extend(pro_data)
                    products_col.insert_many(product_data)
            else:
                db = client[database]
                products_col = db.products

                for count in range(math.ceil(len(p_data)/1000)):
                    product_data = []
                    data_to_add = p_data[count*1000:(count+1)*1000]
                    for record in range(math.ceil(len(data_to_add)/100)):
                        data_to_find = data_to_add[record *
                                                   100:(record+1)*100]
                        pro_data = data_to_find.read(product_fields)
                        if len(pro_data):
                            product_data.extend(pro_data)
                    products_col.insert_many(product_data)
            return product_data
        except ServerSelectionTimeoutError:
            raise ValidationError("server is down.")

    def load_product_data_postgres(self, p_data, product_fields):
        products_data = {}
        product_dict = {}
        # for count in range(math.ceil(len(p_data)/1000)):
        #     product_dict = {}
        #     data_to_add = p_data[count*1000:(count+1)*1000]
        #     for record in range(math.ceil(len(data_to_add)/100)):
        #         data_to_find = data_to_add[record*100:(record+1)*100]
        pro_data = p_data.read(product_fields)
        for product_conv_data in pro_data:
            product_dict[product_conv_data.get(
                'id')] = product_conv_data
            products_data.update(product_dict)
        return products_data

    def sync_partners(self):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        server_data_batch = self.env['model.data.record']
        if mongo_server_rec:
            self.delete_server_cache('res.partner', mongo_server_rec)
            partner_fields = self.return_partner_fields(mongo_server_rec)
            load_pos_data_type = mongo_server_rec.load_pos_data_from
            offset = 0
            created_rec = []
            self._cr.execute(
                'select count(*) from res_partner where active= True')
            partner_len = self._cr.fetchone()[0]
            if load_pos_data_type == 'mongo':
                p_data = self.env['res.partner'].search([])
                partner_data = self.load_partner_data_mongo(
                    p_data, partner_fields)
            else:
                while(offset < partner_len):

                    p_data = self.env['res.partner'].search(
                        [], offset=offset, limit=mongo_server_rec.limit)
                    
                    partner_data = self.load_partner_data_postgres(
                        p_data, partner_fields)
                    partner_keys = partner_data.keys()
                    min_id, max_id = min(partner_keys), max(partner_keys)
                    search_data_len = len(partner_data)
                    temp = search_data_len + \
                        offset if search_data_len < mongo_server_rec.limit else mongo_server_rec.limit+offset
                    _logger.info(
                        f'########## partner syncing start from {offset} to {temp} #######')
                    batch_rec = server_data_batch.search([('mongo_config', '=', mongo_server_rec.id), (
                        'model_name', '=', 'res.partner'), ('offset_start', '=', offset), ('offset_end', '=', temp)])
                    data = {'server_data_cache': base64.encodebytes(
                            json.dumps(partner_data, default=date_utils.json_default).encode('utf-8'))}

                    if batch_rec:
                        batch_rec[0].write(data)
                    else:
                        data.update({
                            'mongo_config': mongo_server_rec.id,
                            'min_id': min_id,
                            'max_id': max_id,
                            'offset_start': offset,
                            'offset_end': temp,
                            'model_name': 'res.partner'
                        })
                        batch_rec = server_data_batch.create(data)
                        created_rec.append(batch_rec.id)
                    self._cr.commit()
                    offset = temp
                if created_rec:
                    mongo_server_rec.collection_data = [(4, 0, created_rec)]
                _logger.info(f'########## partner syncing end #######')
            mongo_server_rec.write({
                'partner_last_update_time': datetime.now(),
                'is_partner_synced': True
            })
            self.delete_common_cache('res.partner')
            try:
                if mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                    mongo_server_rec.write({
                        'is_ordinary_loading': False,
                        'is_pos_data_synced': True
                    })
                    # self.env['common.cache.notification'].get_common_changes()
                message = self.env['pos.fast.loading.message'].create(
                    {'text': "{} Customers have been synced.".format(partner_len)})
                return {'name': _("Message"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'pos.fast.loading.message',
                        'res_id': message.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        }
            except Exception as e:
                _logger.info(
                    "*********************Exception**************:%r", e)

    def sync_products(self):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        server_data_batch = self.env['model.data.record']
        if mongo_server_rec:
            self.delete_server_cache('product.product', mongo_server_rec)
            product_fields = self.return_product_fields(mongo_server_rec)
            offset = 0
            created_rec = []
            load_pos_data_type = mongo_server_rec.load_pos_data_from
            self._cr.execute(
                'select count(*) from product_product as pp join product_template as pt on pp.product_tmpl_id = pt.id where pp.active= True and pt.available_in_pos = True and pt.sale_ok= True')
            product_len = self._cr.fetchone()[0]
            if load_pos_data_type == 'mongo':
                p_data = self.env['product.product'].search([('sale_ok','=',True),('available_in_pos','=',True)])
                products_data = self.load_product_data_mongo(
                    p_data, product_fields)
            else:
                while(offset < product_len):
                    p_data = self.env['product.product'].search(
                        [['sale_ok', '=', True], ['available_in_pos', '=', True]], offset=offset, limit=mongo_server_rec.limit)
                    products_data = self.load_product_data_postgres(
                        p_data, product_fields)
                    product_keys = products_data.keys()
                    min_id, max_id = min(product_keys), max(product_keys)
                    search_data_len = len(products_data)
                    temp = search_data_len + \
                        offset if search_data_len < mongo_server_rec.limit else mongo_server_rec.limit+offset
                    _logger.info(
                        f'########## product syncing start from {offset} to {temp} #######')
                    batch_rec = server_data_batch.search([('mongo_config', '=', mongo_server_rec.id), (
                        'model_name', '=', 'product.product'), ('offset_start', '=', offset), ('offset_end', '=', temp)])
                    data = {'server_data_cache': base64.encodebytes(
                            json.dumps(products_data, default=date_utils.json_default).encode('utf-8'))}
                    if batch_rec:
                        batch_rec[0].write(data)
                    else:
                        data.update({
                            'mongo_config': mongo_server_rec.id,
                            'offset_start': offset,
                            'min_id': min_id,
                            'max_id': max_id,
                            'offset_end': temp,
                            'model_name': 'product.product'
                        })
                        batch_rec = server_data_batch.create(data)
                        created_rec.append(batch_rec.id)
                    self._cr.commit()
                    offset = temp
                if created_rec:
                    mongo_server_rec.collection_data = [(4, 0, created_rec)]
                _logger.info(f'########## product syncing end #######')
            mongo_server_rec.write({
                'product_last_update_time': datetime.now(),
                'is_product_synced': True
            })

            self.delete_common_cache('product.product')
            try:

                if mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                    mongo_server_rec.write({
                        'is_ordinary_loading': False,
                        'is_pos_data_synced': True
                    })
                    # self.env['common.cache.notification'].get_common_changes()
                message = self.env['pos.fast.loading.message'].create(
                    {'text': "{} Products have been synced.".format(product_len)})
                return {'name': _("Message"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'pos.fast.loading.message',
                        'res_id': message.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        }
            except Exception as e:
                _logger.info(
                    "*********************Exception**************:%r", e)

    def sync_pricelist_items(self):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        # try:
        if mongo_server_rec:
            load_pos_data_type = mongo_server_rec.load_pos_data_from
            pricelist_items_synced = 0
            records = self.env['product.pricelist.item'].search([])
            fields = ['__last_update', 'active', 'base', 'categ_id', 'base_pricelist_id', 'company_id', 'compute_price', 'create_date', 'create_uid', 'currency_id', 'date_end', 'date_start', 'display_name', 'fixed_price', 'id',
                      'min_quantity', 'name', 'percent_price', 'price', 'price_discount', 'price_max_margin', 'price_min_margin', 'price_round', 'price_surcharge', 'pricelist_id', 'product_id', 'product_tmpl_id', 'write_date', 'write_uid']
            if load_pos_data_type == 'mongo':
                client = self.get_client()
                databases = client.list_database_names()
                database = self._cr.dbname
                if database in databases:
                    db = client[database]
                    db.pricelist_items.drop()
                    pricelist_items_col = db.pricelist_items
                    new_data = []
                    count = 0
                    for data in records:
                        field_data = data.read(fields)
                        count += 1
                        date_start, date_end = (False, False)
                        if data.date_start:
                            date_start = datetime(
                                data.date_start.year, data.date_start.month, data.date_start.day) or False
                        if data.date_end:
                            date_end = datetime(
                                data.date_end.year, data.date_end.month, data.date_end.day) or False
                        if date_start:
                            field_data[0]['date_start'] = date_start
                        if date_end:
                            field_data[0]['date_end'] = date_end
                        new_data.extend(field_data)
                    if len(new_data):
                        for count in range(math.ceil(len(new_data)/1000)):
                            data_to_add = new_data[count*1000:(count+1)*1000]
                            pricelist_items_col.insert_many(data_to_add)
                        pricelist_items_synced = len(new_data)

                else:
                    db = client[database]
                    pricelist_items_col = db.pricelist_items
                    new_data = []
                    count = 0
                    for data in records:
                        field_data = data.read(fields)
                        count += 1
                        date_start, date_end = (False, False)
                        if data.date_start:
                            date_start = datetime(
                                data.date_start.year, data.date_start.month, data.date_start.day) or False
                        if data.date_end:
                            date_end = datetime(
                                data.date_end.year, data.date_end.month, data.date_end.day) or False
                        if date_start:
                            field_data[0]['date_start'] = date_start
                        if date_end:
                            field_data[0]['date_end'] = date_end
                        new_data.extend(field_data)
                    if len(new_data):
                        for count in range(math.ceil(len(new_data)/1000)):
                            data_to_add = new_data[count*1000:(count+1)*1000]
                            pricelist_items_col.insert_many(data_to_add)
                        pricelist_items_synced = len(new_data)
            else:
                pricelist_data = {}
                for count in range(math.ceil(len(records)/1000)):
                    pricelist_dict = {}
                    data_to_add = records[count*1000:(count+1)*1000]
                    for record in range(math.ceil(len(data_to_add)/100)):
                        data_to_find = data_to_add[record*100:(record+1)*100]
                        price_data = data_to_find.read([])
                        for pricelist_conv_data in price_data:
                            pricelist_dict[pricelist_conv_data.get(
                                'id')] = pricelist_conv_data
                    pricelist_data.update(pricelist_dict)
                pricelist_items_synced = len(records)
                data = {'pos_pricelist_cache': base64.encodebytes(
                    json.dumps(pricelist_data, default=date_utils.json_default).encode('utf-8'))}
                mongo_server_rec.write(data)
            records_to_delete = self.env['common.cache.notification'].search(
                [('model_name', '=', 'product.pricelist.item')])
            if len(records_to_delete):
                records_to_delete.unlink()
            mongo_server_rec.price_last_update_time = datetime.now()
            mongo_server_rec.is_pricelist_synced = True
            try:
                if mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    mongo_server_rec.is_pos_data_synced = True
                self.env['common.cache.notification'].get_common_changes()
                message = self.env['pos.fast.loading.message'].create(
                    {'text': "{} Pricelist Items have been synced.".format(pricelist_items_synced)})
                return {'name': _("Message"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'pos.fast.loading.message',
                        'res_id': message.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        }
            except Exception as e:
                _logger.info(
                    "*********************Exception**************:%r", e)

    @api.model
    def get_pricelist_items_from_mongo(self, **kwargs):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            client = mongo_server_rec.get_client()
            try:
                info = client.server_info()
                if client:
                    database = self._cr.dbname
                    if database in client.list_database_names():
                        db = client[database]
                        pricelist_items_col = db.pricelist_items
                        pricelist_items = pricelist_items_col.find(
                            ({'id': {'$in': kwargs.get('pricelist_item_ids')}}))
                        res = []
                        for record in pricelist_items:
                            if record.get('id'):
                                if(record.get('_id')):
                                    del record['_id']
                                res.append(record)
                        return res
            except ServerSelectionTimeoutError:
                return False
            return False

    @api.model
    def get_customer_data_from_mongo(self, **kwargs):
        mongo_server_rec = self.search([('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            try:
                if kwargs.get('client'):
                    client = kwargs.get('client')
                else:
                    client = mongo_server_rec.get_client()
                    info = client.server_info()
                if client:
                    database = self._cr.dbname
                    if database in client.list_database_names():
                        db = client[database]
                        partner_col = db.partners
                        partner_cur = partner_col.find()

                        res = []
                        for record in partner_col.find():
                            if record.get('id'):
                                if(record.get('_id')):
                                    del record['_id']
                                res.append(record)
                        return res
            except Exception as e:
                _logger.info(
                    "------------------except(*****************):%r", e)
                return False
            return False

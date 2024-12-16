# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

from datetime import datetime, timedelta
from odoo.exceptions import Warning, ValidationError
from odoo import models, fields, api, _
import _pickle as cPickle
import logging
import json
import base64
from odoo.tools import date_utils


_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")


class CommonCacheNotification(models.Model):
    _name = 'common.cache.notification'
    _description = "Common Cache Notification"

    model_name = fields.Char('Model Name')
    record_id = fields.Integer('Record Id')
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'), ('done', 'Done'), ('failed', 'Failed')],
        default='draft'
    )
    operation = fields.Selection(
        selection=[('DELETE', 'DELETE'), ('UPDATE', 'UPDATE'), ('CREATE', 'CREATE')])
    change_vals = fields.Text(string="Fields Changed")

    @api.model_create_multi
    def create(self, vals):
        res = super(CommonCacheNotification, self).create(vals)
        try:
            mongo_server_rec = self.env['mongo.server.config'].search(
                [('active_record', '=', True)], limit=1)
            mongo_server_rec.is_updated = False
        except Exception as e:
            _logger.info("****************Exception***********:%r", e)
        return res

    @api.model
    def get_common_changes(self):
        records = self.sudo().search([('state', '!=', 'done')])
        mongo_server_rec = self.env['mongo.server.config'].search(
            [('active_record', '=', True)], limit=1)
        if mongo_server_rec:
            partner_fields = ['name', 'street', 'city', 'state_id', 'country_id', 'vat', 'color', 'phone', 'zip', 'mobile', 'email', 'barcode',
                            'write_date', 'property_account_position_id', 'property_product_pricelist', 'company_name', 'property_supplier_payment_term_id', 'state_id', 'active']
            if mongo_server_rec.partner_field_ids:
                partner_fields = partner_fields + \
                    [str(data.name) for data in mongo_server_rec.partner_field_ids]
            if mongo_server_rec.partner_all_fields:
                if mongo_server_rec.load_pos_data_from == 'postgres':
                    customer_fields = self.env['ir.model'].sudo().search(
                        [('model', '=', 'res.partner')]).field_id
                    new_fields = [
                        i.name for i in customer_fields if i.ttype != 'binary']
                    temp_fields = set(partner_fields).union(set(new_fields))
                    partner_fields = list(temp_fields)
                else:
                    partner_fields = []
            product_fields = ['display_name', 'list_price', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                            'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
                            'product_tmpl_id', 'tracking', 'active', 'available_in_pos','optional_product_ids']

            pricelist_fields = ['__last_update', 'active', 'applied_on', 'base', 'base_pricelist_id', 'categ_id', 'company_id', 'compute_price', 'create_date', 'create_uid', 'currency_id', 'date_end', 'date_start', 'display_name', 'fixed_price',
                                'id', 'min_quantity', 'name', 'percent_price', 'price', 'price_discount', 'price_max_margin', 'price_min_margin', 'price_round', 'price_surcharge', 'pricelist_id', 'product_id', 'product_tmpl_id', 'write_date', 'write_uid']
            if mongo_server_rec.product_field_ids:
                product_fields = list(set(
                    product_fields + [str(data.name) for data in mongo_server_rec.product_field_ids]))

            if mongo_server_rec.product_all_fields:
                if mongo_server_rec.load_pos_data_from == 'postgres':
                    fields = self.env['ir.model'].sudo().search(
                        [('model', '=', 'product.product')]).field_id
                    new_fields = [i.name for i in fields if i.ttype != 'binary']
                    temp_fields = set(product_fields).union(set(new_fields))
                    product_fields = list(temp_fields)
                else:
                    product_fields = []

            load_pos_data_type = mongo_server_rec.load_pos_data_from
            if load_pos_data_type == 'mongo':
                self.sync_mongo_cache(
                    mongo_server_rec, records, partner_fields, product_fields, pricelist_fields)
            else:
                self.sync_pos_cache(mongo_server_rec, records,
                                    partner_fields, product_fields)

            updated_records = self.search(
                [('state', '=', 'done')], order="id desc")
            records_to_delete = []
            if len(updated_records):
                records_to_delete = updated_records[500:]
            if len(records_to_delete):
                records_to_delete.unlink()
            if not mongo_server_rec.cache_last_update_time and not mongo_server_rec.is_ordinary_loading and mongo_server_rec.is_partner_synced and mongo_server_rec.is_pricelist_synced and mongo_server_rec.is_product_synced:
                mongo_server_rec.cache_last_update_time = datetime.now()

    def sync_pos_cache(self, mongo_server_rec, records, partner_fields, product_fields):
        if(len(records)) and mongo_server_rec:
            # partner_json_data = json.loads(base64.decodebytes(mongo_server_rec.pos_partner_cache).decode('utf-8')) if mongo_server_rec.pos_partner_cache else False
            # product_json_data = json.loads(base64.decodebytes(mongo_server_rec.pos_product_cache).decode('utf-8')) if mongo_server_rec.pos_product_cache else False
            bin_file = False
            pricelist_json_data = json.loads(base64.decodebytes(mongo_server_rec.pos_pricelist_cache).decode('utf-8')) if mongo_server_rec.pos_pricelist_cache else False
            for record in records:
                # try:
                if record.operation == "UPDATE" or record.operation == "CREATE":
                    values = []
                    if record.model_name == 'res.partner':
                        partner = self.env[record.model_name].browse(
                            record.record_id)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                        partner_data = {}
                        if partner:
                            if self._context.get('company_id') and self._context.get('uid'):
                                pro_data = partner.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read(partner_fields)
                            else:
                                pro_data = partner.sudo().read(partner_fields)
                            if len(pro_data):
                                partner_conv_data = pro_data[0]
                                if len(partner_conv_data):
                                    partner_data = partner_conv_data
                        if len(partner_data):
                            update_type = record.operation == 'CREATE'
                            bin_file = mongo_server_rec.find_related_partner_file(partner_data['id'], create=update_type)
                            if bin_file:
                                partner_json_data = json.loads(base64.decodebytes(bin_file.server_data_cache).decode('utf-8')) if bin_file.server_data_cache else False
                                if partner_json_data:
                                    partner_json_data[str(partner_data.get("id"))] = partner_data
                        record.state = 'done'

                    elif record.model_name == 'product.product':
                        product = self.env[record.model_name].browse(
                            record.record_id)
                        product_data = {}
                        if product:
                            if self._context.get('company_id') and self._context.get('uid'):
                                pro_data = product.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read(product_fields)
                            else:
                                pro_data = product.sudo().read(product_fields)
                            if len(pro_data):
                                product_conv_data = pro_data[0]
                                image_fields = ['image_1024', 'image_128', 'image_1920', 'image_256', 'image_512', 'image_variant_1024',
                                                'image_variant_128', 'image_variant_1920', 'image_variant_256', 'image_variant_512']
                                initial_keys = pro_data[0].keys()
                                new_field_list = set(image_fields).intersection(
                                    set(initial_keys))
                                for field in new_field_list:
                                    del product_conv_data[field]
                                if len(product_conv_data):
                                    product_data = product_conv_data
                        if len(product_data):
                            update_type = record.operation == 'CREATE' 
                            bin_file = mongo_server_rec.find_related_product_file(product_data['id'], create = update_type)
                            if bin_file:
                                product_json_data = json.loads(base64.decodebytes(bin_file.server_data_cache).decode('utf-8')) if bin_file.server_data_cache else False
                                if product_json_data:
                                    product_json_data[str(product_data.get("id"))] = product_data
                            
                        record.state = 'done'
                    elif record.model_name == 'product.pricelist.item':
                        pricelist_item = self.env[record.model_name].browse(
                            record.record_id)
                        pricelist_data = {}
                        if pricelist_item:
                            if self._context.get('company_id'):
                                pro_data = pricelist_item.sudo().with_company(self._context['company_id']).read()
                            else:
                                pro_data = pricelist_item.sudo().read()
                            if len(pro_data):
                                pricelist_conv_data = pro_data[0]
                                if len(pricelist_conv_data):
                                    pricelist_data = pricelist_conv_data
                        if len(pricelist_data) and pricelist_json_data:
                            pricelist_json_data[pricelist_data.get("id")] = pricelist_data
                        record.state = 'done'

                elif record.operation == "DELETE":
                    if record.model_name == 'res.partner':
                        bin_file = mongo_server_rec.find_related_partner_file(partner_data['id'])
                        if bin_file:
                            partner_json_data = json.loads(base64.decodebytes(bin_file.server_data_cache).decode('utf-8')) if bin_file.server_data_cache else False
                            if partner_json_data.get(str(record.record_id)):
                                del partner_json_data[str(record.record_id)]
                    elif record.model_name == 'product.product':
                        bin_file = mongo_server_rec.find_related_product_file(product_data['id'])
                        if bin_file:
                            product_json_data = json.loads(base64.decodebytes(bin_file.server_data_cache).decode('utf-8')) if bin_file.server_data_cache else False
                            if product_json_data.get(str(record.record_id)):
                                del product_json_data[str(record.record_id)]
                    elif record.model_name == 'product.pricelist.item' and pricelist_json_data:
                        if pricelist_json_data.get(str(record.record_id)):
                            del pricelist_json_data[str(record.record_id)]
                    record.state = 'done'
                    
                    if partner_json_data and bin_file: 
                        updated_data = base64.encodebytes(
                                            json.dumps(partner_json_data, default=date_utils.json_default).encode('utf-8'))
                        if updated_data:
                            data_to_add = {
                                'server_data_cache': updated_data}
                            bin_file.write(data_to_add)
                        # mongo_server_rec.partner_last_update_time = datetime.now()
                    if product_json_data:
                        updated_data = base64.encodebytes(
                                            json.dumps(product_json_data, default=date_utils.json_default).encode('utf-8'))
                        if updated_data:
                            data_to_add = {
                                'server_data_cache': updated_data}
                            bin_file.write(data_to_add)
                        # mongo_server_rec.product_last_update_time = datetime.now()
            if not mongo_server_rec.is_ordinary_loading:
                mongo_server_rec.cache_last_update_time = datetime.now()
            mongo_server_rec.is_updated = True
            if pricelist_json_data:
                updated_data = base64.encodebytes(
                                    json.dumps(pricelist_json_data, default=date_utils.json_default).encode('utf-8'))
                if updated_data:
                    data_to_add = {
                        'pos_pricelist_cache': updated_data}
                    mongo_server_rec.write(data_to_add)
                mongo_server_rec.price_last_update_time = datetime.now()
        else:
            mongo_server_rec.is_updated = True

    def sync_mongo_cache(self, mongo_server_rec, records, partner_fields, product_fields, pricelist_fields):
        _logger.info("**************mongo fwrokgin***********")
        client = mongo_server_rec.get_client()
        if client:
            database = self._cr.dbname
            if database in client.list_database_names():
                db = client[database]
                products_col = db.products
                partners_col = db.partners
                pricelist_items_col = db.pricelist_items
                if(len(records)):
                    for record in records:
                        try:
                            if record.operation == "UPDATE":
                                query = {"id": record.record_id}
                                values = []
                                change_vals = record.change_vals
                                record_fields_list = []
                                if change_vals:
                                    record_fields_list = change_vals.split(',')
                                if 'name' in record_fields_list or 'default_code' in record_fields_list:
                                    record_fields_list.append('display_name')
                                    if 'name' in record_fields_list:
                                        record_fields_list.remove('name')
                                if record.model_name == 'res.partner':
                                    partner = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    if partner:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = partner.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = partner.sudo().read()
                                    if len(values):
                                        newvalues = {"$set":  values[0]}
                                        partners_col.update_one(
                                            query, newvalues, upsert=True)
                                    mongo_server_rec.partner_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.product':
                                    product = self.env[record.model_name].browse(
                                        record.record_id)
                                    # if len(product):
                                    values = []
                                    if product:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = product.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = product.sudo().read()
                                    if len(values):
                                        newvalues = {"$set":  values[0]}
                                        products_col.update_one(
                                            query, newvalues, upsert=True)
                                    mongo_server_rec.product_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.pricelist.item':
                                    records = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    for data in records:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            field_data = data.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            field_data = data.sudo().read()
                                        if(field_data):
                                            date_start, date_end = (
                                                False, False)
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
                                            values.extend(field_data)
                                    if len(values):
                                        newvalues = {"$set":  values[0]}
                                        pricelist_items_col.update_one(
                                            query, newvalues, upsert=True)
                                    mongo_server_rec.price_last_update_time = datetime.now()
                                    record.state = 'done'

                            elif record.operation == "CREATE":
                                values = []
                                if record.model_name == 'res.partner':
                                    partner = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    if partner:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = partner.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = partner.sudo().read()
                                    if len(values):
                                        partners_col.insert_one(values[0])
                                    mongo_server_rec.partner_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.product':
                                    product = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    if product:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            values = product.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            values = product.sudo().read()
                                    if len(values):
                                        products_col.insert_one(values[0])
                                    mongo_server_rec.product_last_update_time = datetime.now()
                                    record.state = 'done'
                                elif record.model_name == 'product.pricelist.item':
                                    records = self.env[record.model_name].browse(
                                        record.record_id)
                                    values = []
                                    for data in records:
                                        if self._context.get('company_id') and self._context.get('uid'):
                                            field_data = data.sudo().with_company(self._context['company_id']).with_user(self.env.context['uid']).read()
                                        else:
                                            field_data = data.sudo().read()
                                        if(field_data):
                                            date_start, date_end = (
                                                False, False)
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
                                            values.extend(field_data)
                                    if len(values):
                                        pricelist_items_col.insert_one(
                                            values[0])
                                    mongo_server_rec.price_last_update_time = datetime.now()
                                    record.state = 'done'
                            elif record.operation == "DELETE":
                                query = {"id": record.record_id}
                                if record.model_name == 'res.partner':
                                    partners_col.delete_many(query)
                                elif record.model_name == 'product.product':
                                    products_col.delete_many(query)
                                elif record.model_name == 'product.pricelist.item':
                                    pricelist_items_col.delete_many(query)
                                record.state = 'done'
                        except Exception as e:
                            _logger.info(
                                "**************Exception*************:%r", e)
                            record.state = 'failed'
                    if not mongo_server_rec.is_ordinary_loading:
                        mongo_server_rec.cache_last_update_time = datetime.now()
                    mongo_server_rec.is_updated = True
                else:
                    mongo_server_rec.is_updated = True

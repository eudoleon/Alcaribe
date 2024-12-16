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
import pickle
import logging
from odoo.http import request
_logger = logging.getLogger(__name__)
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except Exception as e:
    _logger.error("Python's PyMongo Library is not installed.")
from datetime import datetime



class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        try:
            _logger.info("############# product search read start#############")
            mongo_server_rec = self.env['mongo.server.config'].search([('active_record','=',True)],limit=1)
            is_indexed_updated = self._context.get('is_indexed_updated')
            if (self._context.get('sync_from_mongo')) and mongo_server_rec:
                request.session['product_loaded_details'] = ''
                if is_indexed_updated and is_indexed_updated[0] and not is_indexed_updated[0].get('time') and mongo_server_rec.is_ordinary_loading and mongo_server_rec.is_updated:
                    return []
                if mongo_server_rec.cache_last_update_time and mongo_server_rec.is_pos_data_synced:
                    mongo_server_rec.is_ordinary_loading = False
                    load_pos_data_type = mongo_server_rec.load_pos_data_from
                    if load_pos_data_type == 'mongo':
                        if mongo_server_rec.is_updated and is_indexed_updated and is_indexed_updated[0] and mongo_server_rec.cache_last_update_time and is_indexed_updated[0].get("time") >= mongo_server_rec.cache_last_update_time.strftime("%Y-%m-%d %H:%M:%S"):
                            return []
                        else:
                            context = self._context.copy()
                            del context['sync_from_mongo']
                            client = mongo_server_rec.get_client()
                            info = client.server_info()
                            data = self.env['mongo.server.config'].get_products_from_mongo(fields=fields,client=client)
                            if data:
                                return data
                    else:
                        if mongo_server_rec.is_updated and is_indexed_updated and is_indexed_updated[0] and is_indexed_updated[0].get("time") >= mongo_server_rec.cache_last_update_time.strftime("%Y-%m-%d %H:%M:%S"):
                            return []
                        else:
                            # ****************decode data************************
                            binary_data_rec = mongo_server_rec.collection_data.filtered(lambda x: x.model_name == 'product.product')
                            if binary_data_rec:
                                if not request.session['product_loaded_details']:
                                    request.session['product_loaded_details'] = str(binary_data_rec[0].id)+','
                                json_data = json.loads(base64.decodebytes(binary_data_rec[0].server_data_cache).decode('utf-8'))
                                data = json_data.values()
                                return list(data)
                else:
                    mongo_server_rec.is_ordinary_loading = True
                    return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        except Exception as e:
            if self._context.get('sync_from_mongo'):
                context = self._context.copy()
                del context['sync_from_mongo']
                self.with_context(context)
            return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def create_variant_operations(self,operation,change_vals):
        if operation == 'UPDATE':
            product_operations = self.env['common.cache.notification'].search([('model_name','=',"product.product"),('record_id','=',self.id),('state','in',['error','draft'])],order="id desc")
            if not (product_operations and product_operations[0].operation == 'UPDATE'):
                self.env['common.cache.notification'].create({
                        'record_id': self.id,
                        'operation': 'UPDATE',
                        'model_name': "product.product",
                        'change_vals':change_vals,
                        'state': "draft",
                    })

        elif operation == "CREATE":
            self.env['common.cache.notification'].create({
                    'record_id': self.id,
                    'operation': 'CREATE',
                    'model_name': "product.product",
                    'change_vals':change_vals,
                    'state': "draft",
                })

        else:
            product_operations = self.env['common.cache.notification'].search([('model_name','=',"product.product"),('record_id','=',self.id),('state','in',['error','draft'])],order="id desc")
            if not (product_operations and product_operations[0].operation == 'delete'):
                self.env['common.cache.notification'].create({
                    'record_id': self.id,
                    'operation': 'DELETE',
                    'model_name': "product.product",
                    'change_vals':change_vals,
                    'state': "draft",
                })

    @api.model_create_multi
    def create(self, vals):
        res = super(ProductProduct,self).create(vals)
        for record in res:
            record.create_variant_operations('CREATE','New Product Created')
        return record


    def write(self, vals):
        res = super(ProductProduct,self).write(vals)
        vals_keys = vals.keys()
        change_vals = ','.join(vals_keys)
        vals_keys = set(vals.keys())
        fields = set(['name','display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                 'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
                 'product_tmpl_id','tracking','available_in_pos', 'active'])
        comman_fields = fields.intersection(vals_keys)
        if len(comman_fields):
            for record in self:
                if 'sale_ok' in vals.keys():
                    if not vals['sale_ok']:
                        record.create_variant_operations('DELETE',change_vals)

                    elif vals['sale_ok']:
                        if record.available_in_pos:
                            record.create_variant_operations('UPDATE',change_vals)

                elif 'sale_ok' not in vals.keys() and 'available_in_pos' in vals.keys():
                    if not vals['available_in_pos']:
                        record.create_variant_operations('DELETE',change_vals)

                    elif vals['available_in_pos']:
                        record.create_variant_operations('UPDATE',change_vals)

                elif record.sale_ok and record.available_in_pos:
                    product_operations = self.env['common.cache.notification'].search([('model_name','=',"product.product"),('record_id','=',record.id),('state','=','draft')],order="id desc")
                    if not (product_operations and product_operations[0].operation == 'UPDATE'):
                        self.env['common.cache.notification'].create({
                            'record_id': record.id,
                            'operation': "UPDATE",
                            'state': "draft",
                            'change_vals':change_vals,
                            'model_name': 'product.product',
                        })
        return res


    def unlink(self):
        for record in self:
            if record.sale_ok and record.available_in_pos:
                self.env['common.cache.notification'].create({
                    'record_id': record.id,
                    'operation': "DELETE",
                    'state': "draft",
                    'change_vals':'Product Deleted',
                    'model_name': 'product.product',
                })
        return super(ProductProduct,self).unlink()




class ProductTemplate(models.Model):
    _inherit = "product.template"


    def write(self, vals):
        res = super(ProductTemplate,self).write(vals)
        vals_keys = vals.keys()
        change_vals = ','.join(vals_keys)
        vals_keys = set(vals.keys())
        fields = set(['name','display_name', 'list_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                 'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
                 'product_tmpl_id','tracking','available_in_pos', 'active'])
        comman_fields = fields.intersection(vals_keys)
        if len(comman_fields):
            change_vals = ','.join(vals_keys)
            for record in self:
                if 'sale_ok' in vals.keys():
                    if not vals['sale_ok']:
                        for variant in record.product_variant_ids:
                            variant.create_variant_operations('DELETE',change_vals)

                    elif vals['sale_ok']:
                        if record.available_in_pos:
                            for variant in record.product_variant_ids:
                                variant.create_variant_operations('UPDATE',change_vals)

                elif 'sale_ok' not in vals.keys() and 'available_in_pos' in vals.keys():
                    if not vals['available_in_pos']:
                        for variant in record.product_variant_ids:
                            variant.create_variant_operations('DELETE',change_vals)

                    elif vals['available_in_pos']:
                        for variant in record.product_variant_ids:
                                variant.create_variant_operations('UPDATE',change_vals)

                elif record.sale_ok and record.available_in_pos:
                    for variant in record.product_variant_ids:
                        product_operations = self.env['common.cache.notification'].search([('model_name','=',"product.product"),('record_id','=',variant.id),('state','=','draft')],order="id desc")
                        if not (product_operations and product_operations[0].operation == 'UPDATE'):
                            self.env['common.cache.notification'].create({
                                'record_id': variant.id,
                                'operation': "UPDATE",
                                'state': "draft",
                                'change_vals':change_vals,
                                'model_name': 'product.product',
                            })
        return res

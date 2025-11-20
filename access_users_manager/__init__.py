# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

from . import models
from . import controllers
import openpyxl
from odoo import api, fields, models
from odoo.addons.web.controllers import export
import base64
from .controllers.access_export import InheritExportXlsxWriter

import io
import itertools
import json
import operator
from odoo.http import content_disposition, request
from odoo.tools import lazy_property, osutil, pycompat

def access_export_user_groups(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    export_id = env['ir.exports'].search([('name', '=', 'Default Template')], limit=1)
    if not export_id:
        export_id = env['ir.exports'].create({'name': 'Default Template', 'resource': 'res.groups'})
        export_fields = ['id', 'name', 'category_id/id', 'share', 'model_access/perm_create',
                         'model_access/perm_unlink',
                         'model_access/id', 'users/id', 'implied_ids/id', 'menu_access/id', 'model_access/model_id',
                         'view_access/id', 'model_access/name', 'model_access/perm_write', 'model_access/perm_read',
                         'rule_groups/id'
                         ]
        for field in export_fields:
            env['ir.exports.line'].create({'name': field, 'export_id': export_id.id})
        # export.Export.namelist(export.Export, 'res.groups', export_id.id)

        export_record = export_id.read()[0]
    export_fields_list = export_id.export_fields.read()

    fields_data = fields_info(env,
                              'res.groups', [f['name'] for f in export_fields_list])
    fields_list = [
        {'name': field['name'], 'label': fields_data[field['name']]}
        for field in export_fields_list
    ]
    data = {"import_compat": True, "context": {
        "params": {"cids": env.company.id, },
        "lang": "en_US", "tz": "Asia/Calcutta", "uid": env.user.id, "allowed_company_ids": [1]},
            "domain": [["share", "=", False]],
            "fields": fields_list, "groupby": [],
            "ids": env['res.groups'].search([]).ids, "model": "res.groups"}
    #
    response = base(env, json.dumps(data, indent=4))
    workbook = openpyxl.load_workbook(filename=io.BytesIO(response.data))
    worksheet = workbook.active
    output = io.BytesIO()
    output.seek(0)
    workbook.save(output)
    attachment = env['ir.attachment'].create({
        'name': 'Default_res_groups_export.xlsx',
        'datas': base64.b64encode(output.getvalue()),
        'mimetype': response.mimetype,
        'res_model': 'res.groups',
        'public': True
    })


def fields_info(env, model, export_fields):
    info = {}
    fields = env[model].fields_get()
    if ".id" in export_fields:
        fields['.id'] = fields.get('id', {'string': 'ID'})

    # there's a single fields_get to execute)
    for (base, length), subfields in itertools.groupby(
            sorted(export_fields),
            lambda field: (field.split('/', 1)[0], len(field.split('/', 1)))):
        subfields = list(subfields)
        if length == 2:
            # subfields is a seq of $base/*rest, and not loaded yet
            info.update(graft_subfields(env,
                                        fields[base]['relation'], base, fields[base]['string'],
                                        subfields
                                        ))
        elif base in fields:
            info[base] = fields[base]['string']

    return info


def graft_subfields(env, model, prefix, prefix_string, fields):
    export_fields = [field.split('/', 1)[1] for field in fields]
    return (
        (prefix + '/' + k, prefix_string + '/' + v)
        for k, v in fields_info(env, model, export_fields).items())


def filename(env, base):
    """ Creates a filename *without extension* for the item / format of
    model ``base``.
    """
    if base not in env:
        return base

    model_description = env['ir.model']._get(base).name
    return f"{model_description} ({base})"


def from_group_data(env, fields, groups):
    raise NotImplementedError()


def access_post_install_report_action_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    actions = env['ir.actions.actions'].search([])
    for action in actions:
        env['report.action.data'].create({'name': action.name, 'access_action_id': action.id})
    access_export_user_groups(cr, registry)


def base(env, data, indent=False):
    params = json.loads(data)
    model, fields, ids, domain, import_compat = \
        operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

    Model = env[model].with_context(import_compat=import_compat, **params.get('context', {}))
    if not Model._is_an_ordinary_table():
        fields = [field for field in fields if field['name'] != 'id']

    field_names = [f['name'] for f in fields]
    if import_compat:
        columns_headers = field_names
    else:
        columns_headers = [val['label'].strip() for val in fields]

    groupby = params.get('groupby')
    if not import_compat and groupby:
        groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
        domain = [('id', 'in', ids)] if ids else domain
        groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby,
                                       lazy=False)

        # read_group(lazy=False) returns a dict only for final groups (with actual data),
        # not for intermediary groups. The full group tree must be re-constructed.
        tree = export.GroupsTreeNode(Model, field_names, groupby, groupby_type)
        for leaf in groups_data:
            tree.insert_leaf(leaf)

        response_data = from_group_data(fields, tree)
    else:
        records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)
        # request.env = env
        export_data = records.export_data(field_names).get('datas', [])
        response_data = from_data(env, columns_headers, export_data)

    # TODO: call `clean_filename` directly in `content_disposition`?
    response = request.make_response(response_data,
                                     headers=[('Content-Disposition',
                                               content_disposition(
                                                   osutil.clean_filename(filename(env, model) + '.xlsx'))),
                                              ('Content-Type',
                                               'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')], )

    return response


def from_data(env, fields, rows):
    with InheritExportXlsxWriter(fields, len(rows), env) as xlsx_writer:
        for row_index, row in enumerate(rows):
            for cell_index, cell_value in enumerate(row):
                if isinstance(cell_value, (list, tuple)):
                    cell_value = pycompat.to_text(cell_value)
                xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

    return xlsx_writer.value

import json
import re

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import float_compare
from odoo.tools import get_lang
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from datetime import timedelta, datetime
from collections import defaultdict


class TrialBalanceCustomHandler(models.AbstractModel):
    _name = 'account.aya.trial.balance.report.handler'
    _inherit = 'account.trial.balance.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        def _update_column(line, column_key, new_value, blank_if_zero=True):
            line['columns'][column_key]['name'] = self.env['account.report'].format_value(new_value,
                                                                                          figure_type='monetary',
                                                                                          blank_if_zero=blank_if_zero)
            line['columns'][column_key]['no_format']  = new_value

        def _update_balance_columns(line, debit_column_key, credit_column_key, total_diff_values_key):
            debit_value = line['columns'][debit_column_key]['no_format']
            credit_value = line['columns'][credit_column_key]['no_format']

            if debit_value and credit_value:
                new_debit_value = 0.0
                new_credit_value = 0.0

                if float_compare(debit_value, credit_value,
                                 precision_digits=self.env.company.currency_id.decimal_places) == 1:
                    new_debit_value = debit_value - credit_value
                    total_diff_values[total_diff_values_key] += credit_value
                else:
                    new_credit_value = (debit_value - credit_value) * -1
                    total_diff_values[total_diff_values_key] += debit_value

                _update_column(line, debit_column_key, new_debit_value)
                _update_column(line, credit_column_key, new_credit_value)

        lines = [line[1] for line in
                 self.env['account.general.ledger.report.handler']._dynamic_lines_generator(report, options,
                                                                                            all_column_groups_expression_totals)]

        total_diff_values = {
            'initial_balance': 0.0,
            'end_balance': 0.0,
        }

        for line in lines[:-1]:
            # Initial balance
            res_model = report._get_model_info_from_id(line['id'])[0]
            if res_model == 'account.account':
                _update_balance_columns(line, 1, 2, 'initial_balance')

                # End balance
                _update_balance_columns(line, -2, -1, 'end_balance')

            line.pop('expand_function', None)
            line.pop('groupby', None)
            line.update({
                'unfoldable': False,
                'unfolded': False,
                'class': 'o_account_searchable_line o_account_coa_column_contrast',
            })

            res_model = report._get_model_info_from_id(line['id'])[0]
            if res_model == 'account.account':
                line['caret_options'] = 'trial_balance'

        # Total line
        if lines:
            total_line = lines[-1]
            _update_column(total_line, 1, total_line['columns'][1].get("no_format", 0)  - total_diff_values['initial_balance'],
                           blank_if_zero=False)
            _update_column(total_line, 2, total_line['columns'][2].get("no_format", 0)  - total_diff_values['initial_balance'],
                           blank_if_zero=False)
            _update_column(total_line, -2, total_line['columns'][-2].get("no_format", 0)  - total_diff_values['end_balance'],
                           blank_if_zero=False)
            _update_column(total_line, -1, total_line['columns'][-1].get("no_format", 0)  - total_diff_values['end_balance'],
                           blank_if_zero=False)

        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])

        if options['comparison']['filter'] == 'no_comparison':
            options['column_headers'][0][0]['name'] = 'Balance de Prueba entre el'
            options['column_headers'][0][1]['name'] = f'{date_from} y el {date_to}'
            del options['column_headers'][0][2]

            options['columns'][0]['name'] = 'Saldo Inicial'
            del options['columns'][1]
            del options['columns'][1]
            del options['columns'][1]
            options['columns'][1]['name'] = 'Débito'
            options['columns'][2]['name'] = 'Crédito'
            options['columns'][3]['name'] = 'Saldo Final'
            del options['columns'][4]
            del options['columns'][4]

            for line in lines:
                del line['columns'][1]
                del line['columns'][1]
                del line['columns'][1]
                del line['columns'][4]
                del line['columns'][4]

            return [(0, line) for line in lines]
        else:
            options['column_headers'][0][0]['name'] = 'Balance de Prueba, comparación'
            del options['column_headers'][0][-1]
            cant_comparison = options['comparison']['number_period']
            options['columns'][0]['name'] = 'Saldo Inicial'
            del options['columns'][1]
            del options['columns'][1]
            index = 1
            i = 0
            del_index = []
            for i in range(i, cant_comparison + 1):
                if i <= cant_comparison:
                    del options['columns'][index]
                    del_index.append(index)
                    options['columns'][index]['name'] = 'Débito'
                    options['columns'][index + 1]['name'] = 'Crédito'
                    index = index + 1
                    index += 1
                    i += 1
            options['columns'][index]['name'] = 'Saldo Final'
            del options['columns'][index + 1]
            del options['columns'][index + 1]
            for line in lines:
                del line['columns'][1]
                del line['columns'][1]
                for d in del_index:
                    del line['columns'][d]
                del line['columns'][index + 1]
                del line['columns'][index + 1]
            return [(0, line) for line in lines]

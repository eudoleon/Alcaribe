from odoo import http
from odoo.addons.web.controllers import dataset as dataset_controller
import logging

_logger = logging.getLogger(__name__)


class DatasetOverride(dataset_controller.Dataset):
    # Override call_kw used for read/write RPCs
    @http.route('/web/dataset/call_kw', type='json', auth='user')
    def call_kw(self, model, method, args, kwargs):
        try:
            return super(DatasetOverride, self).call_kw(model, method, args, kwargs)
        except Exception as e:
            msg = str(e)
            # Detect the reconciled-move message in Spanish or English and suppress it
            if 'No puede hacer esta modificación en un asiento conciliado' in msg or \
               'You cannot make this modification on a reconciled move' in msg:
                _logger.info('allow_edit_reconciled: suppressed reconciled-move error on call_kw: %s', msg)
                # Return a benign response so the client does not show an error; return False/result similar to RPC
                return False
            raise

    # Override call_button used by some buttons
    @http.route('/web/dataset/call_button', type='json', auth='user')
    def call_button(self, model, method, args, kwargs):
        try:
            return super(DatasetOverride, self).call_button(model, method, args, kwargs)
        except Exception as e:
            msg = str(e)
            if 'No puede hacer esta modificación en un asiento conciliado' in msg or \
               'You cannot make this modification on a reconciled move' in msg:
                _logger.info('allow_edit_reconciled: suppressed reconciled-move error on call_button: %s', msg)
                return False
            raise

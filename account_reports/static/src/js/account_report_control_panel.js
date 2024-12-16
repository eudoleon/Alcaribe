odoo.define('account_reports.AccountReportControlPanel', function (require) {
    "use strict";

    const ControlPanel = require('web.ControlPanel');

    class AccountReportControlPanel extends ControlPanel {
        _attachAdditionalContent() {
            super._attachAdditionalContent();
            if ("default_filter_accounts" in (this.env.searchModel.config.context || {})) {
                $('.o_searchview_input').val(this.env.searchModel.config.context.default_filter_accounts).trigger("input");
            }
        }
    };

    return AccountReportControlPanel;
});

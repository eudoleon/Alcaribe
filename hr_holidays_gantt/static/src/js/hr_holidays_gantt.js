odoo.define("hr_holidays_gantt.holidays_gantt", function(require) {
    'use strict';

    var GanttView = require("hr_gantt.GanttView");
    var GanttController = require("web_gantt.GanttController");
    var viewRegistry = require("web.view_registry");

    var HolidaysGanttController = GanttController.extend({
        _onCellAddClicked: function(ev) {
            ev.stopPropagation();
            const context = this._getDialogContext(ev.data.date, ev.data.rowId);
            for (const k in context) {
                context[`default_${k}`] = context[k];
            }
            context["default_request_date_from"] = ev.data.date._i;
            context["default_request_date_to"] = ev.data.date._i;
            this._onCreate(context);
        },
    });

    var HolidaysGanttView = GanttView.extend({
        config: _.extend({}, GanttView.prototype.config, {
            Controller: HolidaysGanttController,
        }),
    });

    viewRegistry.add("hr_holidays_gantt", HolidaysGanttView);

    return HolidaysGanttController;

});

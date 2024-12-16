odoo.define('hr_work_entry_contract_enterprise.work_entries_gantt', function(require) {
    'use strict';

    var WorkEntryControllerMixin = require('hr_work_entry_contract.WorkEntryControllerMixin');
    var GanttView = require('web_gantt.GanttView');
    var GanttController = require('web_gantt.GanttController');
    var viewRegistry = require('web.view_registry');


    var WorkEntryGanttController = GanttController.extend(WorkEntryControllerMixin, {
        events: _.extend({}, WorkEntryControllerMixin.events, GanttController.prototype.events),


        _renderButtonsQWeb: function() {
            return this._super.apply(this, arguments).append(this._renderWorkEntryButtons());
        },
        _fetchRecords: function () {
            return this.model.ganttData.records;
        },
        _fetchFirstDay: function () {
            return this.model.ganttData.startDate;
        },
        _fetchLastDay: function () {
            return this.model.ganttData.stopDate;
        },
        _displayWarning: function ($warning) {
            this.$('.o_gantt_view').before($warning);
        },

        _onCellAddClicked: function(ev) {
            ev.stopPropagation();
            const context = this._getDialogContext(ev.data.date, ev.data.rowId);
            for (const k in context) {
                context[_.str.sprintf('default_%s', k)] = context[k];
            }
            const date_obj = new Date(context['default_date_stop']);
            date_obj.setHours(9,0,0)
            context['default_date_start'] = date_obj.toISOString().replace(/T|Z/g, ' ').trim().substring(0, 19);
            date_obj.setHours(17,0,0)
            context['default_date_stop'] = date_obj.toISOString().replace(/T|Z/g, ' ').trim().substring(0, 19);
            this._onCreate(context);
        },

        _onAddClicked(ev) {
            ev.preventDefault();
            const context = {};
            const state = this.model.get();
            const today = new Date();
            today.setHours(9,0,0);
            context[state.dateStartField] = today.toISOString().replace(/T|Z/g, ' ').trim().substring(0, 19);
            today.setHours(17,0,0);
            context[state.dateStopField] = today.toISOString().replace(/T|Z/g, ' ').trim().substring(0, 19);
            for (const k in context) {
                context[_.str.sprintf('default_%s', k)] = context[k];
            }
            this._onCreate(context);
        }
    });

    var WorkEntryGanttView = GanttView.extend({
        config: _.extend({}, GanttView.prototype.config, {
            Controller: WorkEntryGanttController,
        }),
    });

    viewRegistry.add('work_entries_gantt', WorkEntryGanttView);

    return WorkEntryGanttController;

});

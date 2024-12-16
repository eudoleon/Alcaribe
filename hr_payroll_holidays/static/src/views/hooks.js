/** @odoo-module **/

import { Component, useState, useEffect, useEnv, onWillStart, mount, useRef } from "@odoo/owl";

import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class TimeOffToDeferWarning extends Component {
    setup() {
        this.actionService = useService("action");
    }

    get timeOffButtonText() {
        const [, before, inside, after] =
            _t("You have some <button>time off</button> to defer to the next month.").match(
                /(.*)<button>(.*)<\/button>(.*)/
            ) || [];
        return { before, inside, after };
    }

    onTimeOffToDefer() {
        this.actionService.doAction("hr_payroll_holidays.hr_leave_action_open_to_defer");
    }
};

TimeOffToDeferWarning.template = "hr_payroll_holidays.TimeOffToDeferWarning";

export function useTimeOffToDefer(selector, position) {
    const orm = useService("orm");
    const user = useService("user");
    const rootRef = useRef("root");
    const env = useEnv();
    const state = useState({
        hasTimeOffToDefer: false
    });
    onWillStart(async () => {
        const result = await orm.searchCount('hr.leave', [["payslip_state", "=", "blocked"], ["state", "=", "validate"], ["employee_company_id", "in", user.context.allowed_company_ids]]);
        state.hasTimeOffToDefer = result > 0;
    });
    useEffect((el) => {
        if (!el) {
          return;
        }
        const attachElement = el.querySelector(selector);
        mount(TimeOffToDeferWarning, attachElement, {
            position,
            env,
            templates,
        });
      },
      () => [state.hasTimeOffToDefer && rootRef.el]
    )
}

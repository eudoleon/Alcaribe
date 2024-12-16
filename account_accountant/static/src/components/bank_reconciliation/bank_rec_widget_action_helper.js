/** @odoo-module **/

import { RainbowMan } from "@web/core/effects/rainbow_man";
import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillDestroy } from "@odoo/owl";

export class BankRecFinishButtons extends Component {
    getJournalFilter() {
        // retrieves the searchModel's searchItem for the journal
        return Object.values(this.env.searchModel.searchItems).filter(i => i.type == "field" && i.fieldName == "journal_id")[0];
    }

    get breadcrumbs() {
        return this.env.config.breadcrumbs;
    }

    get otherFiltersActive() {
        const facets = this.env.searchModel.facets;
        const journalFilterItem = this.getJournalFilter();
        for (const facet of facets) {
            if (facet.groupId !== journalFilterItem.groupId) {
                return true;
            }
        }
        return false;
    }

    clearFilters() {
        const facets = this.env.searchModel.facets;
        const journalFilterItem = this.getJournalFilter();
        for (const facet of facets) {
            if (facet.groupId !== journalFilterItem.groupId) {
                this.env.searchModel.deactivateGroup(facet.groupId);
            }
        }
    }

    breadcrumbBackOrDashboard() {
        if (this.breadcrumbs.length > 1) {
            this.env.services.action.restore();
        } else {
            this.env.services.action.doAction("account.open_account_journal_dashboard_kanban", {clearBreadcrumbs: true});
        }
    }
}
BankRecFinishButtons.template = "account_accountant.bankRecFinishButtons";

export class BankRecWidgetRainbowMessage extends Component {
    setup() {
        this.bankRecService = useService("bank_rec_widget");
        onWillDestroy(() => this.bankRecService.initReconCounter());
    }

    get counterSummary() {
        const counterData = this.bankRecService.reconciliationCounter;
        const diff = counterData.timeDiff;
        const diffInSeconds = diff.seconds;
        let units = ["seconds"];
        if (diffInSeconds > 60) {
            units.unshift("minutes");
        }
        if (diffInSeconds > 3600) {
            units.unshift("hours");
        }
        return {
            ...counterData,
            secondsPerTransaction: Math.round(diffInSeconds / counterData.reconciledCount),
            formattedDuration: diff.toFormat(localization.timeFormat.replace(/HH/, "hh")),
            humanDuration: diff.shiftTo(...units).toHuman(),
        }
    }
}
BankRecWidgetRainbowMessage.template = "account_accountant.rainbowMessage";
BankRecWidgetRainbowMessage.components = {
    BankRecFinishButtons,
}

export class BankRecActionHelper extends Component {
    setup(){
        this.bankRecService = useService("bank_rec_widget");
    }

    get showRainbow() {
        return this.bankRecService.reconciliationCounter.reconciledCount > 0;
    }

    get rainbowProps() {
        return {
            imgUrl: "/web/static/img/smile.svg",
            Component: BankRecWidgetRainbowMessage,
            close: ()=>{},
        }
    }
}
BankRecActionHelper.template = "account_accountant.BankRecActionHelper";
BankRecActionHelper.components = {
    RainbowMan,
    BankRecFinishButtons,
}

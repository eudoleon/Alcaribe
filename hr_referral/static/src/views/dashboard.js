/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useEffect, useState, useRef } = owl;

export class HrReferralWelcome extends Component {
    setup() {
        super.setup();

        this.actionService = useService("action");
        this.orm = useService('orm');

        this.dashboardData = useState({});

        this.isDebug = odoo.debug;

        this.state = useState({ reachedEnd: false });
        this.carouselRef = useRef("carousel");
        useEffect((el) => {
            el && el.addEventListener('slide.bs.carousel', this.onNextSlide.bind(this));

            return () => {
                el && el.removeEventListener('slide.bs.carousel', this.onNextSlide.bind(this));
            }
        }, () => [this.carouselRef.el]);

        const context = Component.env.session.user_context;

        onWillStart(async () => {
            Object.assign(this.dashboardData, await this.orm.call(
                'hr.applicant',
                'retrieve_referral_welcome_screen',
                [],
                {'context': context}));
            this.dashboardData.company_id = context.allowed_company_ids[0];
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    onNextSlide(e) {
        this.state.reachedEnd = e.to == this.onboardingLength - 1;
    }

    get onboardingLength() {
        return this.dashboardData.onboarding && this.dashboardData.onboarding.length;
    }

    get applicantId() {
        return this.dashboardData.new_friend_id;
    }

    /**
     * @private
     * @param {MouseEvent} e
     */
    async _onMessageDismissClicked(event, message_id) {
        await this.orm.call('hr.referral.alert', 'action_dismiss', [message_id]);
        this.dashboardData.message = this.dashboardData.message.filter(message => message.id !== message_id);
    }

    /**
     * Save that user has seen the onboarding screen then restart the view
     *
     * @private
     * @param {MouseEvent} e
     */
    async _completeOnboarding(completed) {
        await this.orm.call('res.users', 'action_complete_onboarding', [completed]);
        this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'hr_referral_welcome',
            name: this.env._t('Dashboard'),
            target: 'main'
        });
    }

    /**
     * User upgrade his level then restart the view
     *
     * @private
     * @param {MouseEvent} e
     */
    async _upgradeLevel(e) {
        await this.orm.call('hr.applicant', 'upgrade_level', []);
        this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'hr_referral_welcome',
            name: this.env._t('Dashboard'),
            target: 'main'
        });
    }

    /**
     * Save the new user's friend then restart the view
     *
     * @private
     * @param {MouseEvent} e
     */
    async _chooseFriend(friendId) {
        await this.orm.call('hr.applicant', 'choose_a_friend', [[this.applicantId], friendId]);
        this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'hr_referral_welcome',
            name: this.env._t('Dashboard'),
            target: 'main'
        });
    }

}

HrReferralWelcome.template = 'hr_referral.Welcome';

registry.category('actions').add('hr_referral_welcome', HrReferralWelcome);

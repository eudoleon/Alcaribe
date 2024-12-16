/* @odoo-module */

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start, startServer } from "@mail/../tests/helpers/test_utils";

import { getFixture } from "@web/../tests/helpers/utils";
import { click, contains, insertText, scroll } from "@web/../tests/utils";

QUnit.module("mail_enterprise", {}, function () {
QUnit.module("widgets", {}, function () {
QUnit.module("form_renderer_tests.js", {
    beforeEach() {
        patchUiSize({ size: SIZES.XXL });
    },
});

QUnit.test("Message list loads new messages on scroll", async function () {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        display_name: "Partner 11",
        description: [...Array(60).keys()].join("\n"),
    });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: resPartnerId1,
        });
    }
    const views = {
        "res.partner,false,form": `<form string="Partners">
        <sheet>
            <field name="name"/>
            <field name="description"/>
        </sheet>
        <div class="oe_chatter">
            <field name="message_ids" />
        </div>
    </form>`,
    };
    const target = getFixture();
    target.classList.add("o_web_client");
    const { openFormView } = await start({ serverData: { views }, target });
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message", { count: 30 });
    await scroll(".o_Chatter_scrollPanel", "bottom");
    await contains(".o_Message", { count: 60 });
});

QUnit.test("Message list is scrolled to new message after posting a message", async function () {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        activity_ids: [],
        display_name: "Partner 11",
        description: [...Array(60).keys()].join("\n"),
        message_ids: [],
        message_follower_ids: [],
    });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: resPartnerId1,
        });
    }
    const views = {
        "res.partner,false,form": `<form string="Partners">
            <header>
                <button name="primaryButton" string="Primary" type="object" class="oe_highlight" />
            </header>
            <sheet>
                <field name="name"/>
                <field name="description"/>
            </sheet>
            <div class="oe_chatter">
                <field name="message_ids" options="{'post_refresh': 'always'}"/>
            </div>
        </form>`,
    };
    const target = getFixture();
    target.classList.add("o_web_client");
    const { openFormView } = await start({ serverData: { views }, target });
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message", { count: 30 });
    await contains(".o_FormRenderer_chatterContainer.o-aside");
    await contains(".o_content", { scroll: 0 });
    await contains(".o_Chatter_scrollPanel", { scroll: 0 });
    await scroll(".o_Chatter_scrollPanel", "bottom");
    await contains(".o_Message", { count: 60 });
    await contains(".o_content", { scroll: 0 });
    await click("button", { text: "Log note" });
    await insertText(".o_ComposerTextInput_textarea", "New Message");
    await click("button:enabled", { text: "Log" });
    await contains(".o_ComposerTextInput_textarea", { count: 0 });
    await contains(".o_Message", { count: 61 });
    await contains(".o_Message_content", { text: "New Message" });
    await contains(".o_content", { scroll: 0 });
    await contains(".o_Chatter_scrollPanel", { scroll: 0 });
});
});
});

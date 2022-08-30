odoo.define("3mit.dialog", function (require) {
  "use strict";

  var config = require("web.config");
  var core = require("web.core");
  var Dialog = require("web.Dialog");
  var _t = core._t;

  var SelectionDialog = Dialog.extend({
    template: "3mit.SelectionDialog",
    events: _.extend({}, Dialog.prototype.events, {
      "click .selection-item": "click_item",
    }),
    init: function (parent, list, options) {
      // set the field name because key will be lost after sorting dict
      this.list = list || [];

      var opts = {
        buttons: [
          {
            text: _t("Cancel"),
            click: options && options.cancel_callback,
            close: true,
          },
        ],
        onForceClose:
          options && (options.onForceClose || options.cancel_callback),
        ...options,
      };

      this.confirm_callback = options.confirm_callback;

      this._super(parent, opts);
    },

    is_selected(item) {
      return false;
    },
    click_item(evt) {
      const value = $(evt.target).attr("data-item-value");
      var selectedItem = this.list.find((r) => r.item == value);
      if (this.confirm_callback) {
        this.confirm_callback(selectedItem);
      }

      this.onForceClose = false;
      this.close();
    },
  });

  ////
  var PromptDialog = Dialog.extend({
    template: "3mit.PromptDialog",
    init: function (parent, options) {
      this.body = (options && options.body) || null;
      this.value = (options && options.value) || null;
      this.html = (options && options.html) || false;
      this.confirm_callback = options && options.confirm_callback;
      var opts = {
        buttons: [
          {
            text: _t("Ok"),
            classes: "btn-primary",
            close: true,
            click: this._onClick,
          },
          {
            text: _t("Cancel"),
            close: true,
            click: options && options.cancel_callback,
          },
        ],
        ...options,
      };

      this._super(parent, opts);
    },
    renderElement: function () {
      this._super();
      this.$("div[name=body]").html(this.body);
      this.$("input").focus();
    },
    _onClick() {
      if (this.confirm_callback) {
        const val = this.$("input").val();
        this.confirm_callback(val);
      }

      this.onForceClose = false;
      this.close();
    },
  });

  var AlertDialog = Dialog.extend({
    template: "3mit.AlertDialog",
    init: function (parent, options) {
      this.body = (options && options.body) || null;
      this.confirm_callback = options && options.confirm_callback;

      var buttons = [
        {
          text: _t("Ok"),
          classes: "btn-primary",
          close: true,
          click: this.confirm_callback,
        },
      ];
      if (options.print) {
        buttons = [
          {
            text: _t("Print"),
            classes: "btn-primary",
            close: true,
            click: this.print,
          },
          {
            text: _t("Ok"),
            classes: "btn-secondary",
            close: true,
            click: this.confirm_callback,
          },
        ];
      }

      var opts = {
        buttons,
        ...options,
      };

      this._super(parent, opts);
    },
    renderElement: function () {
      this._super();
      this.$("div[name=body]").html(this.body);
    },
    print() {
      var printContents = this.$("div[name=body]").html();
      var $body = $("#__print__").contents().find("body");
      $body.html(printContents);
      window.frames["__print__"].print();
    },
  });

  return {
    confirm: Dialog.confirm,

    selection: function (owner, list, options) {
      const dialog = new SelectionDialog(this, list, options).open();
      return dialog;
    },

    prompt: function (owner, options) {
      const dialog = new PromptDialog(this, options).open();
      return dialog;
    },

    alert: function (owner, options) {
      const dialog = new AlertDialog(this, options).open();
      return dialog;
    },
  };
});

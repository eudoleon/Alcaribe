/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_fast_loading.chrome", function (require) {
  "use strict";

  var models = require("point_of_sale.models");
  var rpc = require("web.rpc");
  var session = require("web.session");
  // var model_list = models.PosModel.prototype.models;
  var product_model = null;
  var partner_model = null;
  var pricelist_item_model = null;
  const PosComponent = require("point_of_sale.PosComponent");
  const Registries = require("point_of_sale.Registries");
  var utils = require("web.utils");
  var round_pr = utils.round_precision;

  class SynchNotificationWidget extends PosComponent {
    setup() {
      super.setup();
      owl.onMounted(this.onMounted);
    }
    onMounted() {
      var self = this;
      self.interval_id = false;
      if (!self.env.pos.config.enable_pos_longpolling) {
        if (
          self.env.pos.db.mongo_config &&
          self.env.pos.db.mongo_config.pos_live_sync == "notify"
        )
          $(".session_update").show();
        if (
          !self.interval_id &&
          self.env.pos.db &&
          self.env.pos.db.mongo_config &&
          self.env.pos.db.mongo_config.pos_live_sync != "reload"
        ) {
          self.start_cache_polling();
        }
      }
      if (self.env.pos.db.mongo_config) {
        setTimeout(() => {
          $(".session_update").click();
        }, 1000);
      }
    }

    _onClickSessionUpdate() {
      var self = this;
      rpc
        .query({
          method: "get_data_on_sync",
          model: "mongo.server.config",
          args: [
            {
              config_id: self.env.pos.config.id,
              mongo_cache_last_update_time:
                self.env.pos.db.mongo_config.cache_last_update_time,
            },
          ],
        })
        .then(function (res) {
          if (
            self.env.pos.db &&
            self.env.pos.db.mongo_config &&
            self.env.pos.db.mongo_config.pos_live_sync != "reload"
          )
            self.post_rechecking_process(res);
          self.render();
        })
        .catch(function (error, event) {
          if (event && event.preventDefault) event.preventDefault();
          $(".session_update .fa-refresh").css({
            color: "rgb(94, 185, 55)",
          });
        });
    }
    start_cache_polling() {
      var self = this;
      if (!self.interval_id)
        self.interval_id = setInterval(function () {
          if (self.env.pos.config.id) {
            setTimeout(function () {
              $.unblockUI();
            }, 3000);
            return session
              .rpc("/cache/notify", {
                mongo_cache_last_update_time:
                  self.env.pos.db.mongo_config.cache_last_update_time,
                config_id: self.env.pos.config.id,
              })
              .then(function (result) {
                if (result.sync_method == "reload") {
                  clearInterval(self.interval_id);
                  self.interval_id = false;
                } else {
                  if (result.is_data_updated) {
                    $(".session_update .fa-refresh").css({
                      color: "rgb(94, 185, 55)",
                    });
                  } else {
                    if (result.sync_method == "notify") {
                      $(".session_update .fa-refresh").css({
                        color: "#ff5656",
                      });
                      clearInterval(self.interval_id);
                      self.interval_id = false;
                    } else if (result.sync_method == "realtime") {
                      $(".session_update .fa-refresh").css({
                        color: "#ff5656",
                      });
                      if (result.data) {
                        self.post_rechecking_process(result.data);
                      }
                    }
                  }
                }
              });
          }
        }, 5000);
    }

    post_rechecking_process(res) {
      var self = this;
      if (res) {
        self.env.pos.db.mongo_config.cache_last_update_time = res.mongo_config;
        var products = res.products || false;
        var partners = res.partners || false;
        var price_deleted_record_ids = res.price_deleted_record_ids || false;
        var partner_deleted_record_ids =
          res.partner_deleted_record_ids || false;
        var product_deleted_record_ids =
          res.product_deleted_record_ids || false;
        var pricelist_items = res.pricelist_items || false;

        if (!self.env.pos.config.enable_pos_longpolling) {
          // *********************Adding and Updating the Products*******************************

          self.updatePosProducts(products, product_deleted_record_ids);

          // *********************Adding and Updating Pricelist Item to pos*********************

          // self.updatePricePos(pricelist_items, price_deleted_record_ids);

          // *********************Adding and Updating Partner to pos*********************

          self.updatePartnerPos(partners, partner_deleted_record_ids);
        }

        // ************************ Partners deleted from indexedDB***************************
        self.env.pos.updatePartnerIDB(partners, partner_deleted_record_ids);

        // **********************Updating Time In IndexedDB************************************

        self.updateCacheTimeIDB();

        // *********** Pricelist item Deleted and Updated from indexedDB**********************

        // self.updatePriceIDB(pricelist_items, price_deleted_record_ids);

        // ***********Products deleted from indexedDB*****************************************

        self.env.pos.updateProductsIDB(products, product_deleted_record_ids);

        // ***********************************************************************************
        if (!self.env.pos.config.enable_pos_longpolling) {
          $(".session_update .fa-refresh").css({
            color: "rgb(94, 185, 55)",
          });
          if (!self.interval_id) {
            self.start_cache_polling();
          }
        }
      } else {
        console.log("product not updated");
      }
    }
    

    

    update_partner_screen() {
      if ($(".load-customer-search").length) $(".load-customer-search").click();
    }
    delete_partner(partner_id) {
      var self = this;
      var partner_sorted = self.db.partner_sorted;
      var data = self.db.get_partner_by_id(partner_id);
      if (data.barcode) {
        delete self.db.partner_by_barcode[data.barcode];
      }
      // remove one element at specified index
      partner_sorted.splice(_.indexOf(partner_sorted, partner_id), 1);
      delete self.db.partner_by_id[partner_id];
      console.log(
        "############ Deleted partner (id :: %s )  ###########)",
        partner_id
      );
      self.update_partner_screen();
    }

    updatePartnerPos(partners, partner_deleted_record_ids) {
      var self = this;
      if (partners) self.env.pos.db.add_partners(partners);
      if (partner_deleted_record_ids && partner_deleted_record_ids.length) {
        console.log("######## deleting partner ##############");
        _.each(partner_deleted_record_ids, function (partner_id) {
          self.delete_partner(partner_id);
        });
      }
    }

    updatePosProducts(products, product_deleted_record_ids) {
      var self = this;
      if (products && products.length) {
        _.each(products, function (product) {
          if (product.id in self.env.pos.db.product_by_id) {
            delete self.env.pos.db.product_by_id[product.id];
          }
        });
        self.env.pos._loadProductProduct(products);
        self.showScreen("PartnerListScreen");
        self.showScreen("ProductScreen");
        //---------------------------------------------
        if (self.env.pos && self.env.pos.get_order()) {
          var order = self.env.pos.get_order();
          if (
            order.get_screen_data() &&
            order.get_screen_data().name == "ProductScreen"
          ) {
            self.showScreen("PartnerListScreen");
            self.showScreen("ProductScreen");
          }
        }
        //-----
      }

      if (product_deleted_record_ids && product_deleted_record_ids.length) {
        _.each(product_deleted_record_ids, function (record) {
          var temp = self.env.pos.db.product_by_id;
          var product = temp[record];
          var categ_search_string = self.env.pos.db._product_search_string(
            product
          );
          var new_categ_string_list = [];
          _.each(self.env.pos.db.category_search_string, function (
            categ_string
          ) {
            if (categ_string.indexOf(categ_search_string) != -1) {
              var regEx = new RegExp(categ_search_string, "g");
              var remove_string = categ_string.replace(regEx, "");
              new_categ_string_list.push(remove_string);
            } else new_categ_string_list.push(categ_string);
          });
          self.env.pos.db.category_search_string = new_categ_string_list;
          delete temp[record];
          self.env.pos.db.product_by_id = temp;
          var new_categ_list = [];
          var categories = self.env.pos.db.product_by_category_id;
          _.each(categories, function (categ) {
            var deleted_element_index = categ.indexOf(record);
            var new_list = categ.splice(deleted_element_index, 1);
            new_categ_list.push(categ);
          });
          self.env.pos.db.product_by_category_id = new_categ_list;
        });
      }
    }

    updateCacheTimeIDB() {
      var self = this;
      if (!("indexedDB" in window)) {
        console.log("This browser doesn't support IndexedDB");
      } else {
        var request = window.indexedDB.open("cacheDate", 1);
        request.onsuccess = function (event) {
          var db = event.target.result;
          if (db.objectStoreNames.contains("last_update")) {
            var transaction = db.transaction("last_update", "readwrite");
            var itemsStore = transaction.objectStore("last_update");
            var dateDataStore = itemsStore.get("time");
            dateDataStore.onsuccess = function (event) {
              var req = event.target.result;
              req = {
                id: "time",
                time: self.env.pos.db.mongo_config.cache_last_update_time,
              };
              var requestUpdate = itemsStore.put(req);
            };
          }
        };
      }
    }

    

    updatePriceIDB(pricelist_items, price_deleted_record_ids) {
      var self = this;
      if ("indexedDB" in window) {
        if (
          (pricelist_items && pricelist_items.length) ||
          (price_deleted_record_ids && price_deleted_record_ids.length)
        ) {
          var request = window.indexedDB.open("Items", 1);
          request.onsuccess = function (event) {
            var db = event.target.result;
            var transaction = db.transaction("items", "readwrite");
            var itemsStore = transaction.objectStore("items");
            if (price_deleted_record_ids && price_deleted_record_ids.length)
              price_deleted_record_ids.forEach(function (id) {
                var data_store = itemsStore.get(id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  var requestUpdate = itemsStore.delete(id);
                };
              });
            if (pricelist_items && pricelist_items.length)
              pricelist_items.forEach(function (item) {
                var data_store = itemsStore.get(item.id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  data = item;
                  var requestUpdate = itemsStore.put(data);
                };
              });

            //---------------------------------------------
            if (self.env.pos && self.env.pos.get_order()) {
              var order = self.env.pos.get_order();
              var pricelist = order.pricelist;
              order.set_pricelist(pricelist);
              if (
                order.get_screen_data() &&
                order.get_screen_data().name == "ProductScreen"
              ) {
                self.showScreen("PartnerListScreen");
                self.showScreen("ProductScreen");
              }
            }
            //---------------------------------------------
          };
        }
      }
    }

    

    updatePricePos(pricelist_items, price_deleted_record_ids) {
      var self = this;
      var delete_price_data = [];
      if (
        (pricelist_items && pricelist_items.length) ||
        (price_deleted_record_ids && price_deleted_record_ids.length)
      ) {
        var pricelist_items_by_pricelist_id = {};
        _.each(pricelist_items, function (item) {
          if (item.pricelist_id[0] in pricelist_items_by_pricelist_id)
            pricelist_items_by_pricelist_id[item.pricelist_id[0]].push(item);
          else pricelist_items_by_pricelist_id[item.pricelist_id[0]] = [item];
        });
        _.each(price_deleted_record_ids, function (item) {
          delete_price_data.push(pricelist_items_by_pricelist_id);
        });
        _.each(self.env.pos.pricelists, function (pricelist) {
          var new_pricelist_items = [];
          _.each(pricelist.items, function (item) {
            if (price_deleted_record_ids.indexOf(item.id) == -1)
              new_pricelist_items.push(item);
          });
          if (pricelist_items_by_pricelist_id[pricelist.id]) {
            var pricelist_new_items = new_pricelist_items.concat(
              pricelist_items_by_pricelist_id[pricelist.id]
            );
            pricelist.items = pricelist_new_items;
          } else pricelist.items = new_pricelist_items;
        });
      }
    }
  }

  SynchNotificationWidget.template = "SynchNotificationWidget";

  Registries.Component.add(SynchNotificationWidget);
});

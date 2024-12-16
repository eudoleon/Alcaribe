/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_fast_loading.models", function (require) {
  "use strict";

  // var models = require('point_of_sale.models');
  // var model_list = models.PosModel.prototype.models;
  const {
    PosGlobalState,
    Order,
    Orderline,
    Payment,
  } = require("point_of_sale.models");
  const Registries = require("point_of_sale.Registries");
  var PosDB = require("point_of_sale.DB");
  var utils = require("web.utils");

  const MongoServerConfigPosGlobalState = (PosGlobalState) =>
    class MongoServerConfigPosGlobalState extends PosGlobalState {
      //@override to add the pos context
      async load_server_data() {
        var self = this;
        self.product_loaded_using_index = false;
        self.partner_loaded_using_index = false;
        // var context = await self.update_required_context();
        // const loadedData = await this.env.services.rpc({
        //   model: "pos.session",
        //   method: "load_pos_data",
        //   args: [[odoo.pos_session_id]],
        //   kwargs: { context: context },
        // });
        // await this._processData(loadedData);
        await super.load_server_data(...arguments);
      }
      //@override
      async _processData(loadedData) {
        await super._processData(loadedData);
        await this.db._loadMongoServerConfig(loadedData["mongo.server.config"]);
        if (!("indexedDB" in window)) {
          console.log("This browser doesn't support IndexedDB");
          this._loadProductProduct(loadedData["product.product"]);
          this.partners = loadedData["res.partner"];
          this.addPartners(this.partners);
          // this.pricelists = loadedData["product.pricelist"];
        } else {
          this.custom_product_load(loadedData["product.product"]);
          this.custom_partner_load(loadedData["res.partner"]);
          // this.custom_pricelist_load(loadedData["product.pricelist"]);
        }
      }

      send_current_order_to_customer_facing_display() {
        var self = this;
        if (self.config) {
          super.send_current_order_to_customer_facing_display();
        }
      }

      async update_required_context() {
        var self = this;
        var context = {};
        var data = [];
        var request = window.indexedDB.open("cacheDate", 1);
        request.onsuccess = async function (event) {
          var db = event.target.result;
          if (db.objectStoreNames.contains("last_update")) {
            var res = await getRecordsIndexedDB(db, "last_update");
            context["sync_from_mongo"] = true;
            context["is_indexed_updated"] = res;
            return context;
          }
        };
        request.onupgradeneeded = function (event) {
          var db = event.target.result;
          var itemsStore = db.createObjectStore("last_update", {
            keyPath: "id",
          });
        };
        if (!context.length) {
          context["sync_from_mongo"] = true;
          data.push(JSON.parse(localStorage.getItem("cache_last_update")));
          context["is_indexed_updated"] = data;
        }
        return context;
      }
      async loadRemCustomersFast() {
        let partners = [];
        let page = 1;
        var self = this;
        $.blockUI({
          message:
            '<h1 style="color:rgb(220, 236, 243);"><i class="fa fa-spin fa-spinner"></i> Loading Remaining Customers...</h1>',
        });
        do {
          partners = await this.env.services.rpc(
            {
              model: "mongo.server.config",
              method: "load_rem_customer",
              args: [
                ,
                {
                  page: page,
                },
              ],
            },
            { shadow: true }
          );
          if (partners) {
            // const batches = _.chunk(partners, 500);
            // var temp = batches.length;
            // batches.forEach(function(items){
            //   console.log("###### loading partners in batches ########", temp);
            // self.env.pos.addPartners(items);
            // self.updatePartnerIDB(items);
            // temp -= 1;
            // })
            self.addPartners(partners);
            self.updatePartnerIDB(partners);
          }
          page += 1;
        } while (partners.length);
        $.unblockUI();
      }

      async loadRemProductsFast() {
        let products = [];
        let page = 1;
        var self = this;
        $.blockUI({
          message:
            '<h1 style="color:rgb(220, 236, 243);"><i class="fa fa-spin fa-spinner"></i> Loading Remaining Products...</h1>',
        });
        do {
          products = await this.env.services.rpc(
            {
              model: "mongo.server.config",
              method: "load_rem_product",
              args: [
                ,
                {
                  page: page,
                },
              ],
            },
            { shadow: true }
          );
          if (products) {
            self._loadProductProduct(products);
            self.updateProductsIDB(products);
          }
          page += 1;
        } while (products.length);
        $.unblockUI();
      }

      custom_product_load(products) {
        var self = this;
        self.db.product_loaded = false;
        if (products.length) {
          _.each(products, function (obj) {
            obj.pos = self;
          });
          self._loadProductProduct(products);
          self.loadRemProductsFast();
          console.log("product loaded through default...........");
        }

        var request = window.indexedDB.open("Product", 1);
        request.onsuccess = function (event) {
          var db = event.target.result;
          if (!products.length) {
            getRecordsIndexedDB(db, "products").then(function (res) {
              $.blockUI({
                message:
                  '<h1 style="color:rgb(220, 236, 243);"><i class="fa fa-spin fa-spinner"></i> Product Loading...</h1>',
              });
              _.each(res, function (obj) {
                obj.pos = self;
              });
              self._loadProductProduct(res);
              self.product_loaded_using_index = true;
              console.log("product loaded through indexdb...........");
              $.unblockUI();
            });
          } else {
            if (db.objectStoreNames.contains("products")) {
              try {
                var product_transaction = db.transaction(
                  "products",
                  "readwrite"
                );

                var productsStore = product_transaction.objectStore("products");

                /*************************************/
                products.forEach(function (product) {
                  var data_store = productsStore.get(product.id);
                  data_store.onsuccess = function (event) {
                    var data = event.target.result;
                    data = product;
                    delete data["pos"];
                    delete data["applicablePricelistItems"];
                    productsStore.put(data);
                  };
                });
              } catch {
                console.log("----exception---- products");
              }
            }
          }
        };
        request.onupgradeneeded = function (event) {
          var db = event.target.result;
          var productsStore = db.createObjectStore("products", {
            keyPath: "id",
          });
        };
      }

      custom_partner_load(partners) {
        var self = this;
        if (partners.length) {
          self.partners = partners;
          self.addPartners(partners);
          console.log("partners loaded through default...........");
          self.loadRemCustomersFast();
        }
        var request = window.indexedDB.open("Partners", 1);
        request.onsuccess = function (event) {
          var db = event.target.result;
          if (!partners.length) {
            getRecordsIndexedDB(db, "partners").then(function (res) {
              self.partners = res;
              self.addPartners(res);
            });
            self.partner_loaded_using_index = true;
            console.log("partners loaded through indexdb...........");
          } else {
            if (db.objectStoreNames.contains("partners")) {
              try {
                var transaction = db.transaction("partners", "readwrite");
                var partnersStore = transaction.objectStore("partners");
                /*************************************/
                partners.forEach(function (partner) {
                  var data_store = partnersStore.get(partner.id);
                  data_store.onsuccess = function (event) {
                    var data = event.target.result;
                    data = partner;
                    var requestUpdate = partnersStore.put(data);
                  };
                });
              } catch {
                console.log("--- exception --- partners");
              }
            }
          }
        };
        request.onupgradeneeded = function (event) {
          var db = event.target.result;
          var partnersStore = db.createObjectStore("partners", {
            keyPath: "id",
          });
        };

        // **********date*******
        var date_request = window.indexedDB.open("cacheDate", 1);
        date_request.onupgradeneeded = function (event) {
          var db = event.target.result;
          var lastUpdateTimeStore = db.createObjectStore("last_update", {
            keyPath: "id",
          });
        };
        date_request.onsuccess = function (event) {
          var date_db = event.target.result;
          try {
            var time_transaction = date_db.transaction(
              "last_update",
              "readwrite"
            );
            var lastTimeStore = time_transaction.objectStore("last_update");
            var last_date_store = lastTimeStore.get("time");
            last_date_store.onsuccess = function (event) {
              var data = event.target.result;
              data = {
                id: "time",
                time: self.db.mongo_config
                  ? self.db.mongo_config.cache_last_update_time
                  : undefined,
              };
              var last_updated_time = lastTimeStore.put(data);
              localStorage.setItem("cache_last_update", JSON.stringify(data));
            };
          } catch {
            console.log("-----exception---- last update");
          }
        };
      }

      updatePartnerIDB(partners, partner_deleted_record_ids) {
        var self = this;
        // console.log("updating partners in indexdb", partners);
        if (
          (partners && partners.length) ||
          (partner_deleted_record_ids && partner_deleted_record_ids.length)
        ) {
          if (!("indexedDB" in window)) {
            console.log("This browser doesn't support IndexedDB");
          } else {
            var request = window.indexedDB.open("Partners", 1);
            request.onsuccess = function (event) {
              var db = event.target.result;
              var transaction = db.transaction("partners", "readwrite");
              var itemsStore = transaction.objectStore("partners");
              if (partners && partners.length) {
                partners.forEach(function (item) {
                  var data_store = itemsStore.get(item.id);
                  data_store.onsuccess = function (event) {
                    var data = event.target.result;
                    data = item;
                    var requestUpdate = itemsStore.put(data);
                  };
                });
              }
              if (
                partner_deleted_record_ids &&
                partner_deleted_record_ids.length
              ) {
                partner_deleted_record_ids.forEach(function (id) {
                  var data_store = itemsStore.get(id);
                  data_store.onsuccess = function (event) {
                    var data = event.target.result;
                    var requestUpdate = itemsStore.delete(id);
                  };
                });
              }
            };
          }
        }
      }

      updateProductsIDB(products, product_deleted_record_ids) {
        var self = this;
        // console.log("updating products in indexdb", products);
        if (
          (products && products.length) ||
          (product_deleted_record_ids && product_deleted_record_ids.length)
        ) {
          if (!("indexedDB" in window)) {
            console.log("This browser doesn't support IndexedDB");
          } else {
            var request = window.indexedDB.open("Product", 1);
            request.onsuccess = function (event) {
              var db = event.target.result;
              var transaction = db.transaction("products", "readwrite");
              var itemsStore = transaction.objectStore("products");
              if (products && products.length)
                _.each(products, function (item) {
                  //-------------------------------------------

                  var data_store = itemsStore.get(item.id);
                  data_store.onsuccess = function (event) {
                    var data = event.target.result;
                    data = item;
                    delete data["pos"];
                    delete data["applicablePricelistItems"];
                    // console.log('#### Data ----', data);
                    var requestUpdate = itemsStore.put(data);
                  };
                });
              if (
                product_deleted_record_ids &&
                product_deleted_record_ids.length
              )
                _.each(product_deleted_record_ids, function (id) {
                  var data_store = itemsStore.get(id);
                  data_store.onsuccess = function (event) {
                    var data = event.target.result;
                    var requestUpdate = itemsStore.delete(id);
                  };
                });
            };
          }
        }
      }

      // custom_pricelist_load(pricelists) {
      //   var self = this;
      //   if (pricelist_items.length)
      //               super_price_item_loaded.call(this, self, pricelist_items);
      //           var request = window.indexedDB.open('Items', 1);
      //           request.onsuccess = function (event) {
      //               var db = event.target.result;
      //               if (!(pricelist_items.length) && pricelist_item_model.context.is_indexed_updated && pricelist_item_model.context.is_indexed_updated.length) {
      //                   getRecordsIndexedDB(db, 'items').then(function (res) {
      //                       super_price_item_loaded.call(this, self, res);
      //                   });
      //               } else {
      //                   if (db.objectStoreNames.contains('items')) {
      //                       try {
      //                           var transaction = db.transaction('items', 'readwrite');
      //                           var itemsStore = transaction.objectStore('items');
      //                           pricelist_items.forEach(function (item) {
      //                               var data_store = itemsStore.get(item.id);
      //                               data_store.onsuccess = function (event) {
      //                                   var data = event.target.result;
      //                                   data = item;
      //                                   var requestUpdate = itemsStore.put(data);
      //                               }
      //                           });
      //                       } catch {
      //                           console.log("-----exception --- items")
      //                       }
      //                   }
      //               };
      //           }
      //           request.onupgradeneeded = function (event) {
      //               var db = event.target.result;
      //               var itemsStore = db.createObjectStore('items', {
      //                   keyPath: 'id'
      //               });
      //   };

      //   // **********date*******
      //   var date_request = window.indexedDB.open("cacheDate", 1);
      //   date_request.onupgradeneeded = function (event) {
      //     var db = event.target.result;
      //     var lastUpdateTimeStore = db.createObjectStore("last_update", {
      //       keyPath: "id",
      //     });
      //   };
      //   date_request.onsuccess = function (event) {
      //     var date_db = event.target.result;
      //     try {
      //       var time_transaction = date_db.transaction(
      //         "last_update",
      //         "readwrite"
      //       );
      //       var lastTimeStore = time_transaction.objectStore("last_update");
      //       var last_date_store = lastTimeStore.get("time");
      //       last_date_store.onsuccess = function (event) {
      //         var data = event.target.result;
      //         data = {
      //           id: "time",
      //           time: self.db.mongo_config
      //             ? self.db.mongo_config[0].cache_last_update_time
      //             : undefined,
      //         };
      //         var last_updated_time = lastTimeStore.put(data);
      //       };
      //     } catch {
      //       console.log("-----exception---- last update");
      //     }
      //   };
      // }
    };
  Registries.Model.extend(PosGlobalState, MongoServerConfigPosGlobalState);
  PosDB.include({
    _loadMongoServerConfig(mongo_config) {
      var self = this;
      self.mongo_config = {};
      if (mongo_config && mongo_config.filter((a) => a.active_record)) {
        self.mongo_config = mongo_config.filter((a) => a.active_record)[0];
      }
    },
    get_product_by_category: function (category_id) {
      var product_ids = this.product_by_category_id[category_id];
      var list = [];
      if (product_ids) {
        for (
          var i = 0, len = Math.min(product_ids.length, this.limit);
          i < len;
          i++
        ) {
          const product = this.product_by_id[product_ids[i]];
          if (!(product.active && product.available_in_pos)) continue;
          if (!list.filter((a) => a.id === product.id).length)
            list.push(product);
        }
      }
      return list;
    },
    search_product_in_category: function (category_id, query) {
      try {
        query = query.replace(
          /[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,
          "."
        );
        query = query.replace(/ /g, ".+");
        var re = RegExp("([0-9]+):.*?" + utils.unaccent(query), "gi");
      } catch (_e) {
        return [];
      }
      var results = [];
      for (var i = 0; i < this.limit; i++) {
        var r = re.exec(this.category_search_string[category_id]);
        if (r) {
          var id = Number(r[1]);
          const product = this.get_product_by_id(id);
          if (!(product.active && product.available_in_pos)) continue;
          if (!results.filter((a) => a.id === product.id).length)
            results.push(product);
        } else {
          break;
        }
      }
      return results;
    },
  });

  // ********************Function for getting data from indexedDB***************************************

  function getRecordsIndexedDB(db, store) {
    return new Promise((resolve, reject) => {
      if (db.objectStoreNames.contains(store)) {
        try {
          var transaction = db.transaction(store, "readwrite");
          var objectStore = transaction.objectStore(store);
          var data_request = objectStore.getAll();
          data_request.onsuccess = function (event) {
            resolve(event.target.result);
          };
          data_request.onerror = function (event) {
            reject();
          };
        } catch (e) {
          console.log("No Items found", e);
        }
      }
    });
  }
});

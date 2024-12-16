=====================
Add a Reason on Scrap
=====================

This module was written to give the user the possibility to add a reason for the
scrap order.

**Features:**
  * creating reasons as many as possible,
  * possibility to prioritize some reasons by ranking them in the list view
  * possibility to select a reason from the list reasons
  * possibility to add a note on the scrap
  * adding the reason and note on both the wizard (through the Scrap button on the
    move) as well as on the scrap order from the operations.

**Table of contents**
~~~~~~~~~~~~~~~~~~~~~

.. contents::
   :local:

Configuration:
==============

To configure the Scrap Reasons, you need to have "Inventory Manager" access right.

* Go to *Inventory / Configuration / Warehouse Management / Scrap Reasons*.
* Easily add a new Scrap Reason.
* On the list view, with the help of the handle |icon|, you can order the reasons

.. |icon| image:: ./static/description/handle.png
   :height: 1em

How to Use:
===========

To use this module, you need to first configure the reasons as described above, then:

#. On a validated move to an internal location, where the button Scrap is available,
   click on the Scrap button.
#. On the Wizard, you are able to select a Reason or add a note:

   .. figure:: ./static/description/reason_on_wizard.png
      :width: 100 %
      :align: center

#. From *Inventory / Operations / Scrap*, create or select a Scrap order, then you can 
   select a Reason or add a note:

   .. figure:: ./static/description/reason_on_scrap_form.png
      :width: 100 %
      :align: center

#. With the smart button on the *Scrap Reason* form, you can go to the list of "done"
   scrap orders with the corresponding reason:

   .. figure:: ./static/description/scrap_reason_form_with_scrap_order_counts.png
      :width: 100 %
      :align: center

**Notes:**
   * Only inventory managers can create and edit the reasons from the Configuration.
   * The option "Create" as well as "Create and Edit" are disabled on the form views.
   * The reason and note will be read-only when the Scrap is "done", but just in the 
     view so as to be able to import/update the data.


Feedback & Issues
=================

In case of feedback or any possible issues, this can be reported through submitting this
form https://www.bitigloo.com/r/rYu or via an email to apps@bitigloo.com.

Credits
=======

Authors
-------

* bitigloo GmbH <https://github.com/bitigloo>

Maintainers
-----------

This module is maintained by bitigloo GmbH (https://www.bitigloo.com/r/bw4). Check out our 
products (https://www.bitigloo.com/r/zjj) and services (https://www.bitigloo.com/r/Lzo).

.. image:: https://www.bitigloo.com/web/image/website/1/favicon
   :alt: bitigloo GmbH, Odoo Partner in Bonn, NRW, Germany
   :target: https://www.bitigloo.com/r/bw4
   :width: 10%

bitigloo GmbH is a certified Odoo partner in Germany which enjoys the expertise of a
team of proficient Odoo experts with years of experience in finding the best ERP
solutions for various businesses, tailoring them to their specific needs, and
implementing them in the most effective way.

License
=======

This module is under the license "GPL-3 or any later version":
https://www.gnu.org/licenses/licenses.html#LicenseURLs
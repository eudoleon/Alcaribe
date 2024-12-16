odoo.define('pos_fiscal_printer.PartnerDetailsEdit', function (require) {
    'use strict';

    const { useState } = owl;
    const PartnerDetailsEdit = require("point_of_sale.PartnerDetailsEdit");
    const Registries = require("point_of_sale.Registries");

    const PosPartnerDetailsEdit = (OriginalPartnerDetailsEdit) =>
        class extends OriginalPartnerDetailsEdit { 
            setup() {
                super.setup();
                this.intFields.push('city_id');
                const partner = this.props.partner;
                this.changes = useState({
                    ...this.changes,
                    company_type: partner.company_type,
                    city_id: partner.city_id && partner.city_id[0],
                    phone: partner.phone,
                    state_id: partner.state_id && partner.state_id[0],
                    vat: partner.vat,
                    street: partner.street,
                });
            }

            validateRIF(rif) {
                // Expresión regular para validar el formato del RIF
                const rifRegex = /^[VEJPG][0-9]{9}$/;
                if (!rifRegex.test(rif)) {
                    return false;
                }

                // Validación del dígito verificador
                const weights = [3, 2, 7, 6, 5, 4, 3, 2];
                let sum = 0;
                for (let i = 0; i < 8; i++) {
                    sum += parseInt(rif[i + 1]) * weights[i];
                }
                const remainder = 11 - (sum % 11);
                const checkDigit = remainder === 10 ? 0 : (remainder === 11 ? 1 : remainder);

                return parseInt(rif[9]) === checkDigit;
            }

            saveChanges() {
                // Handle additional fields
                this.changes.mobile = this.changes.mobile || this.props.partner.mobile;
                this.changes.state_id = this.changes.state_id || (this.props.partner.state_id && this.props.partner.state_id[0]);
                this.changes.city_id = this.changes.city_id || (this.props.partner.city_id && this.props.partner.city_id[0]);
                this.changes.vat = this.changes.vat || this.props.partner.vat;
                this.changes.street = this.changes.street || this.props.partner.street;
            
                // Validate required fields
                const requiredFields = ['mobile', 'state_id', 'city_id', 'vat', 'street'];
                const fieldNames = {
                    'mobile': 'Teléfono',
                    'state_id': 'Departamento',
                    'city_id': 'Municipio',
                    'vat': 'RIF',
                    'street': 'Dirección'
                };
                const missingFields = requiredFields.filter(field =>
                    !this.changes[field] && !this.props.partner[field]
                );
            
                if (missingFields.length > 0) {
                    const missingFieldNames = missingFields.map(field => fieldNames[field]);
                    this.showPopup("ErrorPopup", {
                        title: "Campos obligatorios",
                        body: `Los siguientes campos son obligatorios: ${missingFieldNames.join(', ')}`,
                    });
                    return;
                }
                super.saveChanges();
            }
        };

    Registries.Component.extend(PartnerDetailsEdit, PosPartnerDetailsEdit);

    return PosPartnerDetailsEdit;
});
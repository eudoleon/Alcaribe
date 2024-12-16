from odoo import models, fields
import xlsxwriter
from io import BytesIO
import base64
from datetime import datetime

class POSReportZExcelWizard(models.TransientModel):
    _name = 'pos.report.z.excel.wizard'
    _description = 'Wizard for generating POS Report Z Excel'

    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True)
    fiscal_printer_id = fields.Many2one('x.pos.fiscal.printer', string='Impresora Fiscal', required=True)
    excel_file = fields.Binary('Excel Report', readonly=True)
    file_name = fields.Char('Excel File', readonly=True)
    report_type = fields.Selection([
        ('normal', 'Reporte Z'),
        ('igtf', 'Reporte IGTF')
    ], string='Tipo de Reporte', default='normal', required=True) 

    def generate_excel_report(self):
        self.ensure_one()
        if self.report_type == 'normal':
            return self._generate_normal_report()
        else:
            return self._generate_igtf_report()

    def _generate_normal_report(self):
        self.ensure_one()
        report_data = self.env['pos.report.z'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('x_fiscal_printer_id', '=', self.fiscal_printer_id.id)
        ])

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Relacion de Ventas')

        # Formats
        company_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        subheader_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        cell_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0.00'})

        # Company information
        company = self.env.company
        worksheet.write('A1', company.name, company_format)
        worksheet.write('A2', f"N° DE RIF.: {company.vat}", company_format)
        worksheet.write('A3', "CONTRIBUYENTE FORMAL-ESPECIAL", company_format)
        worksheet.write('A4', company.street, company_format)
        worksheet.write('A5', "Av. Circunvalacion Norte Local 18 Sector Pozo Grande, Estacion de Servicio de Sario, Los Robles, El Pilar (Los Robles), Nueva Esparta.", company_format)
        worksheet.write('A6', "RELACION DE VENTAS", company_format)
        worksheet.write('A7', f"MES DE {self.date_from.strftime('%B').upper()} {self.date_from.year}", company_format)

        # Subheaders
        worksheet.merge_range('A9:A10', 'Fecha de Emision', header_format)
        worksheet.merge_range('B9:E9', f'MAQUINA FISCAL {self.fiscal_printer_id.serial}', subheader_format)
        worksheet.write('B10', 'Factura Inicial', header_format)
        worksheet.write('C10', 'Factura Final', header_format)
        worksheet.write('D10', 'Total', header_format)
        worksheet.write('E10', 'Total IGTF', header_format)

        worksheet.merge_range('F9:I9', f'Nota de Credito {self.fiscal_printer_id.serial}', subheader_format)
        worksheet.write('F10', 'NC Inicial', header_format)
        worksheet.write('G10', 'NC Final', header_format)
        worksheet.write('H10', 'Total', header_format)
        worksheet.write('I10', 'Total IGTF', header_format)

        worksheet.merge_range('J9:M9', 'Manual', subheader_format)
        worksheet.write('J10', 'Factura Inicial', header_format)
        worksheet.write('K10', 'Factura Final', header_format)
        worksheet.write('L10', 'Total', header_format)
        worksheet.write('M10', 'Total IGTF', header_format)

        worksheet.merge_range('N9:N10', 'Total de Ventas Consolidadas Bs', header_format)
        worksheet.merge_range('O9:O10', 'Total IGTF Consolidadas Bs', header_format)
        worksheet.merge_range('P9:P10', 'Total Ventas Mas IGTF Consolidadas Bs', header_format)

        row = 10
        total_ventas_consolidadas = 0
        total_igtf_consolidadas = 0
        total_ventas_mas_igtf = 0

        for record in report_data:
            col = 0
            worksheet.write(row, col, record.date.strftime('%d/%m/%Y'), cell_format)
            
            # Maquina Fiscal
            worksheet.write(row, col + 1, record.fac_desde or 'NO HUBO', cell_format)
            worksheet.write(row, col + 2, record.fac_hasta or 'NO HUBO', cell_format)
            worksheet.write(row, col + 3, record.total_exempt_pos, number_format)
            worksheet.write(row, col + 4, record.total_igtf_pos, number_format)
            
            # Nota de Credito
            nc_inicial = record.fac_desde if record.total_exempt_pos_nc != 0 else 'NO HUBO'
            nc_final = record.fac_hasta if record.total_exempt_pos_nc != 0 else 'NO HUBO'
            worksheet.write(row, col + 5, nc_inicial, cell_format)
            worksheet.write(row, col + 6, nc_final, cell_format)
            worksheet.write(row, col + 7, abs(record.total_exempt_pos_nc), number_format)
            worksheet.write(row, col + 8, abs(record.total_igtf_pos_nc), number_format)
            
            # Manual
            worksheet.write(row, col + 9, 'NO HUBO', cell_format)
            worksheet.write(row, col + 10, 'NO HUBO', cell_format)
            worksheet.write(row, col + 11, 0, number_format)
            worksheet.write(row, col + 12, 0, number_format)
            
            # Totals
            total_ventas = record.total_exempt_pos - abs(record.total_exempt_pos_nc)
            total_igtf = record.total_igtf_pos - abs(record.total_igtf_pos_nc)
            total_ventas_mas_igtf_dia = total_ventas + total_igtf

            worksheet.write(row, col + 13, total_ventas, number_format)
            worksheet.write(row, col + 14, total_igtf, number_format)
            worksheet.write(row, col + 15, total_ventas_mas_igtf_dia, number_format)
            
            total_ventas_consolidadas += total_ventas
            total_igtf_consolidadas += total_igtf
            total_ventas_mas_igtf += total_ventas_mas_igtf_dia
            
            row += 1

        # Totales
        worksheet.write(row, 13, total_ventas_consolidadas, number_format)
        worksheet.write(row, 14, total_igtf_consolidadas, number_format)
        worksheet.write(row, 15, total_ventas_mas_igtf, number_format)

        row += 2  # Dejar una fila en blanco después de los datos principales

        # Agregar la tabla de detalles
        worksheet.write(row, 0, 'DETALLE', header_format)
        worksheet.write(row, 1, 'BASE IMPONIBLE', header_format)
        worksheet.write(row, 2, 'DEBITO FISCAL', header_format)
        worksheet.write(row, 3, 'IVA', header_format)
        worksheet.write(row, 4, 'Total IGTF', header_format)
        row += 1

        details = [
            ('VENTAS INTERNAS NO GRAVADAS', total_ventas_consolidadas, 0, 0, total_igtf_consolidadas),
            ('VENTAS DE EXPORTACION', 0, 0, 0, 0),
            ('VENTAS INTERNAS GRAVADAS POR ALICUOTA GENERAL', 0, 0, 0, 0),
            ('VENTAS INTERNAS GRAVADAS POR ALICUOTA GENERAL MAS ALICUOTA ADICIONAL', 0, 0, 0, 0),
            ('VENTAS INTERNAS GRAVADAS POR ALICUOTA REDUCIDA', 0, 0, 0, 0),
        ]

        for detail in details:
            worksheet.write(row, 0, detail[0], cell_format)
            worksheet.write(row, 1, detail[1], number_format)
            worksheet.write(row, 2, detail[2], number_format)
            worksheet.write(row, 3, detail[3], number_format)
            worksheet.write(row, 4, detail[4], number_format)
            row += 1

        # Total
        worksheet.write(row, 0, 'TOTAL VENTAS Y DEBITO FISCAL PARA EFECTOS DE DETERMINACION', cell_format)
        worksheet.write(row, 1, total_ventas_consolidadas, number_format)
        worksheet.write(row, 2, 0, number_format)
        worksheet.write(row, 3, 0, number_format)
        worksheet.write(row, 4, total_igtf_consolidadas, number_format)

        # Adjust column widths
        for i, width in enumerate([15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 25, 25, 25]):
            worksheet.set_column(i, i, width)

        workbook.close()
        
        excel_data = output.getvalue()
        self.excel_file = base64.encodebytes(excel_data)
        self.file_name = f'Relacion_de_Ventas_{self.date_from.strftime("%B_%Y")}.xlsx'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.report.z.excel.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
    


    def _generate_igtf_report(self):
        report_data = self.env['pos.report.z'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('x_fiscal_printer_id', '=', self.fiscal_printer_id.id)
        ])

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Relacion de IGTF')

        # Formatos
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        cell_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0.00'})

        # Datos de la empresa
        company = self.env.company
        worksheet.write('A1', company.name.upper(), workbook.add_format({'bold': True, 'font_size': 14}))
        worksheet.write('A2', f"R.I.F.: {company.vat}")
        worksheet.write('A3', f"Rangos: Desde {self.date_from.strftime('%d/%m/%Y')} Hasta {self.date_to.strftime('%d/%m/%Y')}")
        worksheet.write('A4', f"Fecha Consulta: {fields.Datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}")
        worksheet.merge_range('A6:H6', 'RELACIÓN DE IGTF', workbook.add_format({'bold': True, 'align': 'center', 'font_size': 12}))

        # Cabeceras de columnas
        headers = ['Fecha', 'Establecimiento', 'Caja', 'Serial IF', '# Z', 'Transacciones', 'Base Imponible IGTF', 'Total IGTF']
        for col, header in enumerate(headers):
            worksheet.write(7, col, header, header_format)

        # Datos
        row = 8
        total_transactions = 0
        total_base_imponible = 0
        total_igtf = 0

        for record in report_data:
            worksheet.write(row, 0, record.date.strftime('%d-%m-%Y'), cell_format)
            worksheet.write(row, 1, company.name, cell_format)
            worksheet.write(row, 2, f"Caja {record.x_fiscal_printer_id.name}", cell_format)
            worksheet.write(row, 3, record.x_fiscal_printer_code, cell_format)
            worksheet.write(row, 4, record.number, cell_format)
            worksheet.write(row, 5, len(record.pos_order_ids), cell_format)
            worksheet.write(row, 6, record.total_exempt_pos, number_format)
            worksheet.write(row, 7, record.total_igtf_pos, number_format)

            total_transactions += len(record.pos_order_ids)
            total_base_imponible += record.total_exempt_pos
            total_igtf += record.total_igtf_pos

            row += 1

        # Totales
        worksheet.write(row, 5, total_transactions, cell_format)
        worksheet.write(row, 6, total_base_imponible, number_format)
        worksheet.write(row, 7, total_igtf, number_format)

        # Ajustar anchos de columna
        worksheet.set_column('A:H', 18)

        workbook.close()
        
        excel_data = output.getvalue()
        self.excel_file = base64.encodebytes(excel_data)
        self.file_name = f'Relacion_IGTF_{company.name}_{self.date_from.strftime("%d_%m_%Y")}_{self.date_to.strftime("%d_%m_%Y")}.xlsx'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.report.z.excel.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
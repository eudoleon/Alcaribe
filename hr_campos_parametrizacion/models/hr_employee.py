# coding: utf-8
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError, ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee.public'
    zapatos = fields.Selection([('32','32'),('33','33'),('34','34'),('35','35'),('36','36'),('37','37'),('38','38'),('39','39'),('40','40'),('41','41'),('42','42'),('43','43'),('44','44'),('45','45'),('46','46')])
    camisas = fields.Selection([('XS', 'XS'),('S', 'S'),('M', 'M'),('M-L', 'M-L'),('L', 'L'),('L-XL', 'L-XL'),('XL', 'XL'),('XL-XXL', 'XL-XXL'),('XXL', 'XXL')])
    pantalon = fields.Selection([('24','24'),('25','25'),('26','26'),('27','27'),('28','28'),('29','29'),('30','30'),('31','31'),('32','32'),('33','33'),('34','34'),('35','35'),('36','36'),('37','37'),('38','38'),('39','39'),('40','40'),('41','41'),('42','42'),('43','43'),('44','44'),('45','45'),('46','46')])
    chemise = fields.Selection([('XS', 'XS'),('S', 'S'),('M', 'M'),('M-L', 'M-L'),('L', 'L'),('L-XL', 'L-XL'),('XL', 'XL'),('XL-XXL', 'XL-XXL'),('XXL', 'XXL')])


    grado_instruccion = fields.Many2one('hr.grado.instruccion')
    profesion = fields.Many2one('hr.profesion')
    grupo_familiar_ids = fields.One2many('hr.grupo.familiar', 'employee_id', string='Grupo Familiar')
    cursos_ids = fields.One2many('hr.cursos', 'employee_id', string='Cursos')
    documentos_ids = fields.One2many('hr.documentos', 'employee_id', string='Documentos')
    promocion_ids = fields.One2many('hr.promocion', 'employee_id', string='Promociones')
    rif = fields.Char()
    cedula = fields.Char()
    tipo_contribuyente = fields.Selection([('V','V'),('E','E'),('J','J'),('G','G'),('P','P'),('C','C'),])

    direccion = fields.Text()
    ciudad = fields.Char()
    country_id = fields.Many2one('res.country')
    state_id = fields.Many2one('res.country.state')
    cod_post = fields.Char()
    municipality_id = fields.Many2one('res.country.state.municipality')
    parish_id = fields.Many2one('res.country.state.municipality.parish')

    direccion_trabajo = fields.Char(compute='_compute_direccion')

    constancia_trab = fields.Char(default="Jefe HHRR")
    gerente_rrhh_id = fields.Many2one('hr.employee')
    fecha_hoy = fields.Date(compute='_compute_hoy')

    ###### CAMPOS PARA EL MINTRA  #############
    tipo_trabajador = fields.Selection([('1','De Dirección'),('2','De Inspección o Vigilancia'),('3','Aprendiz Ince'),('4','Pasante'),('5','Trabajador Calificado'),('6','Trabajador no Calificado')])
    tipo_contrato = fields.Selection([('TD','Tiempo Completo'),('TI','Tiempo Indeterminado'),('OD','Obra Determinada')])
    fecha_ingreso = fields.Date(compute='_compute_datos_contrato')
    salario = fields.Float(compute='_compute_datos_contrato')
    ocupacion = fields.Char(size=4)
    subproceso = fields.Char(size=9)
    jornada = fields.Selection([('D','Diurno'),('N','Nocturno'),('M','Mixta'),('R2','Rotativo 2 Turnos'),('R3','Rotativo 3 turnos'),('TC','De trabajo Continuo')])
    sindicalizado = fields.Selection([('N','No'),('S','Si')])
    lab_domingo = fields.Selection([('N','No'),('S','Si')])
    prom_hora_lab = fields.Float(digits=(2,0))
    prom_hora_extras = fields.Float(digits=(2,0))

    prom_hora_noc = fields.Float(digits=(2,0))
    carga_familiar = fields.Char(size=2)
    fam_discap  = fields.Selection([('N','No'),('S','Si')])
    hijo_benf_guard = fields.Char(digits=(1,0))
    monto_bene_guar = fields.Float(digits=(3,2))
    mujer_embarazad = fields.Selection([('N','No'),('S','Si')])


    tipo_sangre = fields.Char()
    alergico_descripcion = fields.Char()
    patologia = fields.Char()
    tipo_discapacidad = fields.Char()
    expense_manager_id  = fields.Many2one()
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    zapatos = fields.Selection([('32','32'),('33','33'),('34','34'),('35','35'),('36','36'),('37','37'),('38','38'),('39','39'),('40','40'),('41','41'),('42','42'),('43','43'),('44','44'),('45','45'),('46','46')])
    camisas = fields.Selection([('XS', 'XS'),('S', 'S'),('M', 'M'),('M-L', 'M-L'),('L', 'L'),('L-XL', 'L-XL'),('XL', 'XL'),('XL-XXL', 'XL-XXL'),('XXL', 'XXL')])
    pantalon = fields.Selection([('24','24'),('25','25'),('26','26'),('27','27'),('28','28'),('29','29'),('30','30'),('31','31'),('32','32'),('33','33'),('34','34'),('35','35'),('36','36'),('37','37'),('38','38'),('39','39'),('40','40'),('41','41'),('42','42'),('43','43'),('44','44'),('45','45'),('46','46')])
    chemise = fields.Selection([('XS', 'XS'),('S', 'S'),('M', 'M'),('M-L', 'M-L'),('L', 'L'),('L-XL', 'L-XL'),('XL', 'XL'),('XL-XXL', 'XL-XXL'),('XXL', 'XXL')])


    grado_instruccion = fields.Many2one('hr.grado.instruccion')
    profesion = fields.Many2one('hr.profesion')
    grupo_familiar_ids = fields.One2many('hr.grupo.familiar', 'employee_id', string='Grupo Familiar')
    cursos_ids = fields.One2many('hr.cursos', 'employee_id', string='Cursos')
    documentos_ids = fields.One2many('hr.documentos', 'employee_id', string='Documentos')
    promocion_ids = fields.One2many('hr.promocion', 'employee_id', string='Promociones')
    rif = fields.Char()
    cedula = fields.Char()
    tipo_contribuyente = fields.Selection([('V','V'),('E','E'),('J','J'),('G','G'),('P','P'),('C','C'),])

    direccion = fields.Text()
    ciudad = fields.Char()
    country_id = fields.Many2one('res.country')
    state_id = fields.Many2one('res.country.state')
    cod_post = fields.Char()
    municipality_id = fields.Many2one('res.country.state.municipality')
    parish_id = fields.Many2one('res.country.state.municipality.parish')

    direccion_trabajo = fields.Char(compute='_compute_direccion')

    constancia_trab = fields.Char(default="Jefe HHRR")
    gerente_rrhh_id = fields.Many2one('hr.employee')
    fecha_hoy = fields.Date(compute='_compute_hoy')

    ###### CAMPOS PARA EL MINTRA  #############
    tipo_trabajador = fields.Selection([('1','De Dirección'),('2','De Inspección o Vigilancia'),('3','Aprendiz Ince'),('4','Pasante'),('5','Trabajador Calificado'),('6','Trabajador no Calificado')])
    tipo_contrato = fields.Selection([('TD','Tiempo Completo'),('TI','Tiempo Indeterminado'),('OD','Obra Determinada')])
    fecha_ingreso = fields.Date(compute='_compute_datos_contrato')
    salario = fields.Float(compute='_compute_datos_contrato')
    ocupacion = fields.Char(size=4)
    subproceso = fields.Char(size=9)
    jornada = fields.Selection([('D','Diurno'),('N','Nocturno'),('M','Mixta'),('R2','Rotativo 2 Turnos'),('R3','Rotativo 3 turnos'),('TC','De trabajo Continuo')])
    sindicalizado = fields.Selection([('N','No'),('S','Si')])
    lab_domingo = fields.Selection([('N','No'),('S','Si')])
    prom_hora_lab = fields.Float(digits=(2,0))
    prom_hora_extras = fields.Float(digits=(2,0))

    prom_hora_noc = fields.Float(digits=(2,0))
    carga_familiar = fields.Char(size=2)
    fam_discap  = fields.Selection([('N','No'),('S','Si')])
    hijo_benf_guard = fields.Char(digits=(1,0))
    monto_bene_guar = fields.Float(digits=(3,2))
    mujer_embarazad = fields.Selection([('N','No'),('S','Si')])


    tipo_sangre = fields.Char()
    alergico_descripcion = fields.Char()
    patologia = fields.Char()
    tipo_discapacidad = fields.Char()

    def get_nro_registro_empleado(self):

        self.ensure_one()
        SEQUENCE_CODE = 'nro_registro_empleado'
        company_id = self.company_id.id
        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id)
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': '000-',
                'name': 'secuencia nro registro empleado compañia: %s' % self.company_id.name,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 4,
                'number_increment': 1,
                'company_id': self.company_id.id,
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        #self.invoice_number_cli=name
        return name

    def _compute_datos_contrato(self):
        valor='1999-01-01'
        sueldo=0
        for selff in self:
            if selff.contract_id:
                valor=selff.contract_id.date_start
                sueldo=selff.contract_id.wage
            selff.fecha_ingreso=valor
            selff.salario=sueldo

    @api.onchange('work_location_pri')
    def actualiza_ubicacion(self):
        self.work_location=self.work_location_pri.name

    def generate_nro_registro(self):
        self.registration_number=self.get_nro_registro_empleado()


    def _compute_hoy(self):
        for selff in self:
            hoy=datetime.now().strftime('%Y-%m-%d')
            selff.fecha_hoy=hoy

    @api.onchange('company_id')
    def _compute_direccion(self):
        if self.company_id.street:
            self.direccion_trabajo=self.company_id.street
            if self.company_id.street2:
                self.direccion_trabajo=self.company_id.street+" "+self.company_id.street2
                if self.company_id.city:
                    self.direccion_trabajo=self.company_id.street+" "+self.company_id.street2+". "+self.company_id.city
                    if self.company_id.state_id.name:
                        self.direccion_trabajo=self.company_id.street+" "+self.company_id.street2+". "+self.company_id.city+"/"+self.company_id.state_id.name
        else: 
            self.direccion_trabajo="****"

    def formato_fecha(self,date):
        resultado="0000/00/00"
        if date:
            fecha = str(date)
            fecha_aux=fecha
            ano=fecha_aux[0:4]
            mes=fecha[5:7]
            dia=fecha[8:10]  
            resultado=dia+"/"+mes+"/"+ano
        return resultado

    def float_format(self,valor):
        #valor=self.base_tax
        if valor:
            result = '{:,.2f}'.format(valor)
            result = result.replace(',','*')
            result = result.replace('.',',')
            result = result.replace('*','.')
        else:
            result="0,00"
        return result

    def dia(self,date):
        fecha = str(date)
        fecha_aux=fecha
        dia=fecha[8:10]  
        resultado=dia
        return int(resultado)

    def mes(self,date):
        fecha = str(date)
        fecha_aux=fecha
        mes=fecha[5:7]
        if mes=='01':
            month="Enero"
        if mes=='02':
            month="Febrero"
        if mes=='03':
            month="Marzo"
        if mes=='04':
            month="Abril"
        if mes=='05':
            month="Mayo"
        if mes=='06':
            month="Junio"
        if mes=='07':
            month="Julio"
        if mes=='08':
            month="Agosto"
        if mes=='09':
            month="Septiembre"
        if mes=='10':
            month="Octubre"
        if mes=='11':
            month="Noviembre"
        if mes=='12':
            month="Diciembre"
        resultado=month
        return resultado

    def ano(self,date):
        fecha = str(date)
        fecha_aux=fecha
        ano=fecha_aux[0:4]  
        resultado=ano
        return int(resultado)

    def get_literal_amount(self,amount):
        indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
        entero = int(amount)
        decimal = int(round((amount - entero)*100))
        contador = 0
        numero_letras = ""
        while entero >0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a,1).strip()
            else:
                en_letras = self.convierte_cifra(a,0).strip()
            if a==0:
                numero_letras = en_letras+" "+numero_letras
            elif a==1:
                if contador in (1,3):
                    numero_letras = indicador[contador][0]+" "+numero_letras
                else:
                    numero_letras = en_letras+" "+indicador[contador][0]+" "+numero_letras
            else:
                numero_letras = en_letras+" "+indicador[contador][1]+" "+numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        numero_letras = numero_letras+" con " + str(decimal) +"/100"
        print('numero: ',amount)
        print(numero_letras)
        return numero_letras
        
    def convierte_cifra(self, numero, sw):
        lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
        lista_decena =  ["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
                        ("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
                        ("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
                        ("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
                        ("NOVENTA" , "NOVENTA Y ")
                        ]
        lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
        centena = int (numero / 100)
        decena = int((numero -(centena * 100))/10)
        unidad = int(numero - (centena * 100 + decena * 10))
        
        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""
        
        #Validad las centenas
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad)!=0:
                texto_centena = texto_centena[1]
            else:
                texto_centena = texto_centena[0]
        
        #Valida las decenas
        texto_decena = lista_decena[decena]
        if decena == 1:
            texto_decena = texto_decena[unidad]
        elif decena > 1:
            if unidad != 0:
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        
        #Validar las unidades
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
        
        return "%s %s %s" %(texto_centena,texto_decena,texto_unidad)

class HrNivelInstruccion(models.Model):

    _name = 'hr.grado.instruccion'

    name = fields.Char()
    activo = fields.Boolean(default=True)

class HrProfesion(models.Model):

    _name = 'hr.profesion'

    name = fields.Char()
    activo = fields.Boolean(default=True)

class HrCursos(models.Model):

    _name = 'hr.cursos'

    employee_id = fields.Many2one('hr.employee', string='Cursos')
    name = fields.Char()
    institucion = fields.Char()
    fecha = fields.Date()
    duracion = fields.Char()
    nro_telefono = fields.Char()
    contacto = fields.Char()
    tipo = fields.Selection([('Externo','Externo'),('Interno','Interno')])

class HrDocumentos(models.Model):

    _name = 'hr.documentos'

    employee_id = fields.Many2one('hr.employee', string='Documentos')
    name = fields.Char()
    documento = fields.Binary()

class HrPromosiones(models.Model):

    _name = 'hr.promocion'

    employee_id = fields.Many2one('hr.employee', string='Cursos')
    job_id = fields.Many2one('hr.job')
    motivo = fields.Char()
    fecha = fields.Date()
    autorizor_id = fields.Many2one('hr.employee')

class HrUbicacionTrabajo(models.Model):

    _name = 'hr.ubicacion'

    name = fields.Char()
    activo = fields.Boolean(default=True)


class HrGrupoFamiliar(models.Model):

    _name = 'hr.grupo.familiar'

    employee_id = fields.Many2one('hr.employee', string='Grupo Familiar')
    name = fields.Char()
    name2 = fields.Char()
    fecha_nac = fields.Date()
    edad = fields.Char(compute='_compute_edad')
    sexo = fields.Selection([('F','Femenino'),('M','Masculino')])
    identificador = fields.Char(default="N/A")
    nro_telefono = fields.Char()
    parentesco = fields.Selection([('ma','Madre'),('pa','Padre'),('hi','Hijo(@)'),('ab','Abuelo@'),('ti','Tio(@)'),('pr','Padrino'),('mr','Madrina'),('ot','Otro')])
    parentesco_din = fields.Many2one('hr.parentesco')
    date_actual = fields.Date(string='Date From', compute='_compute_fecha_hoy')

    @api.onchange('fecha_nac')
    def _compute_edad(self):
        tiempo="0 Mes"
        for selff in self:
            if selff.employee_id.id:
                if selff.fecha_nac:
                    fecha_ing=selff.fecha_nac
                else:
                    fecha_ing=selff.date_actual
                fecha_actual=selff.date_actual
                dias=selff.days_dife(fecha_actual,fecha_ing)
                if dias<365:
                    tiempo=str(round(dias/30,1))+" Meses"
                else:
                    tiempo=str(int(round(dias/365,0)))+" Años"
            selff.edad=tiempo

    def days_dife(self,d1, d2):
       return abs((d2 - d1).days)

    @api.onchange('fecha_nac')
    def _compute_fecha_hoy(self):
        hoy=datetime.now().strftime('%Y-%m-%d')
        self.date_actual=hoy

class HrParentesco(models.Model):

    _name = 'hr.parentesco'

    name = fields.Char()
    code = fields.Char()
        
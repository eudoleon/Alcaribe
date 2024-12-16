
{
    "name": "Pagos Masivos",
    "version": "14.0.0.0",
    "category": "Treasury",
    "license": "AGPL-3",
    "summary": "Permite el pago multiple de cuentas por cobrar y/o pagar",
    "author": "David",
    "depends":[
        "base",
        "account",
        "account_check_printing"
    ],
    "data": [
        #'data/sequence_data.xml',
        #"security/group_users.xml",
        "security/ir.model.access.csv",
        #"views/nc.xml",
        "views/account_massive_payment_view.xml",
        "views/action_views.xml",
    ],
    "active": True,
    "application": True,
    "installable": True,
}

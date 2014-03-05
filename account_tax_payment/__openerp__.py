# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: account_tax_payment
#    Author: Goran Kliska
#    mail:   gkliskaATgmail.com
#    Copyright (C) 2011- Slobodni programi d.o.o., Zagreb
#              http://www.slobodni-programi.hr
#    Contributions: 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#import 

{
    "name": "Tax deductible on payment",
    "description" : """

Author: Goran Kliska @ Slobodni programi d.o.o.
        http://www.slobodni-programi.hr
Contributions:

Description:
 Manages taxes that are deductible only when payed & reconciled.
 Adds new field "Tax payment journal" for journal, and two new fields
 in Tax Code For Storno/Contra Tax Code used for additional posting
 on reconciliation of original invoice.
 Additional posting is deleted on unreconciliation.


""",
    "version" : "0.1",
    "author" : "Slobodni programi d.o.o.",
    "category" : "Localisation/Croatia",
    "website": "http://www.slobodni-programi.hr",

    'depends': [
                'account',
                'account_storno',
                ],
    'init_xml': [],
    'update_xml': [ 
                   'security/ir.model.access.csv',
                   'account_view.xml',
                   ],
    "demo_xml" : [],
    'test' : [],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

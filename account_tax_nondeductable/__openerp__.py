# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: l10n_hr_tax
#    Author: Goran Kliska
#    mail:   gkliskaATgmail.com
#    Copyright (C) 2011- Slobodni programi d.o.o., Zagreb
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


{
    "name" : "Partialy Non deductable VAT",
    "description" : """
Croatian localisation.
======================

Author: Goran Kliska @ Slobodni programi d.o.o.
        http://www.slobodni-programi.hr
Contributions: 

Description:

This module enables management of partially deductible taxes 
and takes care of tax and bases rounding.
In case of many taxes on invoice line (partially deductable case)
bases are rounded on invoice line level.

Taxes are rounded on Invoice/Tax level instead of OpenERP 6 default 
rounding of taxes on invoice line level.
    
From dictionary:
   nondeductible - not allowable as a deduction
   deductible - acceptable as a deduction (especially as a tax deduction)

In many countries some purchase taxes are only partially deductable.
In Croatia currently we have 
       30% deductable - 70% nondeductable 
   and 70% deductable - 30% nondeductable
   taxes that are posted on different accounts depending on product.

This module adds new fields on product/product group allowing definition of alternative
accounts for Expense/Income that are used for posting nondeductible part of base.  

TODO:
  Make rounding of taxes/bases optional/selectable on tax or tax code level.       


""",
    "version" : "11.1",
    "author" : "Slobodni programi d.o.o.",
    "category" : "Localisation/Croatia",
    "website": "http://www.slobodni-programi.hr",

    'depends': [
               'account_storno',
                ],
    'init_xml': [],
    'update_xml': [
                   'security/ir.model.access.csv',
                   'account_view.xml',
                   'product_view.xml',
                   ],
    "demo_xml" : [],
    'test' : [],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

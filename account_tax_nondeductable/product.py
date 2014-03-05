# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: l10n_hr_nondeductable
#    Author: Goran Kliska
#    mail:   gkliskaATgmail.com
#    Copyright (C) 2011- Slobodni programi d.o.o., Zagreb
#               http://www.slobodni-programi.hr
#
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

from openerp.osv import fields, orm


class product_category(orm.Model):
    _inherit = "product.category"
    _columns = {
        'code': fields.char('Code', size=64, select=1),

        'property_account_income2_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Income Account 2",
            view_load=True,
            help="Alternative account for product can be used to value part of nondeductable tax base sales for this product category"),

        'property_account_expense2_categ': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expense Account 2",
            view_load=True,
            help="Alternative account for product can be used to value part of tax base expenses for this product category"),
        }

#        'account_expense2_categ_id': fields.many2one('account.account', "Expense Account 2",
#                                    help="Alternative account for product can be used to value part of tax base expenses for this product category"),
#        'account_income2_categ_id': fields.many2one('account.account', "Income Account 2",
#                                    help="Alternative account for product can be used to value part of nondeductable tax base sales for this product category"),
#        'account_income2_id': fields.many2one('account.account', "Income Account 2",
#                              help="This account will be used for invoices to value part of nondeductable tax base sales for the current product category"),
#        'account_expense2_id': fields.many2one('account.account', "Expense Account 2",
#                              help="This account will be used for invoices to value part of nondeductable tax base expenses for the current product category"),


class product_template(orm.Model):
    _inherit = 'product.template'
    _columns = {
        'account_map_ids': fields.one2many('product.account.map', 'product_id', 'Account Mapping'),

        'property_account_income2': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Income Account 2",
            view_load=True,
            help="This account will be used for invoices to value part of nondeductable tax base sales for the current product category"),
        'property_account_expense2': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Expense Account 2",
            view_load=True,
            help="This account will be used for invoices to value part of nondeductable tax base expenses for the current product category"),
    }

    def get_product_accounts2(self, cr, uid, product_id, context=None):
        res = {}
        #res = super( product_product ,self).get_product_accounts( cr, uid, product_id, context=None)
        if not product_id:
            return res
        product_obj = self.pool.get('product.template')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)

        if product:
            # from account
            a = product.product_tmpl_id.property_account_income.id
            if not a:
                a = product.categ_id.property_account_income_categ.id
            res['account_income'] = a

            a = product.product_tmpl_id.property_account_expense.id
            if not a:
                a = product.categ_id.property_account_expense_categ.id
            res['account_expense'] = a

            # from account
            a = product.product_tmpl_id.property_account_income2.id
            if not a:
                a = product.categ_id.property_account_income2_categ.id
            res['account_income2'] = a

            a = product.product_tmpl_id.property_account_expense2.id
            if not a:
                a = product.categ_id.property_account_expense2_categ.id
            res['account_expense2'] = a

            #TO_THINK_ABOUT:method get_product_accounts() from module stock
        return res

    def map_account(self, cr, uid, product_id, account_id, context=None):
        if not product_id:
            return account_id
        if type(product_id) == type(1):  # int?what?
            product = self.pool.get('product.template').browse(cr, uid, product_id, context=context)
        else:
            product = product_id

        for position in product.account_map_ids:
            if position.account_source_id.id == account_id:
                account_id = position.account_dest_id and position.account_dest_id.id or account_id
                break
        return account_id


class product_account_map(orm.Model):
    _name = 'product.account.map'
    _description = 'Product Account Mapping'
    _rec_name = 'account_source_id'
    _columns = {
        'product_id': fields.many2one('product.template', 'Product', required=True, ondelete='cascade'),
        'account_source_id': fields.many2one('account.account', 'Account Source', required=True),
        'account_dest_id': fields.many2one('account.account', 'Account Destination',
                                           domain=[('type', '!=', 'view'), ('type', '!=', 'consolidation')])
    }

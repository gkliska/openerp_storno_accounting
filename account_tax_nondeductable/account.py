# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: l10n_hr....
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

import decimal_precision as dp
import time
from osv import fields, osv
from tools.translate import _
import pooler


class account_tax(osv.osv):
    _inherit = 'account.tax'
    _columns = {
        'base_account': fields.selection([('product_1', 'Product'),
                                           ('product_2', 'Product 2'),
                                           ('tax_base', 'Tax definition'),
                                              ],
                                           'Base Account source.', required=True,
                                           help="Base Account source for this tax. /Product/ will use account from product/invoice line,\n /Product 2/ will force usage of alternative account from product/product category,\n /Tax definition/ will use Base Accounts from tax definition."),
        'base_account_collected_id': fields.many2one('account.account', 'Invoice Base Account', help=''),
        'base_account_paid_id': fields.many2one('account.account', 'Refund Base Account', help=''),
    }
    _defaults = {
    'base_account': 'product_1',
    }

    def _unit_compute(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None, quantity=0):
        res = super(account_tax, self)._unit_compute(cr, uid, taxes, price_unit, address_id, product, partner, quantity)
        product_obj = self.pool.get('product.template')
        tax_obj = self.pool.get('account.tax')
        for tax in res:
            #product account mapping
            if product:
                tax['account_collected_id'] = product_obj.map_account(cr, uid, product, tax['account_collected_id'])
                tax['account_paid_id'] = product_obj.map_account(cr, uid, product, tax['account_collected_id'])
            if tax['id']:
                tax_data = tax_obj.browse(cr, uid, tax['id'])
                tax['base_account'] = tax_data.base_account
                tax['base_account_collected_id'] = tax_data.base_account_collected_id and tax_data.base_account_collected_id.id or False
                tax['base_account_paid_id']      = tax_data.base_account_paid_id      and tax_data.base_account_collected_id.id or False

            # TODO - move in some l10n_hr... module
            if tax['id']:
                tax1 = self.pool.get('account.tax').read(cr, uid, tax['id'],
                                                         ['name', 'description'],
                                                         context={'lang': 'hr_HR'})
                tax['name'] = tax1['name'] or tax1['description']

        return res

    def _unit_compute_inv(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None):
        res = super(account_tax, self)._unit_compute_inv(cr, uid, taxes, price_unit, address_id, product, partner)
        product_obj = self.pool.get('product.template')
        tax_obj = self.pool.get('account.tax')
        for tax in res:
            if product:  # product account mapping
                tax['account_collected_id'] = product_obj.map_account(cr, uid, product, tax['account_collected_id'])
                tax['account_paid_id'] = product_obj.map_account(cr, uid, product, tax['account_collected_id'])
            if tax['id']:
                tax_data = tax_obj.browse(cr, uid, tax['id'])
                tax['base_account'] = tax_data.base_account 
                tax['base_account_collected_id'] = tax_data.base_account_collected_id and tax_data.base_account_collected_id.id or False
                tax['base_account_paid_id'] = tax_data.base_account_paid_id and tax_data.base_account_collected_id.id or False
        return res

    def _compute(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.
        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
        res = self._unit_compute(cr, uid, taxes, price_unit, address_id, product, partner, quantity)
        if not res:
            return res
        total = 0.0
        base_total = 0.0
        base_max_ind = res[0]
        base_max = base_max_ind['price_unit']

        tax_total_rounded = 0.0
        tax_total = 0.0
        tax_max_ind = res[0]
        tax_max = base_max_ind['amount']

        precision_pool = self.pool.get('decimal.precision')
        account_prec = precision_pool.precision_get(cr, uid, 'Account')

        for r in res:
            if r.get('balance', False):
                r['amount'] = round(r.get('balance', 0.0) * quantity, account_prec) - total
            else:
                #don't round tax on each line  #r['amount'] = round(r.get('amount', 0.0) * quantity, account_prec)
                r['amount'] = r.get('amount', 0.0) * quantity
                total += r['amount']

            #get rounded and not rounded sums of taxes
            tax_total += r['amount']
            tax_total_rounded += round(r.get('amount', 0.0), account_prec)

            # round & sum bases, later adjust
            r['price_unit'] = round(r.get('price_unit', 0.0), account_prec)
            base_total += r['price_unit']
            if abs(r['price_unit']) > abs(base_max):
                base_max = r['price_unit']
                base_max_ind = r

        # for more than 1 tax on one line - adjust rounding
        #TODO new field in account.tax to mark one tax as "collect rounding" like in Italian localization
        #find tax with largest amount >0.0 and adjust that one
        tax_rounding_diff = tax_total - tax_total_rounded
        if tax_rounding_diff > 0.005 and tax_rounding_diff < 0.014:
            if abs(base_max_ind.get('amount', 0.0)) > 0.0:
                for r in res:
                    r['amount'] = round(r.get('amount', 0.0), account_prec)
                base_max_ind['amount'] = round(base_max_ind['amount'] + tax_rounding_diff, 6)  # better unrounded

        #adjust base
        diff = round(price_unit - base_total, 4)
        base_max_ind['price_unit'] = round(base_max_ind['price_unit'] + diff, 6)  # better unrounded
        return res

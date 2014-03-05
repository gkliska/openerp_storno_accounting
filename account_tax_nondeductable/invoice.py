# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Author: Goran Kliska
#    mail:   gkliskaATgmail.com
#    Copyright (C) 2011- Slobodni programi d.o.o., Zagreb
#               http://www.slobodni-programi.hr
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
import decimal_precision as dp
import time
from tools.translate import _
import pooler


class account_invoice_line(orm.Model):
    _inherit = 'account.invoice.line'

    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'account2_id': fields.many2one('account.account', 'Account 2', required=False,
                                       domain=[('type', '<>', 'view'), ('type', '<>', 'closed')],
                                       help="Second account related to the selected product."),
        }

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, currency_id=False, context=None, company_id=None):
        res_prod = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, currency_id=currency_id, context=context)
        if product:  # get second account related to product
            res = self.pool.get('product.product').browse(cr, uid, product, context=context)
            if type in ('out_invoice', 'out_refund'):
                a2 = res.product_tmpl_id.property_account_income2.id
                if not a2:
                    a2 = res.categ_id.property_account_income2_categ.id
            else:
                a2 = res.product_tmpl_id.property_account_expense2.id
                if not a2:
                    a2 = res.categ_id.property_account_expense2_categ.id
            if a2:
                if fposition_id:
                    fp_brw = self.pool.get('account.fiscal.position').browse(cr, uid, fposition_id)
                    a2 = self.pool.get('account.fiscal.position').map_account(cr, uid, fp_brw, a2)
                res_prod['value']['account2_id'] = a2
        return res_prod

    def onchange_account2_id(self, cr, uid, ids, product_id, partner_id, inv_type, fposition_id, account_id, account2_id):
        res12 = {}
        if account_id:
            res1 = super(account_invoice_line, self).onchange_account_id(cr, uid, ids, product_id, partner_id, inv_type, fposition_id, account_id)
            # def onchange_account_id(self, cr, uid, ids, product_id, partner_id, inv_type, fposition_id, account_id):
            # res1 = super(account_invoice_line, self).onchange_account_id(cr, uid, ids, fposition_id, account_id)
        if account2_id:
            taxes = self.pool.get('account.account').browse(cr, uid, account2_id).tax_ids
            fpos = fposition_id and self.pool.get('account.fiscal.position').browse(cr, uid, fposition_id) or False
            res2 = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)
            if not account_id:
                return {'value': {'invoice_line_tax_id': res2}}
            return {'value': {'invoice_line_tax_id': res2 + res1['value']['invoice_line_tax_id']}}
        return res12

    # Copy of account.invoice.py. New accounts for nondeductable part of base
    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = []
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        company_currency = inv.company_id.currency_id.id

        for line in inv.invoice_line:
            mres = self.move_line_get_item(cr, uid, line, context)
            rest = abs(line.price_subtotal)  # KGB added
            if not mres:
                continue
            #res.append(mres)          #KGB commented out
            #tax_code_found= False     #KGB commented out
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id,
                    (line.price_unit * (1.0 - (line['discount'] or 0.0) / 100.0)),
                    line.quantity, inv.address_invoice_id.id, line.product_id,
                    inv.partner_id)['taxes']:

                base_code_id = None  # KGB added
                if inv.type in ('out_invoice', 'in_invoice'):
                    base_code_id = tax['base_code_id']  # KGB added
                    base_amount = tax['price_unit'] * tax['base_sign'] * line.quantity
                else:
                    base_code_id = tax['ref_base_code_id']  # KGB added
                    #???base_amount = line.price_subtotal * tax['ref_base_sign']
                    base_amount = tax['price_unit'] * tax['ref_base_sign'] * line.quantity

                if (not base_code_id) and (not cur_obj.is_zero(cr, uid, inv.company_id.currency_id, base_amount)):
                    continue

                rest -= abs(base_amount)
                res.append(self.move_line_get_item(cr, uid, line, context))
                res[-1]['price'] = tax['price_unit'] * line.quantity
                res[-1]['tax_code_id'] = base_code_id
                res[-1]['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, base_amount,
                                                         context={'date': inv.date_invoice,
                                                                  'force_currency_inv_rate': inv.ccurrency_rate,
                                                                  })

                tax_base = tax_obj.browse(cr, uid, tax['id'])  # when part of the base is posted to another account
                base_account_id = res[-1]['account_id']  # default account for base === (tax_base.base_account == 'product1')
                if tax_base.base_account == 'tax_base':
                    if tax_base.base_account_collected_id and inv.type in ('out_invoice', 'out_refund'):
                        base_account_id = tax_base.base_account_collected_id.id
                    if tax_base.base_account_paid_id and inv.type in ('in_invoice', 'in_refund'):
                        base_account_id = tax_base.base_account_paid_id.id
                if tax_base.base_account == 'product_2' and line.account2_id:
                    base_account_id = line.account2_id.id
                if tax_base.base_account == 'product_2' and not line.account2_id:
                    # TODO use get_product_accounts2
                    product_accounts = self.pool.get('product.template').get_product_accounts2(cr, uid, line.product_id.id, context=None)
                    base_account_id = res[-1]['account2_id']  # account2 for base when tax_base.base_account == 'product_2')
                    if not base_account_id:
                        if inv.type in ('in_invoice', 'in_refund'):
                            base_account_id = product_accounts.get('property_account_expense2', False)
                        if inv.type in ('out_invoice', 'out_refund'):
                            base_account_id = product_accounts.get('property_account_income2', False)

                res[-1]['account_id'] = base_account_id
                res[-1]['price'] = tax['price_unit'] * line.quantity
                res[-1]['tax_code_id'] = base_code_id
                res[-1]['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, base_amount,
                                                         context={'date': inv.date_invoice,
                                                                  'force_currency_inv_rate': inv.ccurrency_rate,
                                                                  })
            if len(res) > 0 and not cur_obj.is_zero(cr, uid, inv.company_id.currency_id, rest):
                if res[-1]['price'] < 0.0:
                    rest = -rest
                res[-1]['price'] = rest
                res[-1]['tax_code_id'] = False
                res[-1]['tax_amount'] = 0.0
        return res

    def move_line_get_item(self, cr, uid, line, context=None):
        res = super(account_invoice_line, self).move_line_get_item(cr, uid, line, context=context)
        res['account2_id'] = line.account2_id.id
        return res


class account_invoice_tax(orm.Model):
    _inherit = "account.invoice.tax"

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id.id

        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id,
                                           (line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                                            line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id)['taxes']:
                val = {}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = tax['price_unit'] * line['quantity']

                if inv.type in ('out_invoice', 'in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'],
                                                         context={'date': inv.date_invoice or time.strftime('%Y-%m-%d'),
                                                                   'force_currency_inv_rate': inv.ccurrency_rate,
                                                                   },
                                                         round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'],
                                                        context={'date': inv.date_invoice or time.strftime('%Y-%m-%d'),
                                                                  'force_currency_inv_rate': inv.ccurrency_rate,
                                                                  },
                                                        round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    #KGB start
                    if not tax['account_collected_id']:
                        if tax['base_account'] == 'product_2' and line.account2_id:
                            val['account_id'] = line.account2_id.id
                        if tax['base_account'] == 'tax_base' and tax['base_account_collected_id']:
                            val['account_id'] = tax['base_account_collected_id']
                    #KGB end
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'],
                                                          context={'date': inv.date_invoice or time.strftime('%Y-%m-%d'),
                                                                   'force_currency_inv_rate': inv.ccurrency_rate,
                                                                   },
                                                          round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'],
                                                         context={'date': inv.date_invoice or time.strftime('%Y-%m-%d'),
                                                                  'force_currency_inv_rate': inv.ccurrency_rate,
                                                                  },
                                                         round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    #KGB start
                    if not tax['account_collected_id']:
                        if tax['base_account'] == 'product_2' and line.account2_id:
                            val['account_id'] = line.account2_id.id
                        if tax['base_account'] == 'tax_base' and tax['base_account_paid_id']:
                            val['account_id'] = tax['base_account_paid_id']
                    #KGB end

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped


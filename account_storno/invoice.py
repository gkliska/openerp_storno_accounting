# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: account_storno
#    Author: Goran Kliska
#    mail:   gkliskaATgmail.com
#    Copyright (C) 2013- Slobodni programi d.o.o., Zagreb
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
from tools.translate import _


class account_invoice(orm.Model):
    _inherit = "account.invoice"

    def action_move_create(self, cr, uid, ids, context=None):
        """Creates invoice related analytics and financial move lines
           We have to go one by one to inject invoice to line_get_convert
        """
        if context is None:
            context = {}
        for inv in self.browse(cr, uid, ids, context=context):
            context.update({'brw_invoice': inv})
            super(account_invoice, self).action_move_create(cr, uid, [inv.id], context=context)
        return True

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice, self).line_get_convert(cr, uid, x, part, date, context=context)
        if context is None:
            context = {}
        invoice = context.get('brw_invoice', False)
        if invoice and invoice.journal_id.posting_policy == 'storno':
            credit = debit = 0.0
            if invoice.type in ('out_invoice', 'out_refund'):
                if x.get('type', 'src') in ('dest'):
                    debit = x['price']  # for OUT_invoice dest (tot. amount goes to debit)
                else:  # in('src','tax')
                    credit = x['price'] * (-1)
            else:  # in ('in_invoice', 'in_refund')
                if x.get('type', 'src') in ('dest'):
                    credit = x['price'] * (-1)
                else:
                    debit = x['price']
            res['debit'] = debit
            res['credit'] = credit
            if invoice and invoice.currency_id.id != invoice.company_id.currency_id.id:
                if abs(res['tax_amount']) > 0.00:  # KGB tired, alternative implementation with pg trigger
                    res['tax_amount'] = res['debit'] + res['credit']
        return res

    def group_lines(self, cr, uid, iml, line, inv):
        """Merge account move lines (and hence analytic lines) if invoice line hashcodes are equals"""
        if inv.journal_id.group_invoice_lines:
            if inv.journal_id.posting_policy == 'contra':
                return super(account_invoice, self).group_lines(cr, uid, iml, line, inv)
            if inv.journal_id.posting_policy == 'storno':
                line2 = {}
                for x, y, l in line:
                    hash = self.inv_line_characteristic_hashcode(inv, l)
                    side = abs(l['credit']) > 0.0 and 'credit' or 'debit'
                    if l['credit'] == 0.00 and l['debit'] == 0:
                        tmp_c = '-'.join((hash, 'credit'))
                        side = (tmp_c in line2) and 'credit' or side
                    tmp = '-'.join((hash, side))
                    if tmp in line2:
                        line2[tmp]['debit'] += l['debit'] or 0.0
                        line2[tmp]['credit'] += l['credit'] or 0.00
                        line2[tmp]['tax_amount'] += l['tax_amount']
                        line2[tmp]['analytic_lines'] += l['analytic_lines']
                        line2[tmp]['amount_currency'] += l['amount_currency']
                        line2[tmp]['quantity'] += l['quantity']
                    else:
                        line2[tmp] = l
                line = []
                for key, val in line2.items():
                    line.append((0, 0, val))
        return line

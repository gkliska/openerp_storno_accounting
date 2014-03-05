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

from openerp.osv import fields, orm
import time
from tools.translate import _

JOURNAL_INVOICES = ('sale', 'sale_refund', 'purchase', 'purchase_refund')
JOURNAL_PAYMENTS = ('cash', 'bank')


class account_move_line(orm.Model):
    _inherit = 'account.move.line'

    def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False,
                  writeoff_period_id=False, writeoff_journal_id=False, context=None):

        if context is None:
            context = {}
        journal_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')

        lines = self.browse(cr, uid, ids, context=context)

        payments_ml = []  # [pml,pml...]
        invoices = {}  # {'invoice_id':[iml,iml...]}
        tot_payment = 0.0

        for line in lines:
            if (line.partner_id and line.journal_id.type in JOURNAL_INVOICES):
                # examine move_lines of each lines.move_id.move_lines!
                for iml in line.move_id.line_id:
                    if iml.tax_code_id and iml.tax_code_id.payment_tax_code_id:
                        invoices.setdefault(iml.invoice.id, []).append(iml)
            if (line.partner_id and line.journal_id.type in JOURNAL_PAYMENTS):
                tot_payment = line.debit + line.credit
                payments_ml.append(line)

        if len(invoices) == 0:  # nothing to do
            res = super(account_move_line, self).reconcile(cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=None)
            return res

        new_move_ids = []
        for pml in payments_ml:
            move_journal_id = pml.journal_id.tax_payment_journal_id    \
                              and pml.journal_id.tax_payment_journal_id.id \
                              or  pml.journal_id.id
            for invoice in invoices:
                if invoices[invoice][0].journal_id.tax_payment_journal_id:
                    move_journal_id = invoices[invoice][0].journal_id.tax_payment_journal_id.id
                move_id = move_obj.create(cr, uid, {
                            'journal_id': move_journal_id,
                            'period_id': pml.period_id.id,
                            'date': pml.date,  # or today?
                            'name': pml.name,  # + _('- tax') ?
                            }, context=context)

                new_move_ids.append(move_id)
                # iml_ids = [i.id for i in invoices]
                for iml in invoices[invoice]:
                    new_line = self.copy_data(cr, uid, iml.id)
                    # 1. storno or contra of original tax code
                    if iml.tax_code_id.posting_policy == 'storno':
                        tax_amount = new_line['tax_amount'] * (-1)
                        credit, debit = new_line['credit'] * (-1), new_line['debit'] * (-1)
                    else:
                        tax_amount = -new_line['tax_amount']
                        credit, debit = new_line['debit'], new_line['credit']  # swap

                    new_line['move_id'] = move_id
                    # new_line['tax_code_id'] = iml.tax_code_id.payment_tax_code_id.id
                    new_line['credit'] = credit or 0.0
                    new_line['debit'] = debit or 0.0
                    new_line['tax_amount'] = tax_amount
                    new_line['name'] = iml.name
                    new_line['date'] = pml.date
                    new_line['ref'] = pml.ref
                    new_line['journal_id'] = move_journal_id
                    new_line['period_id'] = pml.period_id.id
                    # new_line['analytic_account_id'] = False

                    # Questionable ???
                    new_line['statement_id'] = pml.statement_id.id

                    ids.append(self.create(cr, uid, new_line, context))

                    # 2.Now contra or storno of original
                    if iml.tax_code_id.payment_tax_code_id.posting_policy == 'storno':
                        tax_amount = -tax_amount
                        credit, debit = -credit, -debit
                    else:
                        tax_amount = -tax_amount
                        credit, debit = debit, credit  # swap
                    new_line['tax_code_id'] = iml.tax_code_id.payment_tax_code_id.id
                    new_line['tax_amount'] = tax_amount
                    new_line['credit'] = credit or 0.0
                    new_line['debit'] = debit or 0.0
                    if iml.tax_code_id.payment_account_id:
                        new_line['account_id'] = iml.tax_code_id.payment_account_id.id
                    ids.append(self.create(cr, uid, new_line, context))

                # Post AFTER reconciliation move_obj.post(cr, uid, [move_id], context)
                # raise osv.except_osv(_('Error !'), _('Additional move for deductable tax on payment failed to validate. Check tax settings.'))

        context['fy_closing'] = True  # not exactly true - cheating to avoid reconcile constraints
        reconcile_id = super(account_move_line, self).reconcile(cr, uid, ids, type='auto_tax', context=context)
        # remember additional moves
        reconcile_move_obj = self.pool.get('account.move.reconcile.move')
        for move_id in new_move_ids:
            reconcile_move_obj.create(cr, uid,
                                      { 'name': 'auto deductible tax',
                                        'reconcile_id': reconcile_id,
                                        'move_id': move_id,
                                        'type': 'tax_payment',
                                      }, context)
        move_obj.post(cr, uid, new_move_ids, context)
        return reconcile_id

    def _remove_move_reconcile(self, cr, uid, move_ids=[], context=None):
        # Find reconcile ids
        obj_move_line = self.pool.get('account.move.line')
        obj_move_rec = self.pool.get('account.move.reconcile')

        unlink_ids = []
        if not move_ids:
            return True
        recs = obj_move_line.read(cr, uid, move_ids, ['reconcile_id', 'reconcile_partial_id'])
        full_recs = filter(lambda x: x['reconcile_id'], recs)
        rec_ids = [rec['reconcile_id'][0] for rec in full_recs]
        part_recs = filter(lambda x: x['reconcile_partial_id'], recs)
        part_rec_ids = [rec['reconcile_partial_id'][0] for rec in part_recs]
        unlink_ids += rec_ids
        unlink_ids += part_rec_ids
        # if len(unlink_ids) > 0 :
        obj_rec_move = self.pool.get('account.move.reconcile.move')
        obj_move = self.pool.get('account.move')
        rec_move_ids = obj_rec_move.search(cr, uid, [('reconcile_id', 'in', unlink_ids),
                                                     ('type', 'in', ['tax_payment', ])
                                                    ])
        # then call super just in case :) for obj_move_rec.unlink(cr, uid, unlink_ids)
        res = super(account_move_line, self)._remove_move_reconcile(cr, uid, move_ids, context)

        # remove additional moves (better to reverse them? if period is closed?)
        for rec_move in obj_rec_move.browse(cr, uid, rec_move_ids):
            obj_move.button_cancel(cr, uid, [rec_move.move_id.id])
            obj_move.unlink(cr, uid, [rec_move.move_id.id])
        obj_rec_move.unlink(cr, uid, rec_move_ids)

        return res

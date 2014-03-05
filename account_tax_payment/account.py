# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Module: account_tax_payment
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

from openerp.osv import fields, orm
import time
from tools.translate import _


class account_journal(orm.Model):
    _inherit = "account.journal"
    _columns = {
        'tax_payment_journal_id': fields.many2one('account.journal', 'Tax payment journal',
                                  help="General journal for additional posting of taxes on reconciliation(payment).",
                                                 ),
        #'tax_payment_position_id': fields.many2one('account.fiscal.position','Tax payment fiscal position'),
                }


class account_tax_code(orm.Model):
    _inherit = "account.tax.code"
    _columns = {
        'payment_tax_code_id': fields.many2one('account.tax.code', 'Payment tax code', help='Contra tax code for additional posting on reconciliation.'),
        'payment_account_id': fields.many2one('account.account', 'Account',
                                              #required=True,
                                              domain=[('type', '<>', 'consolidation'), ('type', '<>', 'view'), ('type', '<>', 'closed')]
                                              ),
        'posting_policy': fields.selection([
                               ('contra', 'Contra (debit<->credit)'),
                               ('storno', 'Storno (-)'),
                               ],
                             'Storno or Contra', size=16, required=True,
                             help="Contra swaps credit and debit side. Storno allows minus postings."),
    }
    _defaults = {'posting_policy': 'storno', }


# this object is used only to record additional moves done by reconciliation
# in order to delete/reverse those moves on unreconciliation 
class account_move_reconcile_move(orm.Model):
    _name = "account.move.reconcile.move"
    _description = "Account Reconciliation Moves"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'reconcile_id': fields.many2one('account.move.reconcile', 'Reconcile', select=1, readonly=True),
        'move_id': fields.many2one('account.move', 'Move',  select=1, readonly=True,),
        'type': fields.selection([
                                    ('tax_payment', 'Deductible on payment'),
                                    ('write_off', 'Write off'),
                                    ('currency diff', 'Currency diff.'),
                                ], 'Type of reconcile move', size=16, required=True,
                         ),
    }


class account_move_reconcile(orm.Model):
    _inherit = "account.move.reconcile"
    _columns = {
        'reconcile_move_ids': fields.one2many('account.move.reconcile.move', 'reconcile_id', 'Additional moves'),
        }

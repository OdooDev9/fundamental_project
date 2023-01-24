
from odoo import models, api, _

class AccountCashFlowReportInherit(models.AbstractModel):
    _inherit = 'account.cash.flow.report'

    @api.model
    def _get_bu_br_journals(self):
        journals = self.env['account.journal'].search([('type', 'in', ('bank', 'cash')), ('bu_br_id', '=', self.env.user.current_bu_br_id.id)])
        return journals

    @api.model
    def _get_filter_journals(self):
        # OVERRIDE to filter only bank / cash journals.
        journals = self.env['account.journal'].search([
            ('company_id', 'in', self.env.companies.ids),
            ('type', 'in', ('bank', 'cash')),
            ('bu_br_id', '=', self.env.user.current_bu_br_id.id)
        ], order='company_id, name')
        if self.env.user.user_type_id in ['bu', 'br']:
            journals = self.env['account.journal'].search([('bu_br_id', '=', self.env.user.current_bu_br_id.id)])
        return journals

    @api.model
    def _get_liquidity_move_ids(self, options):
        ''' Retrieve all liquidity moves to be part of the cash flow statement and also the accounts making them
        such moves.

        :param options: The report options.
        :return:        payment_move_ids: A tuple containing all account.move's ids being the liquidity moves.
                        payment_account_ids: A tuple containing all account.account's ids being used in a liquidity journal.
        '''
        new_options = self._get_options_current_period(options)
        selected_journals = self._get_options_journals(options)

        # Fetch liquidity accounts:
        # Accounts being used by at least one bank / cash journal.
        selected_journal_ids = [j['id'] for j in selected_journals]
        if selected_journal_ids:
            where_clause = "account_journal.id IN %s"
            where_params = [tuple(selected_journal_ids)]
        else:
            bu_br_journal_ids = self._get_bu_br_journals().ids
            where_clause = "account_journal.id IN %s"
            where_params = [tuple(bu_br_journal_ids)]

        self._cr.execute('''
            SELECT array_remove(ARRAY_AGG(DISTINCT default_account_id), NULL),
                   array_remove(ARRAY_AGG(DISTINCT apml.payment_account_id), NULL),
                   array_remove(ARRAY_AGG(DISTINCT rc.account_journal_payment_debit_account_id), NULL),
                   array_remove(ARRAY_AGG(DISTINCT rc.account_journal_payment_credit_account_id), NUll)
            FROM account_journal
            JOIN res_company rc ON account_journal.company_id = rc.id
            LEFT JOIN account_payment_method_line apml ON account_journal.id = apml.journal_id
            WHERE ''' + where_clause, where_params)

        res = self._cr.fetchall()[0]
        payment_account_ids = set((res[0] or []) + (res[1] or []) + (res[2] or []) + (res[3] or []))

        if not payment_account_ids:
            return (), ()

        # Fetch journal entries:
        # account.move having at least one line using a liquidity account.
        payment_move_ids = set()
        tables, where_clause, where_params = self._query_get(new_options, [('account_id', 'in', list(payment_account_ids))])

        query = '''
            SELECT DISTINCT account_move_line.move_id
            FROM ''' + tables + '''
            WHERE ''' + where_clause + '''
            GROUP BY account_move_line.move_id
        '''
        self._cr.execute(query, where_params)
        for res in self._cr.fetchall():
            payment_move_ids.add(res[0])

        return tuple(payment_move_ids), tuple(payment_account_ids)

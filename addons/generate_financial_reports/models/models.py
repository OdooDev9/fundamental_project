# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import *

class AccountFinancialHtmlReport(models.Model):
    _inherit = 'account.financial.html.report'
    bu_br_id = fields.Many2one('business.unit', string='Business')

class AccountFinancialHtmlReportLines(models.Model):
    _inherit = 'account.financial.html.report.line'
    bu_br_id = fields.Many2one('business.unit', string='Business')

class BusinessUnit(models.Model):
    _inherit = 'business.unit'

    def generate_pnl_report(self):
        unit_code = self.code
        main_model = self.env['account.financial.html.report']
        line_model = self.env['account.financial.html.report.line']

        bu_domain = "('account_id.bu_br_id', '=', %s)" % self.id

        # CODEs
        # Net Profit
        NEP = 'NEP_%s' % (unit_code)
        # Operation Income
        OPINC = 'OPINC_%s' % (unit_code)
        # Other Income
        OIN = 'OIN_%s' % (unit_code)
        # Cost of Revenue
        COS = 'COS_%s' % (unit_code)
        #Less Expense
        LEX = 'LEX_%s' % (unit_code)
        # Expense
        EXP = 'EXP_%s' % (unit_code)
        # Depreciation
        DEP = 'DEP_%s' % (unit_code)
        # Income
        INC = 'INC_%s' % (unit_code)
        # Gross Profit
        GRP = 'GRP_%s' % (unit_code)

        # Create Main
        main_data = {
            'bu_br_id': self.id,
            'name': 'Profit and Loss[%s]' % (self.code),
            'analytic': True,
            'unfold_all_filter': True,
            'show_journal_filter': True,
            'parent_id': self.env.ref('account.account_reports_legal_statements_menu').id
        }
        # print("main_data ===>", main_data)
        
        # Create report 
        report = main_model.create(main_data)

        # Create Net Profit Layer
        net_profit_data = {
            'bu_br_id': self.id,
            'name': 'Net Profit[%s]' % (self.code),
            'code': NEP,
            'financial_report_id': report.id,
            'formulas': '%s + %s - %s - %s - %s' % (OPINC, OIN, COS, EXP, DEP),
            'sequence':3,
            'level':0,
        }
        # print("net_profit ===>", net_profit_data)
        net_profit = line_model.create(net_profit_data)
        # print("net_profit ===>", net_profit)

        # Create Income Layer
        income_data = {
            'bu_br_id': self.id,
            'name': 'Income[%s]' % (self.code),
            'code': INC,
            'formulas': '%s + %s' % (OPINC, OIN),
            'control_domain': "[('account_id.user_type_id.internal_group', '=', 'income'), %s]" % (bu_domain),
            'parent_id': False,
            'financial_report_id': report.id,
            'sequence':1,
            'level':0,
        }
        # print("income ===>", income_data)
        income = line_model.create(income_data)

        # Create Gross Profit Layer
        gross_profit_data = {
            'bu_br_id': self.id,
            'name': 'Gross Profit[%s]' % (self.code),
            'code': GRP,
            'formulas': '%s - %s' % (OPINC, OIN),
            'parent_id': income.id,
            'sequence': 1,
            'level': 2,
        }
        # print("gross_profit_data ===>", gross_profit_data)
        gross_profit = line_model.create(gross_profit_data)

        # Create Operating Income
        data_account_type_revenue = self.env.ref('account.data_account_type_revenue')
        opreating_income_data = {
            'bu_br_id': self.id,
            'name': 'Operating Income[%s]' % (self.code),
            'code': OPINC,
            'formulas': '-sum',
            'parent_id': gross_profit.id,
            'domain': "[('account_id.user_type_id', '=', %s),%s]" % (data_account_type_revenue.id, bu_domain),
            'groupby': 'account_id',
            'sequence': 1,
            'level': 3,
        }
        # print("opreating_income_data ===>", opreating_income_data)
        opreating_income = line_model.create(opreating_income_data)

        # Create Cost of Revenue
        data_account_type_direct_costs = self.env.ref('account.data_account_type_direct_costs')
        cost_of_revenue_data = {
            'bu_br_id': self.id,
            'name': 'Cost of Revenue[%s]' % (self.code),
            'code': COS,
            'formulas': 'sum',
            'parent_id': gross_profit.id,
            'domain': "[('account_id.user_type_id', '=', %s),%s]" % (data_account_type_direct_costs.id, bu_domain),
            'groupby': 'account_id',
            'sequence': 1,
            'green_on_positive': False,
            'level': 3,
        }
        # print("cost_of_revenue_data ===>", cost_of_revenue_data)
        cost_of_revenue = line_model.create(cost_of_revenue_data)

        # Create Other Income
        data_account_type_other_income = self.env.ref('account.data_account_type_other_income')
        other_income_data = {
            'bu_br_id': self.id,
            'name': 'Other Income[%s]' % (self.code),
            'code': OIN,
            'formulas': '-sum',
            'parent_id': income.id,
            'domain': "[('account_id.user_type_id', '=', %s), %s]" % (data_account_type_other_income.id, bu_domain),
            'groupby': 'account_id',
            'sequence': 2,
            'level': 2,
        }
        # print("other_income_data ===>", other_income_data)
        other_income = line_model.create(other_income_data)        

        # Create Less Expenses
        less_expenses_data = {
            'bu_br_id': self.id,
            'name': 'Expenses[%s]' % (self.code),
            'code': LEX,
            'formulas': '%s + %s' % (EXP, DEP),
            'parent_id': False,
            'control_domain': "[('account_id.user_type_id.internal_group', '=', 'expense'), %s]" % (bu_domain),
            'groupby': 'account_id',
            'sequence': 2,
            'green_on_positive': False,
            'level': 0,
            'financial_report_id': report.id,
        }
        # print("less_expenses_data ===>", less_expenses_data)
        less_expenses = line_model.create(less_expenses_data)

        # Create Expenses
        data_account_type_expenses = self.env.ref('account.data_account_type_expenses')
        expenses_data = {
            'bu_br_id': self.id,
            'name': 'Expenses[%s]' % (self.code),
            'code': EXP,
            'formulas': 'sum',
            'parent_id': less_expenses.id,
            'domain': "[('account_id.user_type_id', '=', %s), %s]" % (data_account_type_expenses.id, bu_domain),
            'groupby': 'account_id',
            'sequence': 1,
            'green_on_positive': False,
            'level': 2,
        }
        # print("expenses_data ===>", expenses_data)
        expenses = line_model.create(expenses_data)

        # Create Depreciation
        data_account_type_depreciation = self.env.ref('account.data_account_type_depreciation')
        depreciation_data = {
            'bu_br_id': self.id,
            'name': 'Depreciation[%s]' % (self.code),
            'code': DEP,
            'formulas': 'sum',
            'parent_id': less_expenses.id,
            'domain': "[('account_id.user_type_id', '=', %s), %s]" % (data_account_type_depreciation.id, bu_domain),
            'groupby': 'account_id',
            'sequence': 2,
            'green_on_positive': False,
            'level': 2,
        }
        # print("depreciation_data ===>", depreciation_data)
        depreciation = line_model.create(depreciation_data)
    
    def generate_balance_sheet_report(self):
        unit_code = self.code
        main_model = self.env['account.financial.html.report']
        line_model = self.env['account.financial.html.report.line']

        bu_domain = "('account_id.bu_br_id', '=', %s)" % self.id

        # CODEs
        # Net Profit
        NEP = 'NEP_%s' % (unit_code)
        
        # <----------- Create Main ----------->
        main_data = {
            'bu_br_id': self.id,
            'name': 'Balance Sheet[%s]' % (self.code),
            'date_range': False,
            'unfold_all_filter': True,
            'show_journal_filter': True,
            'parent_id': self.env.ref('account.account_reports_legal_statements_menu').id
        }
        # print("main_data ===>", main_data)
        
        # Create report 
        report = main_model.create(main_data)


        # ONLY FOR BALANCE SHEET
        # ASSETS
        TA = 'TA_%s' % (unit_code)
        CA = 'CA_%s' % (unit_code)
        BA = 'BA_%s' % (unit_code)
        REC = 'REC_%s' % (unit_code)
        CAS = 'CAS_%s' % (unit_code)
        PRE = 'PRE_%s' % (unit_code)
        FA = 'FA_%s' % (unit_code)
        PNCA = 'PNCA_%s' % (unit_code)
        L = 'L_%s' % (unit_code)
        CL = 'CL_%s' % (unit_code)
        CL1 = 'CL1_%s' % (unit_code)
        CL2 = 'CL2_%s' % (unit_code)
        NL = 'NL_%s' % (unit_code)
        NA = 'NA_%s' % (unit_code)
        EQ = 'EQ_%s' % (unit_code)
        UNAFFECTED_EARNINGS = 'UNAFFECTED_EARNINGS_%s' % (unit_code)
        CURR_YEAR_EARNINGS = 'CURR_YEAR_EARNINGS_%s' % (unit_code)
        CURR_YEAR_EARNINGS_PNL = 'CURR_YEAR_EARNINGS_%s_PNL' % (unit_code)
        CURR_YEAR_EARNINGS_ALLOC = 'CURR_YEAR_EARNINGS_ALLOC_%s' % (unit_code)
        PREV_YEAR_EARNINGS = 'PREV_YEAR_EARNINGS_%s' % (unit_code)
        ALLOCATED_EARNINGS = 'ALLOCATED_EARNINGS_%s' % (unit_code)
        RETAINED_EARNINGS = 'RETAINED_EARNINGS_%s' % (unit_code)
        LE = 'LE_%s' % (unit_code)
        OS = 'OS_%s' % (unit_code)
        
        total_assets_data = {
            'bu_br_id': self.id,
            'name': 'ASSETS[%s]' % (self.code),
            'code': TA,
            'financial_report_id': report.id,
            'formulas': '%s + %s + %s' % (CA, FA, PNCA),
            'sequence':1,
            'level':0,
        }
        total_assets = line_model.create(total_assets_data)
        
        # Current Assets
        
        data_account_type_liquidity = self.env.ref('account.data_account_type_liquidity')
        data_account_type_current_assets = self.env.ref('account.data_account_type_current_assets')
        data_account_type_prepayments = self.env.ref('account.data_account_type_prepayments')
        current_assets_data = {
            'bu_br_id': self.id,
            'name': 'Current Assets[%s]' % (self.code),
            'code': CA,
            'parent_id': total_assets.id,
            'control_domain': """[
                '&', '|', ('account_id.user_type_id', 'in', [%s, %s, %s]),
                     ('account_id.user_type_id.type', '=', 'receivable'), %s
            ]""" % (data_account_type_liquidity.id, data_account_type_current_assets.id, data_account_type_prepayments.id, bu_domain),
            'formulas': '%s + %s + %s + %s' % (BA, REC, CAS, PRE),
            'sequence':1,
            'level':1,
        }      
        current_assets = line_model.create(current_assets_data)  
        
        # Bank and Cash Accounts
        
        BA_accounts_data = {
            'bu_br_id': self.id,
            'name': 'Bank and Cash Accounts[%s]' % (self.code),
            'code': BA,
            'parent_id': current_assets.id,
            'domain': """[
                ('account_id.user_type_id', '=', %s), %s
            ]""" % (data_account_type_liquidity.id, bu_domain),
            'groupby': 'account_id',
            'formulas': 'sum',
            'sequence': 1,
            'level': 2,
        }
        BA_accounts = line_model.create(BA_accounts_data)  

        # Receivables

        receivables_data = {
            'bu_br_id': self.id,
            'name': 'Receivables[%s]' % (self.code),
            'code': REC,
            'parent_id': current_assets.id,
            'domain': """[
                ('account_id.user_type_id.type', '=', 'receivable'), ('account_id.exclude_from_aged_reports', '=', False), %s
            ]""" % (bu_domain),
            'groupby': 'account_id',
            'formulas': 'sum',
            'sequence': 2,
            'level': 2,
        }
        receivables = line_model.create(receivables_data)  

        # Current Assets
        current_assets_s_data = {
            'bu_br_id': self.id,
            'name': 'Current Assets[%s]' % (self.code),
            'code': CAS,
            'parent_id': current_assets.id,
            'domain': """[
                '&', '|', ('account_id.user_type_id', '=', %s), '&', ('account_id.user_type_id.type', '=', 'receivable'), ('account_id.exclude_from_aged_reports', '=', True), %s
            ]""" % (data_account_type_current_assets.id, bu_domain),
            'groupby': 'account_id',
            'formulas': 'sum',
            'sequence': 3,
            'level': 2,
        }
        current_assets_s = line_model.create(current_assets_s_data)

        # Prepayments
        
        prepayment_data = {
            'bu_br_id': self.id,
            'name': 'Prepayments[%s]' % (self.code),
            'code': PRE,
            'parent_id': current_assets.id,
            'domain': """[
                ('account_id.user_type_id', '=', %s), %s
            ]""" % (data_account_type_prepayments.id, bu_domain),
            'groupby': 'account_id',
            'formulas': 'sum',
            'sequence': 4,
            'level': 2,
        }
        prepayment = line_model.create(prepayment_data)

        # Plus Fixed Assets
        
        data_account_type_fixed_assets = self.env.ref('account.data_account_type_fixed_assets')
        plus_fixed_assets_data = {
            'bu_br_id': self.id,
            'name': 'Plus Fixed Assets[%s]' % (self.code),
            'code': FA,
            'parent_id': total_assets.id,
            'domain': """[
                ('account_id.user_type_id', '=', %s), %s
            ]""" % (data_account_type_fixed_assets.id, bu_domain),
            'groupby': 'account_id',
            'formulas': 'sum',
            'sequence': 3,
            'level': 1,
        }
        plus_fixed_assets = line_model.create(plus_fixed_assets_data)

        # Plus Non-current Assets
        
        data_account_type_non_current_assets = self.env.ref('account.data_account_type_non_current_assets')
        plus_non_current_assets_data = {
            'bu_br_id': self.id,
            'name': 'Plus Non-current Assets[%s]' % (self.code),
            'code': PNCA,
            'parent_id': total_assets.id,
            'domain': """[
                ('account_id.user_type_id', '=', %s), %s
            ]""" % (data_account_type_non_current_assets.id, bu_domain),
            'groupby': 'account_id',
            'formulas': 'sum',
            'sequence': 4,
            'level': 1,
        }
        plus_non_current_assets = line_model.create(plus_non_current_assets_data)

        # LIABILITIES
        
        liabilities_data = {
            'bu_br_id': self.id,
            'name': 'LIABILITIES[%s]' % (self.code),
            'code': L,
            'financial_report_id': report.id,
            'control_domain': """[
                ('account_id.user_type_id.internal_group', '=', 'liability')
            ]""",
            'groupby': 'account_id',
            'formulas': '%s + %s' % (CL, NL),
            'sequence': 2,
            'level': 0,
            'green_on_positive': False,
        }
        liabilities = line_model.create(liabilities_data)

        # Current Liabilities
        
        data_account_type_current_liabilities = self.env.ref('account.data_account_type_current_liabilities')
        data_account_type_credit_card = self.env.ref('account.data_account_type_credit_card')
        current_assets_cl_data = {
            'bu_br_id': self.id,
            'name': 'Current Liabilities[%s]' % (self.code),
            'code': CL,
            'parent_id': liabilities.id,
            'control_domain': """[
                '|', ('account_id.user_type_id', 'in', [%s, %s]),
                     ('account_id.user_type_id.type', '=', 'payable'),
            ]""" % (data_account_type_current_liabilities.id, data_account_type_credit_card.id),
            'groupby': 'account_id',
            'formulas': '%s + %s' % (CL1, CL2),
            'sequence': 1,
            'level': 1,
            'green_on_positive': False,
        }
        current_assets_cl = line_model.create(current_assets_cl_data)

        # Current Liabilities
        
        current_assets_cl1_data = {
            'bu_br_id': self.id,
            'name': 'Current Liabilities[%s]' % (self.code),
            'code': CL1,
            'parent_id': current_assets_cl.id,
            'domain': """[
                '|', ('account_id.user_type_id', 'in', [%s, %s]), '&', ('account_id.user_type_id.type', '=', 'payable'), ('account_id.exclude_from_aged_reports', '=', True), %s
            ]""" % (data_account_type_current_liabilities.id, data_account_type_credit_card.id, bu_domain),
            'groupby': 'account_id',
            'formulas': '-sum',
            'sequence': 1,
            'level': 2,
            'green_on_positive': False,
        }
        current_assets_cl1 = line_model.create(current_assets_cl1_data)

        # Payables
        
        current_assets_cl2_data = {
            'bu_br_id': self.id,
            'name': 'Payables[%s]' % (self.code),
            'code': CL2,
            'parent_id': current_assets_cl.id,
            'domain': """[
                ('account_id.user_type_id.type', '=', 'payable'), ('account_id.exclude_from_aged_reports', '=', False), %s
            ]""" % (bu_domain),
            'groupby': 'account_id',
            'formulas': '-sum',
            'sequence': 2,
            'level': 2,
            'green_on_positive': False,
        }
        current_assets_cl2 = line_model.create(current_assets_cl2_data)

        # Plus Non-current Liabilities
        
        data_account_type_non_current_liabilities = self.env.ref('account.data_account_type_non_current_liabilities')
        plus_non_current_liabilities_data = {
            'bu_br_id': self.id,
            'name': 'Plus Non-current Liabilities[%s]' % (self.code),
            'code': NL,
            'parent_id': liabilities.id,
            'domain': """[
                ('account_id.user_type_id', '=', %s), %s
            ]""" % (data_account_type_non_current_liabilities.id, bu_domain),
            'groupby': 'account_id',
            'formulas': '-sum',
            'sequence': 2,
            'level': 1,
            'green_on_positive': False,
        }
        plus_non_current_liabilities = line_model.create(plus_non_current_liabilities_data)

        # Net Assets
        
        net_assets_data = {
            'bu_br_id': self.id,
            'name': 'Net Assets[%s]' % (self.code),
            'code': NA,
            'formulas': '%s - %s' % (TA, L),
            'sequence': 3,
            'level': 0,
        }
        net_assets = line_model.create(net_assets_data)

        # EQUITY
        
        equity_data = {
            'bu_br_id': self.id,
            'name': 'EQUITY[%s]' % (self.code),
            'code': EQ,
            'formulas': '%s + %s' % (UNAFFECTED_EARNINGS,RETAINED_EARNINGS),
            'financial_report_id': report.id,
            'sequence': 4,
            'level': 0,
        }
        equity = line_model.create(equity_data)

        # Unallocated Earnings
        
        unallocated_earnings_data = {
            'bu_br_id': self.id,
            'name': 'Unallocated Earnings[%s]' % (self.code),
            'code': UNAFFECTED_EARNINGS,
            'parent_id': equity.id,
            'formulas': '%s + %s' % (CURR_YEAR_EARNINGS, PREV_YEAR_EARNINGS),
            'sequence': 1,
            'level': 1,
            'green_on_positive': False,
            'special_date_changer': 'normal',
        }
        unallocated_earnings = line_model.create(unallocated_earnings_data)

        # Current Year Unallocated Earnings
        
        curr_year_unallocated_earnings_data = {
            'bu_br_id': self.id,
            'name': 'Current Year Unallocated Earnings[%s]' % (self.code),
            'code': CURR_YEAR_EARNINGS,
            'parent_id': unallocated_earnings.id,
            'formulas': '%s + %s' % (CURR_YEAR_EARNINGS_PNL, CURR_YEAR_EARNINGS_ALLOC),
            'sequence': 1,
            'level': 2,
        }
        curr_year_unallocated_earnings = line_model.create(curr_year_unallocated_earnings_data)

        # Current Year Earnings
        
        curr_year_earnings_data = {
            'bu_br_id': self.id,
            'name': 'Current Year Earnings[%s]' % (self.code),
            'code': CURR_YEAR_EARNINGS_PNL,
            'parent_id': curr_year_unallocated_earnings.id,
            'domain': "[]",
            'formulas': NEP,
            'sequence': 1,
            'level': 3,
        }
        curr_year_earnings = line_model.create(curr_year_earnings_data)

        # Current Year Allocated Earnings
        
        data_unaffected_earnings = self.env.ref('account.data_unaffected_earnings')
        curr_year_earnings_data = {
            'bu_br_id': self.id,
            'name': 'Current Year Allocated Earnings[%s]' % (self.code),
            'code': CURR_YEAR_EARNINGS_ALLOC,
            'parent_id': curr_year_unallocated_earnings.id,
            'domain': "[('account_id.user_type_id', '=', %s), %s]" % (data_unaffected_earnings.id, bu_domain),
            'formulas': '-sum',
            'sequence': 2,
            'level': 3,
            'special_date_changer': 'from_fiscalyear',
        }
        curr_year_earnings = line_model.create(curr_year_earnings_data)

        """<+++++++++++++ Previous Years ++++++++++++++++>"""
        # Previous Years Unallocated Earnings
        
        data_account_type_revenue = self.env.ref('account.data_account_type_revenue')
        data_account_type_other_income = self.env.ref('account.data_account_type_other_income')
        data_account_type_direct_costs = self.env.ref('account.data_account_type_direct_costs')
        data_account_type_expenses = self.env.ref('account.data_account_type_expenses')
        data_account_type_depreciation = self.env.ref('account.data_account_type_depreciation')
        prev_year_unallocated_earnings_data = {
            'bu_br_id': self.id,
            'name': 'Previous Years Unallocated Earnings[%s]' % (self.code),
            'code': PREV_YEAR_EARNINGS,
            'domain': """[
                ('account_id.user_type_id', 'in', [%s,%s,%s,%s,%s]), %s
            ]""" % (
                data_account_type_revenue.id,data_account_type_other_income.id,
                data_account_type_direct_costs.id,data_account_type_expenses.id,
                data_account_type_depreciation.id, bu_domain
            ),
            'parent_id': unallocated_earnings.id,
            'formulas': '-sum + %s - %s' % (ALLOCATED_EARNINGS, CURR_YEAR_EARNINGS),
            'sequence': 2,
            'level': 2,
            'special_date_changer': 'from_beginning',
        }
        prev_year_unallocated_earnings = line_model.create(prev_year_unallocated_earnings_data)

        # Allocated Earnings
        
        allocated_earnings_data = {
            'bu_br_id': self.id,
            'name': 'Allocated Earnings[%s]' % (self.code),
            'code': ALLOCATED_EARNINGS,
            'domain': """[
                ('account_id.user_type_id', '=', %s)
            ]""" % (data_unaffected_earnings.id),
            'parent_id': unallocated_earnings.id,
            'formulas': '-sum',
            'sequence': 2,
            'level': 2,
            'special_date_changer': 'from_beginning',
        }
        allocated_earnings = line_model.create(allocated_earnings_data)

        # Retained Earnings
        
        data_account_type_equity = self.env.ref('account.data_account_type_equity')
        retained_earnings_data = {
            'bu_br_id': self.id,
            'name': 'Retained Earnings[%s]' % (self.code),
            'code': RETAINED_EARNINGS,
            'domain': """[
                ('account_id.user_type_id', '=', %s), %s
            ]""" % (data_account_type_equity.id, bu_domain),
            'parent_id': equity.id,
            'formulas': '-sum',
            'sequence': 2,
            'level': 1,
            'special_date_changer': 'from_beginning',
        }
        retained_earnings = line_model.create(retained_earnings_data)

        # LIABILITIES + EQUITY
        
        liabilities_and_equity_data = {
            'bu_br_id': self.id,
            'name': 'LIABILITIES + EQUITY[%s]' % (self.code),
            'code': LE,
            'financial_report_id': report.id,
            'formulas': '%s + %s' % (L, EQ),
            'sequence': 4,
            'level': 0,
            'groupby': 'account_id',
            'green_on_positive': False,
        }
        liabilities_and_equity = line_model.create(liabilities_and_equity_data)

        # OFF BALANCE SHEET ACCOUNTS
        
        data_account_off_sheet = self.env.ref('account.data_account_off_sheet')
        report_off_sheet_data = {
            'bu_br_id': self.id,
            'name': 'OFF BALANCE SHEET ACCOUNTS[%s]' % (self.code),
            'code': OS,
            'domain': """[
                ('account_id.user_type_id', '=', %s)
            ]""" % (data_account_off_sheet.id),
            'control_domain':"""[
                ('account_id.user_type_id.internal_group', '=', 'off_balance'), %s
            ]""" % (bu_domain),
            'financial_report_id': report.id,
            'formulas': '-sum',
            'sequence': 5,
            'level': 0,
            'groupby': 'account_id',
            'hide_if_empty': True,
        }
        report_off_sheet = line_model.create(report_off_sheet_data)

    def generate_executive_summary_report(self):
        unit_code = self.code
        main_model = self.env['account.financial.html.report']
        line_model = self.env['account.financial.html.report.line']

        bu_domain = "('account_id.bu_br_id', '=', %s)" % self.id

        # CODES
        CR = 'CR_%s' % (unit_code)
        CS = 'CS_%s' % (unit_code)
        DEB = 'DEB_%s' % (unit_code)
        CRE = 'CRE_%s' % (unit_code)

        # FROM PROFIT & LOSS
        # Income : It came from profit and loss report
        INC = 'INC_%s' % (unit_code)
        # Cost of Revenue : It came from profit and loss report
        COS = 'COS_%s' % (unit_code)
        # Gross Profit : It came from profit and loss report
        GRP = 'GRP_%s' % (unit_code)
        #Less Expense : It came from profit and loss report
        LEX = 'LEX_%s' % (unit_code)
        # Net Profit : It came from profit and loss report
        NEP = 'NEP_%s' % (unit_code)
        # Operation Income : It came from profit and loss report
        OPINC = 'OPINC_%s' % (unit_code)

        # FROM BALANCE SHEET
        # Net assets : It came from balance sheet
        NA = 'NA_%s' % (unit_code)
        # TOTAL ASSETS : It came from balance sheet
        TA = 'TA_%s' % (unit_code)
        # ASSETS : It came from balance sheet
        CA = 'CA_%s' % (unit_code)
        # Current Liabilities : It came from balance sheet
        CL = 'CL_%s' % (unit_code)
        # <----------- Create Main ----------->
        main_data = {
            'bu_br_id': self.id,
            'name': 'EXECUTIVE SUMMARY[%s]' % (self.code),
            'parent_id': self.env.ref('account.account_reports_legal_statements_menu').id
        }
        
        # Create report 
        report = main_model.create(main_data)

        # CASH
        cash_data = {
            'bu_br_id': self.id,
            'name': 'Cash[%s]' % (self.code),
            'financial_report_id': report.id,
            'sequence': 1,
            'level': 0,
        }
        cash = line_model.create(cash_data)

        # Cash received
        cash_received_data = {
            'bu_br_id': self.id,
            'name': 'Cash received[%s]' % (self.code),
            'code': CR,
            'parent_id': cash.id,
            'domain': "[('account_id.user_type_id.type', '=', 'liquidity'), ('debit', '>', 0.0), %s]" % (bu_domain),
            'formulas': 'sum',
            'show_domain': 'never',
            'special_date_changer': 'strict_range',
            'sequence': 1,
            'level': 3,
        }
        cash_received = line_model.create(cash_received_data)

        # Cash spent
        cash_spent_data = {
            'bu_br_id': self.id,
            'name':'Cash spent[%s]' % (unit_code),
            'code': CS,
            'parent_id': cash.id,
            'domain': "[('account_id.user_type_id.type', '=', 'liquidity'), ('credit', '>', 0.0), %s]" % (bu_domain),
            'formulas': 'sum',
            'show_domain': 'never',
            'green_on_positive': False,
            'special_date_changer': 'strict_range', 
            'sequence': 2,
            'level': 3,
        }
        cash_spent = line_model.create(cash_spent_data)

        # Cash surplus
        cash_surplus_data = {
            'bu_br_id': self.id,
            'name':'Cash surplus[%s]' % (unit_code),
            'parent_id': cash.id,
            'formulas': '%s + %s' % (CR, CS),
            'sequence': 3,
            'level': 3,
        }
        cash_surplus = line_model.create(cash_surplus_data)

        # Closing bank balance
        closing_bank_balance_data = {
            'bu_br_id': self.id,
            'name':'Closing bank balance[%s]' % (unit_code),
            'parent_id': cash.id,
            'domain': "[('account_id.internal_type', '=', 'liquidity'), %s]" % (bu_domain),
            'formulas': 'sum',
            'sequence': 4,
            'level': 3,
        }
        closing_bank_balance = line_model.create(closing_bank_balance_data)

        # Profitability
        profitability_data = {
            'bu_br_id': self.id,
            'name':'Profitability[%s]' % (unit_code),
            'parent_id': report.id,
            'sequence': 2,
            'level': 0,
        }
        profitability = line_model.create(profitability_data)

        # Income
        income_data = {
            'bu_br_id': self.id,
            'name':'Income[%s]' % (unit_code),
            'parent_id': profitability.id,
            'formulas': INC,
            'sequence': 1,
            'level': 3,
        }
        income = line_model.create(income_data)

        # Cost of Revenue
        cost_of_revenue_data = {
            'bu_br_id': self.id,
            'name':'Cost of Revenue[%s]' % (unit_code),
            'parent_id': profitability.id,
            'formulas': COS,
            'sequence': 2,
            'level': 3,
            'green_on_positive': False,
        }
        cost_of_revenue = line_model.create(cost_of_revenue_data)

        # Gross profit
        gross_profit_data = {
            'bu_br_id': self.id,
            'name':'Gross profit[%s]' % (unit_code),
            'parent_id': profitability.id,
            'formulas': GRP,
            'sequence': 3,
            'level': 3,
        }
        gross_profit = line_model.create(gross_profit_data)

        # Expenses
        expenses_data = {
            'bu_br_id': self.id,
            'name':'Expenses[%s]' % (unit_code),
            'parent_id': profitability.id,
            'formulas': LEX,
            'sequence': 4,
            'level': 3,
            'green_on_positive': False,
        }
        expenses = line_model.create(expenses_data)

        # Net Profit
        net_profit_data = {
            'bu_br_id': self.id,
            'name':'Net Profit[%s]' % (unit_code),
            'parent_id': profitability.id,
            'formulas': NEP,
            'sequence': 5,
            'level': 3,
        }
        net_profit = line_model.create(net_profit_data)

        # Balance Sheet
        balance_sheet_data = {
            'bu_br_id': self.id,
            'name':'Balance Sheet[%s]' % (unit_code),
            'financial_report_id': report.id,
            'sequence': 3,
            'level': 0,
        }
        balance_sheet = line_model.create(balance_sheet_data)

        # Receivables
        receivables_data = {
            'bu_br_id': self.id,
            'name':'Receivables[%s]' % (unit_code),
            'code': DEB,
            'parent_id': balance_sheet.id,
            'domain': "[('account_id.user_type_id.type', '=', 'receivable'), %s]" % (bu_domain),
            'formulas': 'sum',
            'show_domain': 'never',
            'green_on_positive': False,
            'sequence': 1,
            'level': 3,
        }
        receivables = line_model.create(receivables_data)

        # Payables
        payables_data = {
            'bu_br_id': self.id,
            'name':'Payables[%s]' % (unit_code),
            'code': CRE,
            'parent_id': balance_sheet.id,
            'domain': "[('account_id.user_type_id.type', '=', 'payable'), %s]" % (bu_domain),
            'formulas': 'sum',
            'show_domain': 'never',
            'green_on_positive': False,
            'sequence': 2,
            'level': 3,
        }
        payables = line_model.create(payables_data)

        # Net assets
        net_assets_data = {
            'bu_br_id': self.id,
            'name':'Net assets[%s]' % (unit_code),
            'parent_id': balance_sheet.id,
            'formulas': NA,
            'sequence': 3,
            'level': 3,
        }
        net_assets = line_model.create(net_assets_data)

        # Performance
        performance_data = {
            'bu_br_id': self.id,
            'name':'Performance[%s]' % (unit_code),
            'financial_report_id': report.id,
            'sequence': 4,
            'level': 0,
        }
        performance = line_model.create(performance_data)

        # Gross profit margin (gross profit / operating income)
        gross_profit_margin_data = {
            'bu_br_id': self.id,
            'name':'Gross profit margin (gross profit / operating income)[%s]' % (unit_code),
            'parent_id': performance.id,
            'formulas': '%s / %s' % (GRP, OPINC),
            'figure_type': 'percents',
            'sequence': 1,
            'level': 3,
        }
        gross_profit_margin = line_model.create(gross_profit_margin_data)

        # Net profit margin (net profit / income)
        net_profit_margin_data = {
            'bu_br_id': self.id,
            'name':'Net profit margin (net profit / income)[%s]' % (unit_code),
            'parent_id': performance.id,
            'formulas': '%s / %s' % (GRP, INC),
            'figure_type': 'percents',
            'sequence': 2,
            'level': 3,
        }
        net_profit_margin = line_model.create(net_profit_margin_data)

        # Return on investments (net profit / assets)
        return_on_investments_data = {
            'bu_br_id': self.id,
            'name':'Return on investments (net profit / assets)[%s]' % (unit_code),
            'parent_id': performance.id,
            'formulas': '%s / %s' % (NEP, TA),
            'figure_type': 'percents',
            'sequence': 3,
            'level': 3,
        }
        return_on_investments = line_model.create(return_on_investments_data)

        # Position
        position_data = {
            'bu_br_id': self.id,
            'name':'Position[%s]' % (unit_code),
            'financial_report_id': report.id,
            'sequence': 5,
            'level': 0,
        }
        position = line_model.create(position_data)

        # Average debtors days
        average_debtors_days_data = {
            'bu_br_id': self.id,
            'name':'Average debtors days[%s]' % (unit_code),
            'parent_id': position.id,
            'formulas': '%s / %s * NDays' % (DEB, OPINC),
            'figure_type': 'no_unit',
            'sequence': 1,
            'level': 3,
            'green_on_positive': False,
        }
        average_debtors_days = line_model.create(average_debtors_days_data)

        # Average creditors days
        average_creditors_days_data = {
            'bu_br_id': self.id,
            'name':'Average creditors days[%s]' % (unit_code),
            'parent_id': position.id,
            'formulas': '-%s / %s * NDays' % (CRE, OPINC),
            'figure_type': 'no_unit',
            'sequence': 2,
            'level': 3,
            'green_on_positive': False,
        }
        average_creditors_days = line_model.create(average_creditors_days_data)

        # Short term cash forecast
        short_term_cash_forecast_data = {
            'bu_br_id': self.id,
            'name':'Short term cash forecast[%s]' % (unit_code),
            'parent_id': position.id,
            'formulas': '%s + %s' % (DEB, CRE),
            'figure_type': 'no_unit',
            'sequence': 3,
            'level': 3,
            'green_on_positive': False,
        }
        short_term_cash_forecast = line_model.create(short_term_cash_forecast_data)

        # Current assets to liabilities
        current_assets_to_liabilities_data = {
            'bu_br_id': self.id,
            'name':'Current assets to liabilities[%s]' % (unit_code),
            'parent_id': position.id,
            'formulas': '%s / %s' % (CA, CL),
            'figure_type': 'no_unit',
            'sequence': 4,
            'level': 3,
            'green_on_positive': False,
        }
        current_assets_to_liabilities = line_model.create(current_assets_to_liabilities_data)

    def generate_generic_statement_reports(self):
        try:
            self.generate_pnl_report()
            self.generate_balance_sheet_report()
            self.generate_executive_summary_report()
        except Exception as Error:
            raise UserError(_(str(Error)))

  
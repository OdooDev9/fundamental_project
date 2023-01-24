# -*- coding: utf-8 -*-
from attr import field
from odoo import models, fields, api

class AccountAccountInherit(models.Model):
    _inherit = "account.account"
    bu_br_id = fields.Many2one('business.unit', string='Business')  

    def name_get(self):
        result = []
        for account in self:
            name = account.code + ' ' + account.name
            if account.bu_br_id:
                name += '(' + account.bu_br_id.name + ')'
            result.append((account.id, name))
        return result    

class AccountJournalInherit(models.Model):
    _inherit = "account.journal"
    is_transit_jr = fields.Boolean('Is Transit')
    bu_br_id = fields.Many2one('business.unit', string='Business')
    cash_in_transit_id =  fields.Many2one('account.account', 'Cash In Transit')

    def name_get(self):
        res = []
        for journal in self:
            name = journal.name
            if journal.currency_id and journal.currency_id != journal.company_id.currency_id:
                name = "%s (%s)" % (name, journal.currency_id.name)
            if journal.bu_br_id:
                name = "%s (%s)" % (name, journal.bu_br_id.name)
            res += [(journal.id, name)]
        return res

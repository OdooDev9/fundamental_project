from odoo import api, fields, models, _
from odoo.tools import float_compare
from collections import defaultdict
from odoo.exceptions import UserError,AccessError
from odoo.tools.misc import format_date, get_lang
class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_bu(self):
        if self.env.user.user_type_id =='bu':
            return self.env.user.current_bu_br_id
    
    @api.model
    def _get_br(self):
        if self.env.user.user_type_id =='br':
            return self.env.user.current_bu_br_id
    def _set_bu_domain(self):
        domain = [('id', 'in', [bu.id for bu in self.env.user.hr_bu_ids])]
        return domain
    def _set_br_domain(self):
        domain = [('id', 'in', [br.id for br in self.env.user.hr_br_ids])]
        return domain
    
    is_extra_move = fields.Boolean('Extra Transaction')
    extra_source_id = fields.Many2one(
        'account.payment',
        string='Payment ID',
        help='This is the parent payment record of extra transaction move.'
        )
    hr_br_id = fields.Many2one('business.unit', string='Branch',default=_get_br,domain=_set_br_domain)
    hr_bu_id =fields.Many2one('business.unit',string='Business Unit',default=_get_bu,domain=_set_bu_domain)
    service_type = fields.Boolean(string="Service Type")
    br_discount_amount = fields.Float()
    discount_view = fields.Selection([('doc_discount', 'Document Discount'), ('line_discount', 'Line Discount')],
                                     string='Discount Type')
    discount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Discount Method')
    discount_value = fields.Float(string='Discount Value')
    br_discount = fields.Boolean(string="Branch Discount")
    unit_or_part = fields.Selection([('unit', 'Unit'), ('part', 'Spare Part')], string='Units or Parts')
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('approved_service_head','Approved Service Head'),
            ('approved_sale_head','Approved Sale Head'),
            ('approved_finance_pic', 'Approved F & A PIC'),
            ('approved_finance_head','Approved F & A Head'),
            ('approved_gm_agm','Approved GM/AGM'),
            ('approved_corp_ap_pic','Approved Corp. AP PIC'),
            ('approved_corp_ap_head','Approved Corp. AP Head'),
            ('approved_corp_ap_gm_agm','Approved Corp. AP Head'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
        
    oversea_payment_id = fields.Many2one('account.payment', string='Oversea Payment')


    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('stock_move_id') and val.get('stock_valuation_layer_ids') and val.get('move_type') == 'entry':
                stock_move = self.env['stock.move'].search([('id','=', int(val.get('stock_move_id')))])
                if stock_move:
                    sale_order = self.env['sale.order'].search([('name','=',stock_move.origin)])
                    if sale_order:
                        val['hr_bu_id'] = sale_order.hr_bu_id.id
        return super(AccountMoveInherit, self).create(vals)

    # def _post(self, soft=True):
    #     """Post/Validate the documents.

    #     Posting the documents will give it a number, and check that the document is
    #     complete (some fields might not be required if not posted but are required
    #     otherwise).
    #     If the journal is locked with a hash table, it will be impossible to change
    #     some fields afterwards.

    #     :param soft (bool): if True, future documents are not immediately posted,
    #         but are set to be auto posted automatically at the set accounting date.
    #         Nothing will be performed on those documents before the accounting date.
    #     :return Model<account.move>: the documents that have been posted
    #     """
    #     if soft:
    #         future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
    #         future_moves.auto_post = True
    #         for move in future_moves:
    #             msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
    #             move.message_post(body=msg)
    #         to_post = self - future_moves
    #     else:
    #         to_post = self

    #     # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
    #     if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
    #         raise AccessError(_("You don't have the access rights to post an invoice."))
    #     for move in to_post:
    #         if move.partner_bank_id and not move.partner_bank_id.active:
    #             raise UserError(_("The recipient bank account link to this invoice is archived.\nSo you cannot confirm the invoice."))
    #         if move.state == 'posted':
    #             raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
    #         if not move.line_ids.filtered(lambda line: not line.display_type):
    #             raise UserError(_('You need to add a line before posting.'))
    #         if move.auto_post and move.date > fields.Date.context_today(self):
    #             date_msg = move.date.strftime(get_lang(self.env).date_format)
    #             raise UserError(_("This move is configured to be auto-posted on %s", date_msg))
    #         if not move.journal_id.active:
    #             raise UserError(_(
    #                 "You cannot post an entry in an archived journal (%(journal)s)",
    #                 journal=move.journal_id.display_name,
    #             ))

    #         if not move.partner_id:
    #             if move.is_sale_document():
    #                 raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
    #             elif move.is_purchase_document():
    #                 raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

    #         if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
    #             raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))

    #         if move.display_inactive_currency_warning:
    #             raise UserError(_("You cannot validate an invoice with an inactive currency: %s",
    #                               move.currency_id.name))

    #         # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
    #         # lines are recomputed accordingly.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         if not move.invoice_date:
    #             if move.is_sale_document(include_receipts=True):
    #                 move.invoice_date = fields.Date.context_today(self)
    #                 move.with_context(check_move_validity=False)._onchange_invoice_date()
    #             elif move.is_purchase_document(include_receipts=True):
    #                 raise UserError(_("The Bill/Refund date is required to validate this document."))

    #         # When the accounting date is prior to the tax lock date, move it automatically to today.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date) and (move.line_ids.tax_ids or move.line_ids.tax_tag_ids):
    #             move.date = move._get_accounting_date(move.invoice_date or move.date, True)
    #             move.with_context(check_move_validity=False)._onchange_currency()

    #     # Create the analytic lines in batch is faster as it leads to less cache invalidation.
    #     to_post.mapped('line_ids').create_analytic_lines()
    #     to_post.write({
    #         'state': 'posted',
    #         'posted_before': True,
    #     })

    #     for move in to_post:
    #         move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])

    #         # Compute 'ref' for 'out_invoice'.
    #         if move._auto_compute_invoice_reference():
    #             to_write = {
    #                 'payment_reference': move._get_invoice_computed_reference(),
    #                 'line_ids': []
    #             }
    #             for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
    #                 to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))
    #             move.write(to_write)

    #     for move in to_post:
    #         if move.is_sale_document() \
    #                 and move.journal_id.sale_activity_type_id \
    #                 and (move.journal_id.sale_activity_user_id or move.invoice_user_id).id not in (self.env.ref('base.user_root').id, False):
    #             move.activity_schedule(
    #                 date_deadline=min((date for date in move.line_ids.mapped('date_maturity') if date), default=move.date),
    #                 activity_type_id=move.journal_id.sale_activity_type_id.id,
    #                 summary=move.journal_id.sale_activity_note,
    #                 user_id=move.journal_id.sale_activity_user_id.id or move.invoice_user_id.id,
    #             )

    #     customer_count, supplier_count = defaultdict(int), defaultdict(int)
    #     for move in to_post:
    #         if move.is_sale_document():
    #             customer_count[move.partner_id] += 1
    #         elif move.is_purchase_document():
    #             supplier_count[move.partner_id] += 1
    #     for partner, count in customer_count.items():
    #         (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
    #     for partner, count in supplier_count.items():
    #         (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

    #     # Trigger action for paid invoices in amount is zero
    #     to_post.filtered(
    #         lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
    #     ).action_invoice_paid()

    #     # Force balance check since nothing prevents another module to create an incorrect entry.
    #     # This is performed at the very end to avoid flushing fields before the whole processing.
    #     to_post._check_balanced()
    #     return to_post


    # SLO start   
    @api.onchange('discount_type')
    def onchange_discount_type_move(self):
        for rec in self:
            # rec.discount_value = 0.00
            # rec.onchange_discount_value()
            for line in rec.invoice_line_ids:
                line._get_price_total_and_subtotal()
                # line.discount_type = rec.discount_type
                line._onchange_discount_type()
            rec.onchange_discount_value()
            rec._onchange_invoice_line_ids()

    @api.onchange('discount_view')
    def onchange_discount(self):
        for rec in self:
            rec.discount_value = 0.00
            rec.onchange_discount_value()
            if rec.discount_view == 'line_discount':
                rec.discount_value = 0.00
            for line in rec.invoice_line_ids:
                # line.discount_view = self.discount_view
                line.discount = 0
                line._onchange_discount_type()
                line._get_price_total_and_subtotal()

    @api.onchange('discount_value','invoice_line_ids')
    def onchange_discount_value(self):
        res = {}
        for rec in self.invoice_line_ids:
            if self.discount_value > 0.0:
                if self.discount_view == 'doc_discount' and self.discount_type == 'fixed':
                    rec.discount = self.discount_value/len(self.invoice_line_ids)
                else:
                    rec.discount = self.discount_value
                rec._onchange_price_subtotal()
                rec._get_price_total_and_subtotal()
                self._onchange_invoice_line_ids()
            else:
                rec._onchange_price_subtotal()
                rec._get_price_total_and_subtotal()
                self._onchange_invoice_line_ids()
    # SLO end
    @api.onchange('unit_or_part','hr_bu_id')
    def _onchange_unit_part(self):
        self.invoice_line_ids = False

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        self = self.with_company(self.company_id)
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_company(self.journal_id.company_id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if self.hr_bu_id:
                # out_invoice intend to Invoice from sale order
                if self.move_type == 'out_invoice':
                    # Retrieve account from BU
                    if not self.hr_bu_id.property_account_receivable_id:
                        raise UserError(_("Account Missing Error!. Your haven't set receivable account for current business unit called %s." % self.hr_bu_id.name))
                    return self.hr_bu_id.property_account_receivable_id
                
                # in_invoice intend to Bill from purchase
                if self.move_type == 'in_invoice':
                    account_id = self.hr_bu_id.po_property_account_payable_id if self.is_oversea_purchase else self.hr_bu_id.property_account_payable_id
                    if not account_id:
                        raise UserError(_("Account Missing Error!. Your haven't set payable account for Current Business Unit(%s)." % (self.hr_bu_id.name)))
                    return self.env['account.account'].browse(int(account_id)).exists()     
                    # account_id = self.env['ir.config_parameter'].sudo().get_param('account_extension.property_account_payable_id')
                    # if not account_id:
                    #     raise UserError(_("Account Missing Error!. Your haven't set payable account for Head Office(HO)."))
                    # return self.env['account.account'].browse(int(account_id)).exists()     
            # This is for br only sale(intended to service sale for each Business unit)
            elif self.hr_br_id and not self.hr_bu_id:
                # out_invoice intend to Invoice from sale order
                if self.move_type == 'out_invoice':
                    # Retrieve account from BU
                    if not self.hr_br_id.property_account_receivable_id:
                        raise UserError(_("Account Missing Error!. Your haven't set receivable account for current Business Branch called %s." % self.hr_br_id.name))
                    return self.hr_br_id.property_account_receivable_id
                
                # in_invoice intend to Bill from purchase
                if self.move_type == 'in_invoice':
                    account_id = self.hr_br_id.property_account_payable_id
                    if not account_id:
                        raise UserError(_("Account Missing Error!. Your haven't set payable account for Current Business Branch called %s." % (self.hr_br_id.name)))
                    return self.env['account.account'].browse(int(account_id)).exists() 

            elif payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.move_type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate.update(candidate._get_fields_onchange_balance(force_computation=True))
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.payment_reference = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity
    # SLO start
    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                # sign = -1 if move.is_outbound() else 1
                quantity = base_line.quantity
                total_discount = base_line.discount+base_line.br_dis_value
                is_refund = move.move_type in ('out_refund', 'in_refund')
                amount = base_line.price_unit - (base_line.discount + base_line.br_dis_value)
                price_unit_wo_discount = sign * base_line.price_unit * (1 - ((base_line.discount + base_line.br_dis_value) / 100.0)) if self.discount_type == 'percentage' else sign * amount
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            return base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=move.always_tax_exigible,
            )
            
        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'], tax_repartition_line, tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            to_write_on_line = {
                'amount_currency': taxes_map_entry['amount'],
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))
    # SLO end


    @api.model
    def _search_default_journal(self, journal_types):
        company_id = self._context.get('default_company_id', self.env.company.id)
        domain = [('company_id', '=', company_id), ('type', 'in', journal_types), ('bu_br_id', '=', self.env.user.current_bu_br_id.id)]

        journal = None
        if self._context.get('default_currency_id'):
            currency_domain = domain + [('currency_id', '=', self._context['default_currency_id'])]
            journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            company = self.env['res.company'].browse(company_id)

            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        return journal


    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            bu_br_ids = m.hr_br_id.ids + m.hr_bu_id.ids
            domain = [('company_id', '=', company_id), ('type', '=', journal_type), ('bu_br_id', 'in', bu_br_ids)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def default_get(self, default_fields):
        # OVERRIDE
        values = super(models.Model, self).default_get(default_fields)

        values['business_id'] = self._context.get('default_business_id')

        if 'account_id' in default_fields and not values.get('account_id') \
            and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
            and self._context.get('default_move_type') in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt'):
            # Fill missing 'account_id'.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            values['account_id'] = journal.default_account_id.id
        elif self._context.get('line_ids') and any(field_name in default_fields for field_name in ('debit', 'credit', 'account_id', 'partner_id')):
            move = self.env['account.move'].new({'line_ids': self._context['line_ids']})

            # Suggest default value for debit / credit to balance the journal entry.
            balance = sum(line['debit'] - line['credit'] for line in move.line_ids)
            # if we are here, line_ids is in context, so journal_id should also be.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            currency = journal.exists() and journal.company_id.currency_id
            if currency:
                balance = currency.round(balance)
            if balance < 0.0:
                values.update({'debit': -balance})
            if balance > 0.0:
                values.update({'credit': balance})

            # Suggest default value for 'partner_id'.
            if 'partner_id' in default_fields and not values.get('partner_id'):
                if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].partner_id == move.line_ids[-2].partner_id != False:
                    values['partner_id'] = move.line_ids[-2:].mapped('partner_id').id

            # Suggest default value for 'account_id'.
            if 'account_id' in default_fields and not values.get('account_id'):
                if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].account_id == move.line_ids[-2].account_id != False:
                    values['account_id'] = move.line_ids[-2:].mapped('account_id').id
        if values.get('display_type') or self.display_type:
            values.pop('account_id', None)
        return values

    business_id = fields.Many2one('business.unit',related='move_id.hr_bu_id',string='BU/BR/DIV', )
    discount_value = fields.Float(string='Discount Value')
    br_dis_value = fields.Float(string="BR Discount Value")
    # SLO start
    discount_type = fields.Selection(related='move_id.discount_type', string='Discount Method')
    discount_view = fields.Selection(related='move_id.discount_view',string='Discount Type')
    # SLO end
    color = fields.Char('Color')
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes)
            line.tax_ids = taxes
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()
        for move in self.move_id:
            return {'domain': {'product_id': ['&','|',('unit_or_part','=',move.unit_or_part),('landed_cost_ok','=',True),('business_id', '=', move.hr_bu_id.id),]}}
# SLO start
    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None, br_dis_value=None, discount_type=None,discount_view=None):
        self.ensure_one()
        data = self._get_price_total_and_subtotal_model(
            price_unit=price_unit or self.price_unit,
            quantity=quantity or self.quantity,
            discount=discount or self.discount,
            currency=currency or self.currency_id,
            product=product or self.product_id,
            partner=partner or self.partner_id,
            taxes=taxes or self.tax_ids,
            move_type=move_type or self.move_id.move_type,
            br_dis_value=br_dis_value or self.br_dis_value,
            discount_type=discount_type or self.discount_type,
            discount_view=discount_view or self.discount_view,
        )
        return data

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity,discount, currency, product, partner, taxes, move_type, br_dis_value,discount_type,discount_view):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        # line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        # subtotal = quantity * line_discount_price_unit

        if discount_type == 'fixed' and discount_view == 'doc_discount':
            print('doc discount')
            _discount = discount + br_dis_value
            subtotal = (quantity * price_unit) - _discount
        elif discount_type == 'fixed' and discount_view == 'line_discount':
            line_discount_price_unit = price_unit - discount - br_dis_value
            subtotal = quantity * line_discount_price_unit

        else:
            discount = price_unit * (1 - ((discount + br_dis_value) / 100.0))
            line_discount_price_unit = discount
            subtotal = quantity * line_discount_price_unit
        print("*"*10)
        print(subtotal)
       
        
        if taxes:
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            # print(res['price_subtotal'],'if >>>>>>>>>>>>>>>>>>>>')
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
            # print('res----------------------->','')
            # print('---------------->',subtotal)
            # print(res['price_subtotal'],'else........')
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def _get_fields_onchange_balance(self, quantity=None, discount=None, amount_currency=None, move_type=None, currency=None, taxes=None, price_subtotal=None, br_dis_value=None,discount_type=None,discount_view=None,force_computation=False):
        self.ensure_one()
        return self._get_fields_onchange_balance_model(
            quantity=quantity or self.quantity,
            discount=discount or self.discount,
            amount_currency=amount_currency or self.amount_currency,
            move_type=move_type or self.move_id.move_type,
            currency=currency or self.currency_id or self.move_id.currency_id,
            taxes=taxes or self.tax_ids,
            price_subtotal=price_subtotal or self.price_subtotal,
            br_dis_value=br_dis_value or self.br_dis_value,
            discount_type=discount_type or self.discount_type,
            discount_view=discount_view or self.discount_view,
            force_computation=force_computation,


        )

    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes, price_subtotal,discount_type,discount_view, br_dis_value, force_computation=False):
        ''' This method is used to recompute the values of 'quantity', 'discount', 'price_unit' due to a change made
        in some accounting fields such as 'balance'.

        This method is a bit complex as we need to handle some special cases.
        For example, setting a positive balance with a 100% discount.

        :param quantity:        The current quantity.
        :param discount:        The current discount.
        :param amount_currency: The new balance in line's currency.
        :param move_type:       The type of the move.
        :param currency:        The currency.
        :param taxes:           The applied taxes.
        :param price_subtotal:  The price_subtotal.
        :return:                A dictionary containing 'quantity', 'discount', 'price_unit'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        amount_currency *= sign
        
        # Avoid rounding issue when dealing with price included taxes. For example, when the price_unit is 2300.0 and
        # a 5.5% price included tax is applied on it, a balance of 2300.0 / 1.055 = 2180.094 ~ 2180.09 is computed.
        # However, when triggering the inverse, 2180.09 + (2180.09 * 0.055) = 2180.09 + 119.90 = 2299.99 is computed.
        # To avoid that, set the price_subtotal at the balance if the difference between them looks like a rounding
        # issue.
        if not force_computation and currency.is_zero(amount_currency - price_subtotal):
            return {}

        taxes = taxes.flatten_taxes_hierarchy()
        if taxes and any(tax.price_include for tax in taxes):
            # Inverse taxes. E.g:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 110           | 10% incl, 5%  |                   | 100               | 115
            # 10            |               | 10% incl          | 10                | 10
            # 5             |               | 5%                | 5                 | 5
            #
            # When setting the balance to -200, the expected result is:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 220           | 10% incl, 5%  |                   | 200               | 230
            # 20            |               | 10% incl          | 20                | 20
            # 10            |               | 5%                | 10                | 10
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency, currency=currency, handle_price_include=False)
            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                if tax.price_include:
                    amount_currency += tax_res['amount']

        if discount_type == 'percentage':
            discount_factor = 1 - ((discount + br_dis_value) / 100.0)
        else:
            discount_factor = discount
        if amount_currency and discount_factor:
            # discount != 100%
            vals = {
                'quantity': quantity or 1.0,
                'price_unit': amount_currency / discount_factor / (quantity or 1.0) if discount_type == 'percentage' else (amount_currency+(quantity*discount))/quantity,
            }
        elif amount_currency and not discount_factor:
            # discount == 100%
            vals = {
                'quantity': quantity or 1.0,
                'discount': 0.0,
                'price_unit': amount_currency / (quantity or 1.0),
            }
        elif not discount_factor:
            # balance of line is 0, but discount  == 100% so we display the normal unit_price
            vals = {}
        else:
            # balance is 0, so unit price is 0 as well
            vals = {'price_unit': 0.0}

        return vals

    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        self.ensure_one()
        return self._get_fields_onchange_subtotal_model(
            price_subtotal=price_subtotal or self.price_subtotal,
            move_type=move_type or self.move_id.move_type,
            currency=currency or self.currency_id,
            company=company or self.move_id.company_id,
            date=date or self.move_id.date,
        )


    @api.onchange('discount_type','discount_view','br_dis_value')
    def _onchange_discount_type(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            line.discount_type = line.discount_type
            line.move_id._recompute_tax_lines()
            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        
        for vals in vals_list:
            print("vals===============>", vals)
            move = self.env['account.move'].browse(vals['move_id'])
            vals.setdefault('company_currency_id', move.company_id.currency_id.id) # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

            # Ensure balance == amount_currency in case of missing currency or same currency as the one from the
            # company.
            currency_id = vals.get('currency_id') or move.company_id.currency_id.id
            if currency_id == move.company_id.currency_id.id:
                balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
                vals.update({
                    'currency_id': currency_id,
                    'amount_currency': balance,
                })
            else:
                vals['amount_currency'] = vals.get('amount_currency', 0.0)

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.new({'tax_ids': vals.get('tax_ids', [])}).tax_ids
                tax_ids = set(taxes.ids)
                taxes = self.env['account.tax'].browse(tax_ids)

                # Ensure consistency between accounting & business fields.
                # As we can't express such synchronization as computed fields without cycling, we need to do it both
                # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
                # business [resp. accounting] fields are recomputed.
                if any(vals.get(field) for field in ACCOUNTING_FIELDS):
                    print("ACCOUNTING_FIELDS==========>")
                    price_subtotal = self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                        vals.get('br_dis_value', 0.0),
                        move.discount_type or self.discount_type,
                        move.discount_view or self.discount_view,
                    ).get('price_subtotal', 0.0)
                    vals.update(self._get_fields_onchange_balance_model(
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals['amount_currency'],
                        move.move_type,
                        currency,
                        taxes,
                        price_subtotal,
                        vals.get('br_dis_value', 0.0),
                        move.discount_type or self.discount_type,
                        move.discount_view or self.discount_view,
                    ))
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                        vals.get('br_dis_value', 0.0),
                        move.discount_type or self.discount_type,
                        move.discount_view or self.discount_view,
                    ))
                elif any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                        vals.get('br_dis_value', 0.0),
                        move.discount_type or self.discount_type,
                        move.discount_view or self.discount_view,
                    ))
                    vals.update(self._get_fields_onchange_subtotal_model(
                        vals['price_subtotal'],
                        move.move_type,
                        currency,
                        move.company_id,
                        move.date,
                    ))
                    vals['discount_type'] = self.discount_type
                    vals['discount_view'] = self.discount_view
                    print(vals['discount_type'],'slo------------------------>>>')
        lines = super(models.Model, self).create(vals_list)

        moves = lines.mapped('move_id')
        if self._context.get('check_move_validity', True):
            moves._check_balanced()
        moves._check_fiscalyear_lock_date()
        lines._check_tax_lock_date()
        moves._synchronize_business_models({'line_ids'})

        return lines
# SLO end

    

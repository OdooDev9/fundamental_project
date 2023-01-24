from odoo import models, _

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def _init_filter_journals(self, options, previous_options=None):
        if self.filter_journals is None:
            return
        all_journal_groups = self._get_filter_journal_groups()
        all_journals = self._get_filter_journals()
        journals_sel = []
        options['journals'] = []
        group_selected = False
        if previous_options and previous_options.get('journals'):
            for journal in previous_options['journals']:
                if isinstance(journal.get('id'), int) and journal.get('id') in all_journals.ids and journal.get('selected'):
                    journals_sel.append(journal)
        # In case no previous_options exist, the default behaviour is to select the first Journal Group that exists.
        elif all_journal_groups:
            selected_journals = all_journals - all_journal_groups[0].excluded_journal_ids
            for journal in selected_journals:
                journals_sel.append({
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                    'selected': True,
                })
        # Create the dropdown menu
        if all_journal_groups:
            options['journals'].append({'id': 'divider', 'name': _('Journal Groups')})
            for group in all_journal_groups:
                group_journal_ids = (all_journals.filtered(lambda x: x.company_id == group.company_id) - group.excluded_journal_ids).ids
                if not group_selected and journals_sel \
                        and len(journals_sel) == len(group_journal_ids) \
                        and all(journal_opt['id'] in group_journal_ids for journal_opt in journals_sel):
                    group_selected = group
                options['journals'].append({'id': 'group', 'name': group.name, 'ids': group_journal_ids})

        previous_company = False
        journals_selection = {opt['id'] for opt in journals_sel}
        for journal in all_journals:
            if journal.company_id != previous_company:
                business = self.env.user.current_bu_br_id.name
                options['journals'].append({'id': 'divider', 'name': business})
                previous_company = journal.company_id
            options['journals'].append({
                'id': journal.id,
                'name': journal.name,
                'code': journal.code,
                'type': journal.type,
                'selected': journal.id in journals_selection,
            })

        # Compute the displayed option name
        if group_selected:
            options['name_journal_group'] = group_selected.name
        elif len(journals_sel) == 0 or len(journals_sel) == len(all_journals):
            options['name_journal_group'] = _("All Journals")
        elif len(journals_sel) <= 5:
            options['name_journal_group'] = ', '.join(jrnl['code'] for jrnl in journals_sel)
        elif len(journals_sel) == 6:
            options['name_journal_group'] = ', '.join(jrnl['code'] for jrnl in journals_sel) + _(" and one other")
        else:
            options['name_journal_group'] = ', '.join(jrnl['code'] for jrnl in journals_sel[:5]) + _(" and %s others",
                                                                                                     len(journals_sel) - 5)

    def _init_filter_custom(self, options, previous_options=None):
        options['name_journal_custom'] = "CUSTOM"
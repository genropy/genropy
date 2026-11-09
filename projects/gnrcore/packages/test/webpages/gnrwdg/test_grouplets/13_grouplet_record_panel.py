# -*- coding: utf-8 -*-

"""groupletPanel on the fields of a real TH record: every grouplet returns
locationpath='record', so the inner memory form edits the outer record and
autosaves into it; the real save is the outer form's.

- test_1 (tree) and test_2 (multibutton): empty the company name in Company,
  then open Contact: a dialog offers Cancel (stay on Company, selection
  kept) or Discard and continue. Opening a group without edits leaves the
  outer form unchanged, extra_data (a Bag column) included. Status is
  mandatory on source: while it is empty Status is red with the warning
  icon, its branch is red and the outer form cannot be saved. On a draft
  record (try genro.formById('prospect_tree_form').setDraft(true)) the
  marks turn italic, source is not required and the form saves; back to
  setDraft(false) the save is refused again.
- test_3: the Logs grouplet mounts a relation handler on sys.task, with its
  datapath outside the grouplet record: the grid lists the task_result rows
  of the outer record, and opening it leaves the outer form unchanged.

The probe records are created on first load."""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     th/th:TableHandler,
                     gnrcomponents/grouplet/grouplet:GroupletHandler"""

    def _probe_prospect(self):
        tbl = self.db.table('test.myprospect')
        found = tbl.query(where='$company_name=:name',
                          name='Grouplet record probe').fetch()
        if found:
            return found[0]['id']
        record = tbl.newrecord(company_name='Grouplet record probe',
                               contact_name='Ada Lovelace', status='new',
                               extra_data=Bag(dict(budget=Bag(dict(amount=1000)))))
        tbl.insert(record)
        self.db.commit()
        return record['id']

    def _probe_task(self):
        tbl = self.db.table('sys.task')
        found = tbl.query(where='$task_name=:name',
                          name='Grouplet record probe').fetch()
        if found:
            return found[0]['id']
        task = tbl.newrecord(task_name='Grouplet record probe',
                             command='probe',
                             parameters=Bag(dict(mode='dry', retries=2)))
        tbl.insert(task)
        results = self.db.table('sys.task_result')
        for is_error in (False, True):
            results.insert(results.newrecord(task_id=task['id'],
                                             is_error=is_error))
        self.db.commit()
        return task['id']

    def _recordPanel(self, pane, table=None, pkey=None, frameCode=None,
                     topic=None):
        def formCb(form):
            form.center.groupletPanel(value='^#FORM', table=table, topic=topic,
                                      grouplets_root='grouplets_record',
                                      frameCode=frameCode)
        bc = pane.borderContainer(height='450px', border='1px solid silver')
        bc.contentPane(region='center').thFormHandler(
            table=table, formId=f'{frameCode}_form', startKey=pkey,
            formCb=formCb)

    def test_1_tree(self, pane):
        """Tree panel on test.myprospect"""
        self._recordPanel(pane, table='test.myprospect',
                          pkey=self._probe_prospect(),
                          frameCode='prospect_tree')

    def test_2_multibutton(self, pane):
        """Multibutton panel (topic main) on test.myprospect"""
        self._recordPanel(pane, table='test.myprospect',
                          pkey=self._probe_prospect(),
                          frameCode='prospect_mb', topic='main')

    def test_3_relation(self, pane):
        """Relation handler inside a grouplet on sys.task"""
        self._recordPanel(pane, table='sys.task', pkey=self._probe_task(),
                          frameCode='task_tree')

# -*- coding: utf-8 -*-

"hierarchicalSelect: a select whose arrow opens a tree"

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'hierarchicalSelect'

    def test_0_hierarchical_table(self, pane):
        """A hierarchical table: the tree shows its levels and only the leaves are selectable.
        Typing searches the leaves, as a dbSelect does"""
        fb = pane.formlet(cols=1)
        fb.hierarchicalSelect(value='^.tag_id', table='adm.htag', lbl='Tag',
                              caption_field='hierarchical_description')

    def test_1_grouped_by_fk(self, pane):
        """Users under their group: hierarchical names the field the tree groups by.
        The username filter reaches both the typed search and the tree, and a group left
        with no user disappears. selected_group_code writes the group of the chosen user"""
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.prefix', lbl='Username like', default='%', placeholder='e.g. a%')
        fb.div('^.group_code', lbl='Selected group')
        fb.hierarchicalSelect(value='^.user_id', table='adm.user', hierarchical='$group_code',
                              lbl='User', condition='$username ILIKE :prefix',
                              condition_prefix='^.prefix', selected_group_code='.group_code',
                              colspan=2)

    def test_2_several_levels(self, pane):
        """Provinces by zone, then by region: a field of a related table, then a foreign key"""
        fb = pane.formlet(cols=2)
        fb.hierarchicalSelect(value='^.provincia', table='glbl.provincia',
                              hierarchical='@regione.zona,$regione', caption_field='nome',
                              lbl='Provincia', selected_regione='.regione')
        fb.div('^.regione', lbl='Selected region')

    def test_3_values(self, pane):
        """No table: the rows of a Bag grouped by their fields. Typing searches them, as a select does"""
        pane.data('.fruits', self.fruits())
        fb = pane.formlet(cols=2)
        fb.hierarchicalSelect(value='^.fruit', values='^.fruits', hierarchical='color,taste',
                              lbl='Fruit')
        fb.div('^.fruit', lbl='Value')

    def fruits(self):
        result = Bag()
        for code, caption, color, taste in [('lemon', 'Lemon', 'Yellow', 'Sour'),
                                            ('banana', 'Banana', 'Yellow', 'Sweet'),
                                            ('lime', 'Lime', 'Green', 'Sour'),
                                            ('kiwi', 'Kiwi', 'Green', 'Sweet'),
                                            ('cherry', 'Cherry', 'Red', 'Sweet'),
                                            ('currant', 'Redcurrant', 'Red', 'Sour')]:
            result.setItem(code, None, caption=caption, color=color, taste=taste)
        return result

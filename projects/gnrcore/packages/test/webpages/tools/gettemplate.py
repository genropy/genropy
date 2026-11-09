# -*- coding: utf-8 -*-

"""Templates: inline, from a resource, from a table, and the templateChunk

A `template` attribute renders `$field` placeholders against its `datasource`.
The template can be written inline, read with `dataResource` from
`webpages/_resources`, taken with `tableTemplate` from the table's `tpl/`
resources, or rendered by a `templateChunk`, which loads the compiled template
of the table, server side through `record_id` or client side through a
`dataProvider`. Table templates are read from
`test/resources/tables/_packages/adm/<table>/tpl/`.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                   gnrcomponents/tpleditor:ChunkEditor"""

    def test_1_template_a(self, pane):
        """Inline template: pick a table, its record fills the placeholders, $pippo comes from a template attribute"""
        pane.dbSelect(dbtable='adm.tblinfo', value='^.pkey', _class='gnrfield')
        pane.dataRecord('.record', 'adm.tblinfo', pkey='^.pkey', _if='pkey')
        pane.data('.pippo', 55)
        pane.div(template="""<div><span>$tblid $pkgid</span>
                             </div><div>$description</div> $pippo""", datasource='^.record', pippo='^.pippo')

    def test_3_template(self, pane):
        """Template read by name from webpages/_resources with dataResource: change the name to load another one"""
        pane.textbox(value='^.template_name', default_value='demotpl1.html')
        pane.dbSelect(dbtable='adm.tblinfo', value='^.pkey', _class='gnrfield')
        pane.dataRecord('.record', 'adm.tblinfo', pkey='^.pkey', _if='pkey')
        pane.data('.pippo', 55)
        pane.dataResource('.remote_tpl', resource='^.template_name')
        pane.div(template='^.remote_tpl', datasource='^.record', pippo='^.pippo')

    def test_4_tableTemplate(self, pane):
        """The table's html template `short`, read at build time with tableTemplate"""
        pane.dbSelect(dbtable='adm.tblinfo', value='^.pkey', _class='gnrfield')
        pane.dataRecord('.record', 'adm.tblinfo', pkey='^.pkey', _if='pkey')
        pane.div(template=self.tableTemplate('adm.tblinfo', 'short'), datasource='^.record')

    def test_36_templateChunk(self, pane):
        """Plain-text chunk: the package template `testplain` rendered without markup"""
        pane.dbSelect(dbtable='adm.pkginfo', value='^.pkey', _class='gnrfield', lbl='Package')
        rpc = pane.dataRecord('.record', 'adm.pkginfo', pkey='^.pkey', _if='pkey')
        pane.templateChunk(innerHTML='^.testplain', template='testplain', table='adm.pkginfo', datasource='^.record',
                           height='100px',
                           dataProvider=rpc,
                           editable=True, plainText=True)

    def test_6_templateChunk_server(self, pane):
        """Table template `custom` rendered on the server from the record_id"""
        pane.dbSelect(dbtable='adm.tblinfo', value='^.pkey', _class='gnrfield')
        pane.dataRecord('.record', 'adm.tblinfo', pkey='^.pkey', _if='pkey')
        pane.templateChunk(template='custom', table='adm.tblinfo', datasource='^.record',
                           height='100px', record_id='^.record.tblid')

    def test_7_templateChunk_client(self, pane):
        """The same table template rendered on the client from the record its dataProvider loads"""
        pane.dbSelect(dbtable='adm.tblinfo', value='^.pkey', _class='gnrfield')
        rpc = pane.dataRecord('.record', 'adm.tblinfo', pkey='^.pkey', _if='pkey')
        pane.templateChunk(template='custom', table='adm.tblinfo', datasource='^.record',
                           height='100px', dataProvider=rpc)

    def test_9_templateChunk(self, pane):
        """Package template `custom` rendered on the server from the picked pkey, with a row per table"""
        pane.dbSelect(dbtable='adm.pkginfo', value='^.pkey', _class='gnrfield')
        pane.templateChunk(innerHTML='^.piero', template='custom', table='adm.pkginfo',
                           record_id='^.pkey', height='100px', editable=True)

    def test_z_formulasyntax(self, pane):
        """Formula attributes (==): the width follows the number, the last textbox is disabled when Dis is 'disabled'"""
        fb = pane.formbuilder(cols=1)
        fb.numberTextbox(value='^.width', lbl='Width')
        fb.textbox(value='^.pippo', width='==_width+_uu+"px";', _width='^.width', _uu=66)
        fb.checkbox(value='^.prova', lbl='disabled')
        fb.textbox(disabled='^.prova')
        fb.textbox(value='^.dis', lbl='Dis')
        fb.textbox(value='^.xxx', disabled='==_prova=="disabled";', _prova='^.dis')

# -*- coding: utf-8 -*-

"Dbselect"

from time import sleep

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'Dbselect'   

    def test_0_firsttest(self,pane):
        """Basic dbSelect and dbComboBox with auxColumns, selected and hasDownArrow"""
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.dbSelect(table='adm.user',value='^.user_id',lbl='User',
                    selected_username='.username',width='25em',
                    hasDownArrow=True)
        fb.dbCombobox(table='adm.user',value='^.username',lbl='Combo',width='25em',
                    hasDownArrow=True)
        fb.dbSelect(table='adm.user',value='^.user_id_2',lbl='Aux col',
                    auxColumns='$username',
                    width='25em', 
                    hasDownArrow=True)
        fb.div('^.username',lbl='Username')

    def test_5_selected(self,pane):
        "Use of selected:"
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.dbSelect(table='glbl.provincia',value='^.sigla',
                        lbl='Sigla',width='25em', selected_regione='.regione')
        fb.dbSelect(table='glbl.regione',value='^.regione',lbl='Regione',width='25em',selected_nome='.nome_regione')
        fb.textbox(value='^.nome_regione',lbl='Nome regione')



    def test_1_condition(self,pane):
        "Use of condition: first choose a Region, then you will find cities only in the selected region"
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.dbSelect(table='glbl.regione',value='^.regione',lbl='Regione',width='25em',selected_nome='.nome_regione')
        fb.dbSelect(table='glbl.provincia',value='^.sigla',condition='$regione=:regione',condition_regione='^.regione',
                        lbl='Sigla',width='25em', selected_nome='.nome_provincia',
                        validate_notnull=True, validate_notnull_error='Manca il valore')
        fb.textbox(value='^.nome_provincia',lbl='Nome provincia')

    def test_7_condition_single_option(self,pane):
        "A single option updates both select widgets and their related values"
        pane.data('.regione','LOM')
        pane.data('.sigla','MI')
        pane.data('.sigla_combo','MI')
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.dbSelect(table='glbl.regione',value='^.regione',lbl='Regione',width='25em')
        fb.dbSelect(table='glbl.provincia',value='^.sigla',condition='$regione=:regione',
                    condition_regione='^.regione',lbl='DbSelect',width='25em',
                    selected_nome='.nome_provincia',validate_notnull=True)
        fb.dbComboBox(table='glbl.provincia',value='^.sigla_combo',alternatePkey='sigla',
                      condition='$regione=:regione',condition_regione='^.regione',
                      lbl='DbComboBox',width='25em',selected_nome='.nome_provincia_combo',
                      validate_notnull=True)
        fb.textbox(value='^.nome_provincia',lbl='Nome dbSelect')
        fb.textbox(value='^.nome_provincia_combo',lbl='Nome dbComboBox')
        fb.button('Set VAL / AO',action="SET .regione='VAL'; SET .sigla='AO'; SET .sigla_combo='AO';")

    def test_8_condition_race(self,pane):
        "A stale condition reply must not restore or invalidate a newer value"
        pane.data('.regione','VAL')
        pane.data('.sigla','AO')
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.dbSelect(table='glbl.regione',value='^.regione',lbl='Regione',width='25em')
        fb.dbSelect(table='glbl.provincia',value='^.sigla',method=self.delayedDbSelect,
                    condition='$regione=:regione',condition_regione='^.regione',
                    lbl='DbSelect',width='25em')
        fb.div('^.sigla',lbl='Datastore value')
        pane.dataRpc('.race_province',self.raceProvince,regione='^.regione',
                     _if="regione=='LOM'",_else='null')
        pane.dataController("SET .sigla=province;",province='^.race_province',_if='province')
        fb.button('Set LOM / MI',action="SET .regione='LOM';")

    @public_method
    def delayedDbSelect(self,_id=None,**kwargs):
        if _id == 'AO':
            sleep(1)
        return self.app.dbSelect(_id=_id,**kwargs)

    @public_method
    def raceProvince(self,regione=None):
        return 'MI' if regione == 'LOM' else None
        
    def test_2_clientmethod(self,pane):
        "Manually set what to display with callbackSelect"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.callbackSelect(value='^.test',callback="""function(kw){
                var _id = kw._id;
                var _querystring = kw._querystring;
                var data = [{name:'Mario Rossi',addr:'Via del Pero',state:'Milano',_pkey:'mrossi',caption:'Mario Rossi (mrossi)'},
                              {name:'Luigi Bianchi',addr:'Via del Mare',state:'Roma',_pkey:'lbianchi',caption:'Luigi Bianchi (lbianchi)'},
                              {name:'Carlo Manzoni',addr:'Via Bisceglie',state:'Firenze',_pkey:'cmanzoni',caption:'Carlo Manzoni (cmanz)'},
                              {name:'Marco Vanbasten',addr:'Via orelli',state:'Como',_pkey:'mvan',caption:'Marco Vanbasten(mvan)'},
                              {name:'',caption:'',_pkey:null}
                              ]
                var cbfilter = function(n){return true};
                if(_querystring){
                    _querystring = _querystring.slice(0,-1).toLowerCase();
                    cbfilter = function(n){return n.name.toLowerCase().indexOf(_querystring)>=0;};
                }else if(_id){
                    cbfilter = function(n){return n._pkey==_id;}
                }
                data = data.filter(cbfilter);
                return {headers:'name:Customer,addr:Address,state:State',data:data}
            }""",auxColumns='addr,state',lbl='Callback select',hasDownArrow=True,nodeId='cbsel')

    def test_3_packageSelect(self,pane):
        "Select package (packageSelect) and table (tableSelect)"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.packageSelect(value='^.pkg',lbl='Pkg')
        fb.tableSelect(value='^.tbl',lbl='Table',pkg='=.pkg',auxColumns='tbl')

    def test_4_invaliditemCondition(self,pane):
        "Set invalid items cryteria: in this case, only names shorter than 10 characters are availables"
        form = pane.frameForm(frameCode='pippo',store='memory',height='50px',store_startKey='*newrcord*')
        fb = form.record.formbuilder(cols=1, border_spacing='4px')
        fb.dbSelect(table='glbl.provincia',value='^.sigla',
                        lbl='Provincia corta',width='25em',invalidItemCondition='(char_length($nome)>10)',
                        selected_regione='.regione',
                        invalidItemCondition_message='troppo lungo',auxColumns='$regione')
        fb.div('^.regione')

    def test_6_hdbselect(self,pane):
        "hdbSelect on a hierarchical table: table= kwarg and the deprecated dbtable= spelling sharing a connectedMenu"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.hdbSelect(value='^.tag_id',table='adm.htag',lbl='Tag',width='25em',
                    caption_field='hierarchical_description',connectedMenu='htag_menu')
        fb.hdbSelect(value='^.tag_id_2',dbtable='adm.htag',lbl='Tag (old spelling)',width='25em',
                    caption_field='hierarchical_description',connectedMenu='htag_menu')

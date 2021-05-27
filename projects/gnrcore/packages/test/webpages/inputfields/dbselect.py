# -*- coding: utf-8 -*-

"Dbselect"

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from time import sleep

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

    def test_1_condition(self,pane):
        "Use of condition: first choose a Region, then you will find cities only in the selected region"
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.dbSelect(table='glbl.regione',value='^.regione',lbl='Regione',width='25em',selected_nome='pippo')
        fb.dbSelect(table='glbl.provincia',value='^.sigla',condition='$regione=:regione',condition_regione='^.regione',
                        lbl='Sigla',width='25em', validate_notnull=True, validate_notnull_error='Manca il valore')
    
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


    def test_3_dbselectrpc(self,pane):
        "Define a Rpc method and use it in remoteSelect"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.remoteSelect(value='^.user',width='25em',lbl='User',auxColumns='status,auth_tags',
                        method=self.getUserCustomRpc)

    @public_method
    def getUserCustomRpc(self,_querystring=None,_id=None,**kwargs):
        result = Bag()
        if _id:
            f = self.db.table('adm.user').query(where='$id = :u',u=_id).fetch()
        else:
            sleep(2)
            f = self.db.table('adm.user').query(where='$username ILIKE :u',u='%s%%' %_querystring.replace('*','')).fetch()
        for i,r in enumerate(f):
            result.setItem('%s_%s' %(r['id'],i),None,caption='%s - %s' %(r['username'], r['auth_tags']),
                status=r['status'],auth_tags=r['auth_tags'],_pkey=r['id'],username=r['username'])
        return result,dict(columns='username,status,auth_tags',headers='Name,Status,Tags')

    def test_4_packageSelect(self,pane):
        "Select package (packageSelect) and table (tableSelect)"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.packageSelect(value='^.pkg',lbl='Pkg')
        fb.tableSelect(value='^.tbl',lbl='Table',pkg='=.pkg',auxColumns='tbl')

    def test_5_invaliditemCondition(self,pane):
        "Set invalid items cryteria: in this case, only names shorter than 10 characters are availables"
        form = pane.frameForm(frameCode='pippo',store='memory',height='50px',store_startKey='*newrcord*')
        fb = form.record.formbuilder(cols=1, border_spacing='4px')
        fb.dbSelect(table='glbl.provincia',value='^.sigla',
                        lbl='Provincia corta',width='25em',invalidItemCondition='(char_length($nome)>10)',
                        selected_regione='.regione',
                        invalidItemCondition_message='troppo lungo',auxColumns='$regione')
        fb.div('^.regione')
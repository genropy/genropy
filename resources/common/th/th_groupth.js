var genro_plugin_groupth = {
    toggleCounterColumn:function(kw){
        var sourceNode = kw.sourceNode;
        var cb = function(){
            let structrow = sourceNode.getRelativeData('.struct.view_0.rows_0')
            let cell = structrow.getAttr('_grp_count');
            if(!cell){
                structrow.setItem('_grp_count',null,{field:'_grp_count',name:'Cnt',width:'5em',group_aggr:'sum',dtype:'L'});
            }else{
                structrow.popNode('_grp_count');
            }
        }  
        kw.menu.setItem('#id',null,{caption:_T('Toggle counter column'),action:cb});
    },

    buildGroupTree:function(pane,structBag,treekw){
        pane.getValue().popNode('treeroot');
        var root = pane._('div','treeroot').getParentNode();
        if(!(structBag && structBag.getItem('#0.#0'))){
            return;
        }
        root.freeze();
        treekw = treekw || {};
        var tr = root._('treeGrid',objectUpdate(treekw,{storepath:'.treestore',
                                    autoCollapse:false,
                                    headers:true,_class:'groupby_tree'}));
        var struct_row = structBag.getItem('#0.#0');
        tr._('treegrid_column',{field:'description',header:''});
        var fld,width;
        
        struct_row.forEach(function(n){
            if(n.attr.group_aggr && 'NLIRF'.indexOf(n.attr.dtype)>=0  || n.attr.group_nobreak || n.attr.calculated){
                fld = n.attr.field.replace(/\W/g, '_');
                fld += (n.attr.group_aggr?'_'+n.attr.group_aggr.replace(/\W/g, '_').toLowerCase():'');
                if(n.attr.width){
                    width = parseInt(n.attr.width);
                    if(n.attr.width.endsWith('em')){
                        width = width*14;
                    }
                }else{
                    width = 120;
                }
                tr._('treegrid_column',{field:fld,dtype:(n.attr.group_aggr && n.attr.group_nobreak)?'T':n.attr.dtype,
                                        size:width,header:n.attr.tree_name || n.attr.name,format:n.attr.format});
            }
        });
        root.unfreeze();
    },
    groupCellInfoFromStruct:function(struct){
        var result = {};
        result.group_by_cols = [];
        result.formulalist = [];
        var f,cell;
        struct.getItem('#0.#0').forEach(function(n){
            if(!(n.attr.group_aggr && 'NLIRF'.indexOf(n.attr.dtype)>=0 || n.attr.group_nobreak || n.attr.formula) ){
                f = n.attr.field.replace(/\W/g, '_');
                if(n.attr.group_aggr){
                    f += '_'+n.attr.group_aggr.replace(/\W/g, '_').toLowerCase();
                }
                cell = objectExtract(n.attr,'field,queryfield,group_aggr',true);
                cell.field_getter = f;
                cell.original_field = cell.field;
                cell.dtype = n.attr.dtype;
                result.group_by_cols.push(cell);
            }else if(n.attr.formula){
                result.formulalist.push([n.attr.field,n.attr.formula]);
            }
        });
        return result;
    },

    groupTreeData:function(gridstore,structBag,rootName){
        if(!(gridstore && structBag && structBag.getItem('#0.#0'))){
            return;
        }
        var result = new gnr.GnrBag();
        var treedata;
        if(rootName){
            treedata = new gnr.GnrBag();
            result.setItem('_root_',treedata,{'description':rootName});
        }else{
            treedata = result;
        }
        var row,kl,description,treepath,value;
        var info = this.groupCellInfoFromStruct(structBag);
        var group_by_cols = info.group_by_cols;
        var formulalist = info.formulalist;   
        gridstore.forEach(function(n){
            kl = [];
            row = objectUpdate({},n.attr);
            group_by_cols.forEach(function(cell){
                let k = cell.field_getter;
                value = objectPop(row,k);
                description = value;
                if(typeof(value)!='string'){
                    description = _F(description);
                }
                kl.push(flattenString(description,['.']));
                treepath = kl.join('.');
                if(!treedata.getNode(treepath)){
                    treedata.setItem(treepath,null,{'description':description,_cell:cell,value:value});
                }
            });
            objectUpdate(treedata.getAttr(kl),row);
        });
        this.updateTreeTotals(result,formulalist);
        return result;
    },

    updateTreeTotals:function(treeData,formulalist){
        var that = this;
        treeData.forEach(function(n){
            that.updateBranchTotals(n,formulalist);
        });
    },
    
    updateBranchTotals:function(branchDataNode,formulalist){
        var currAttr = branchDataNode.attr;
        var k;
        var that = this;
        var branchdata = branchDataNode.getValue();
        if(!branchdata){
            return;
        }
        branchdata.forEach(function(n){
            if(n.getValue()){
                that.updateBranchTotals(n,formulalist);
            }
            currAttr._pkeylist = currAttr._pkeylist?currAttr._pkeylist+','+n.attr._pkeylist:n.attr._pkeylist;
            that.updateTotalsAttr(currAttr,n.attr);
            formulalist.forEach(function(felem){
                currAttr[felem[0]] = funcApply("return "+felem[1],currAttr);
            });
        });
    },
    updateTotalsAttr:function(currAttr,attr){
        for(let k in attr){
            if(k.endsWith('_sum')){
                currAttr[k] = (currAttr[k] || 0)+attr[k];
            }else if(k.endsWith('_avg')){
                currAttr[k+'_avg_cnt'] = (currAttr[k+'_avg_cnt'] || 0)+attr._grp_count_sum;
                currAttr[k+'_avg_s'] = (currAttr[k+'_avg_s'] || 0)+attr[k]*attr._grp_count_sum;
                currAttr[k] = currAttr[k+'_avg_s']/currAttr[k+'_avg_cnt'];
            }else if(k.endsWith('_min')){
                currAttr[k] = Math.min(k in currAttr? currAttr[k]:attr[k],attr[k]);
            }else if(k.endsWith('_max')){
                currAttr[k] = Math.max(k in currAttr? currAttr[k]:attr[k],attr[k]);
            }
        }
    },

    getPivotGrid:function(sourceStore,sourceStruct){
        if(!(sourceStore && sourceStore.len() && sourceStruct)){
            return false;
        }
        var resultStore = new gnr.GnrBag();
        var resultStruct = new gnr.GnrBag();
        var resultStructRow = new gnr.GnrBag();
        resultStruct.setItem('view_0.rows_0',resultStructRow);

        var struct_row = sourceStruct.getItem('#0.#0');
        
        var grpcol = [];
        var valuecols = [];
        var nobreak = [];
        struct_row.forEach(function(n){
            let attr = objectUpdate({},n.attr);
            attr.col_getter = attr.field.replace(/\W/g, '_');
            if (attr.group_aggr){
                attr.col_getter+='_'+attr.group_aggr.replace(/\W/g, '_').toLowerCase();
            }
            if((attr.group_aggr || attr.formula) && 'NLIRF'.indexOf(attr.dtype)>=0 ){    
                valuecols.push(attr);
            }else if (attr.group_nobreak){
                nobreak.push(attr);
            }else{
                grpcol.push(attr);
            }
        });
        var columnsets = new gnr.GnrBag();
        var lastGrpcol = grpcol.pop();
        if(!lastGrpcol){
            return {'struct':resultStruct,'store':resultStore};
        }
        var lastGrpcolField = lastGrpcol.col_getter;
        var colset = Array.from(new Set(sourceStore.columns('#a.'+lastGrpcolField)[0])).sort();
        colset.push('TOTALS')
        var colsetDict = {};
        var emptyrow = {_pkeylist:null};
        var formuladict,formulalist,newname,k,structNode;
        var that = this;
        grpcol.concat(nobreak).forEach(function(kw,idx){
            resultStructRow.setItem('cell_'+resultStructRow.len(),null,objectUpdate({},kw));
        });
        colset.forEach(function(f,colsetidx){
            let csname = f;
            if(f=='TOTALS'){
                colsetidx = 'TT';
                csname = _T('Totals')
            }
            colsetDict[f]=colsetidx;
            formuladict = {};
            formulalist = [];
            valuecols.forEach(function(kw){
                let attr = objectUpdate({},kw);
                newname = attr.field+'_'+colsetidx;
                if(attr.group_aggr){
                    newname+= '_'+attr.group_aggr.replace(/\W/g, '_').toLowerCase();
                }
                emptyrow[newname] = null;
                formuladict[attr.col_getter] = newname;
                attr.field = attr.field+'_'+colsetidx;
                attr.tree_name = csname+'<br/>'+attr.name;
                attr.columnset = 'grp_'+colsetidx;
                if(!columnsets.getNode(attr.columnset)){
                    let csattr = {code:'grp_'+colsetidx,name:csname};
                    if(colsetidx=='TT'){
                        csattr.cells_background='rgba(173, 202, 170, 0.20)'
                        csattr.background='rgba(38, 88, 32, 1.00)'
                    }
                    columnsets.setItem(attr.columnset,null,csattr);
                }
                structNode = resultStructRow.setItem('cell_'+resultStructRow.len(),null,attr);
                if(attr.formula){
                    formulalist.push(structNode.attr);
                }
            });
            formulalist.forEach(function(f){
                for(k in formuladict){
                    f.formula = f.formula.replace(new RegExp(k,'g'),formuladict[k]);
                }
            });
        });
        sourceStore.getNodes().forEach(function(n,idx){
            var attr = n.attr;
            let grprow = {};
            let keylist = [];
            let pkeylist = attr._pkeylist;
            let st_row;
            let cskey = colsetDict[attr[lastGrpcolField]];
            grpcol.forEach(function(f){
                let colname = f.col_getter;
                keylist.push(attr[colname]);
                grprow[colname] = attr[colname];
            });
            let key = keylist.join('_').replace(/\W/g, '_');
            let st_node = resultStore.getNode(key);
            if(!st_node){
                st_row = objectUpdate(objectUpdate({},emptyrow),grprow);
                st_row._totals = {}
                st_node = resultStore.setItem(key,null,st_row);
            }else{
                st_row = st_node.attr;
            }
            nobreak.forEach(function(f){
                let colname = f.col_getter;
                st_row[colname] = attr[colname];
            });
            that.updateTotalsAttr(st_row._totals,attr);
            valuecols.forEach(function(f){
                let value = attr[f.col_getter];
                let colname = f.field.replace(/\W/g, '_');
                let newkey = colname+'_'+cskey;
                if(f.group_aggr){
                    newkey+='_'+f.group_aggr.replace(/\W/g, '_').toLowerCase();
                }
                st_row[newkey] = value;
            });
            let prev_pkeylist = st_row._pkeylist;
            st_row._pkeylist = prev_pkeylist?prev_pkeylist+','+pkeylist:pkeylist;
            st_node.updAttributes(st_row);
        });
        resultStruct.setItem('info.columnsets',columnsets);
        resultStore.forEach(function(n){
            let attr = n.attr;
            let totals = objectPop(attr,'_totals');
            for (let keytot in totals){
                let klist = keytot.split('_');
                klist.splice(klist.length-1,null,'TT');
                attr[klist.join('_')] = totals[keytot]
            }
            console.log('attr',attr);
            n.updAttributes(attr);
        });
        return {'struct':resultStruct,'store':resultStore};
    },
    addColumnCb:function(grid,kw){
        var treeNode = kw.treeNode;
        var data = kw.data;
        var column = kw.column;
        var fieldcellattr = kw.fieldcellattr;
        var n = treeNode.getRelativeData(treeNode.attr.storepath).getNode(data.fieldpath);
        /* if(n && n.attributeOwnerNode('mode','M')){
            genro.publish('floating_message',{messageType:'warning',message:_T('This kind of relation is not allowed in group by totalization')});
        } */
        var dtype = data.dtype;
        var that = this;
        var dflt = new gnr.GnrBag(data);
        if('RNLIF'.indexOf(dtype)>=0){
            dflt.setItem('cell_group_aggr','sum');
            dflt.setItem('cell_totalize',true);
        }
        var promptkw = {dflt:dflt};
        promptkw.widget = function(pane){
            var fb =  genro.dev.formbuilder(pane,1,{border_spacing:'3px',margin:'5px'});
            fb.addField('textbox',{value:'^.fullcaption',lbl:'Caption'});
            that.groupByParsFields(fb,dtype,'cell_');
        };
        promptkw.action = function(result){
            result = result.asDict();
            if(result.cell_group_aggr=='break' || result.cell_group_aggr=='nobreak'){
                result.group_nobreak = result.cell_group_aggr=='nobreak';
                result.cell_group_aggr = false;
            }
            grid.addColumn(result, column,fieldcellattr);
            grid.sourceNode.publish('group_added_column',{column:column});
        };
        genro.dlg.prompt(_T('Add column'),promptkw);
        
    },

    groupByParsFields:function(fb,dtype,prefix){
        prefix = prefix || '';
        prefix = '^.'+prefix;
        var numeric = 'RNLIF'.indexOf(dtype)>=0;
        var dateTime = ['DH','DHZ','D'].indexOf(dtype)>=0;
        if(numeric){
            fb.addField('filteringSelect',{value:prefix+'group_aggr',
                        values:'sum:Sum,avg:Average,min:Min,max:Max,break:Break,nobreak:No break',
                        lbl:_T('Aggregator'),validate_onAccept:"this.setRelativeData('.cell_totalize',value=='sum')"});
            fb.addField('checkbox',{value:'^.cell_totalize',label:'Totalize'});
            fb.addField('checkbox',{value:'^.not_zero',label:'Not zero'});
            fb.addField('numberTextBox',{value:'^.min_value',lbl:'Min value',width:'5em',default_value:null});
            fb.addField('numberTextBox',{value:'^.max_value',lbl:'Max value',width:'5em',default_value:null});

        }else if(dateTime){
            let values = genro.commonDatasets.datetimes_chunk.join(',');
            var tb = fb.addField('textbox',{lbl:_T('Date aggregator'),value:prefix+'group_aggr'});
            tb._('ComboMenu',{values:values,action:function(kw,ctx){
                var cv = this.attr.attachTo.widget.getValue();
                this.attr.attachTo.widget.setValue(cv?cv+'-'+kw.fullpath:kw.fullpath,true);
            }});
            fb.addField('checkbox',{value:prefix+'group_nobreak',label:_T('No break')});
            fb.addField('textbox',{value:prefix+'group_empty',lbl:_T('Empty value'),
                                    hidden:prefix+'group_nobreak',placeholder:'[NP]'})
        }else{
            fb.addField('checkbox',{value:prefix+'group_nobreak',label:_T('No break')});
            fb.addField('textbox',{value:prefix+'group_empty',lbl:_T('Empty value'),
                                    hidden:prefix+'group_nobreak',placeholder:'[NP]'})
        }
    },

  
    saveAsDashboard:function(sourceNode,kw){
        kw = kw || {};
        var th = TH(sourceNode.attr._linkedTo || sourceNode.attr.nodeId+'_query');
        var queryParsBag = th.querymanager.queryParsBag();
        sourceNode.setRelativeData('.queryPars',queryParsBag);
        kw.dataIndex = {
            where:th.querymanager.sourceNode.absDatapath('.query.where'),
            groupLimit:th.querymanager.sourceNode.absDatapath('.query.limit'),
            groupOrderBy:th.querymanager.sourceNode.absDatapath('.query.customOrderBy'),
            joinConditions:th.querymanager.sourceNode.absDatapath('.query.joinConditions'),
            groupByStruct:'.grid.struct',
            groupMode:'.groupMode',
            treeRootName:'.treeRootName',
            output:'.output',
            queryPars:'.queryPars',
        };
        kw.objtype = 'dash_groupby';
        kw.metadataPath = '.dashboardMeta';
        kw.table = sourceNode.attr.table;
        kw.title = _T('Save dashboard');
        kw.preview = true;
        kw.defaultMetadata = {flags:'groupth|'+sourceNode.attr.nodeId};
        var onSaved = objectPop(kw,'onSaved');
        if(!onSaved){
            onSaved =function(result){
                sourceNode.setRelativeData('.dashboardMeta',new gnr.GnrBag(result.attr));
                sourceNode.fireEvent('.refreshDashboardsMenu',true);
            };
        }
        return genro.dev.userObjectSave(sourceNode,kw,onSaved);
    },

    loadDashboard:function(sourceNode,kw){
        kw.userObjectIdOrCode = objectPop(kw,'pkey');
        kw.metadataPath = '.dashboardMeta';
        kw.tbl = sourceNode.attr.table;
        kw.objtype = 'dash_groupby';
        kw.onLoaded = function(dataIndex,resultValue,resultAttr){
            if(sourceNode.attr._linkedTo){
                var qm = TH(sourceNode.attr._linkedTo).querymanager;
                var qsn = qm.sourceNode;
                var where = resultValue.getItem('where');
                if(where && where.len()){
                    qsn.setRelativeData('.query.currentQuery','__queryeditor__');
                    qsn.setRelativeData('.query.queryAttributes.extended',true);
                    qsn.setRelativeData('.query.queryEditor',true);
                    qm.buildQueryPane();
                }
                qsn.fireEvent('.runQuery',true);

            }else{
                sourceNode.fireEvent('.reloadMain',true);
            }
        };
        return genro.dev.userObjectLoad(sourceNode,kw);
    },

    deleteCurrentDashboard:function(sourceNode,kw){
        var pkey = sourceNode.getRelativeData('.dashboardMeta.id');
        if(!pkey){
            return;
        }
        genro.serverCall('_table.adm.userobject.deleteUserObject',{pkey:pkey},function(){
            sourceNode.setRelativeData('.dashboardMeta',new gnr.GnrBag());
        });
    }

};
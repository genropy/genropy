var THPicker = {

    onDropElement:function(sourceNode,data,mainpkey,rpcmethod,treepicker,tbl,one,many,grid,defaults){
        var kw = {dropPkey:mainpkey,tbl:tbl,one:one,many:many};
        var cbdef = function(destrow,sourcerow,d){
            var l = d.split(':');
            var sfield = l[0];
            var dfield = l.length==1?l[0]:l[1];
            destrow[dfield] = sourcerow[sfield];
        };
        if(treepicker){
            kw.dragPkeys = [data['pkey']];
            if(defaults){
                var drow = {};
                kw.dragDefaults = {};
                defaults.split(',').forEach(function(d){cbdef(drow,data['_record'],d);});
                kw.dragDefaults[data['pkey']] = drow;
            }
        }else{
            var pkeys = [];
            var dragDefaults = {};
            dojo.forEach(data,function(n){
                pkeys.push(n['_pkey'])
                if(defaults){
                    var drow = {};
                    defaults.split(',').forEach(function(d){cbdef(drow,n,d);});
                    dragDefaults[n['_pkey']] = drow;
                }
                
            });
            kw.dragPkeys = pkeys;
            kw.dragDefaults = dragDefaults;
        }
        kw['_sourceNode'] = sourceNode;
        if(grid.gridEditor && grid.gridEditor.editorPars){
            var rows = [];
            dojo.forEach(kw.dragPkeys,function(fkey){
                var r = {};
                r[many] = fkey;
                if(kw.dragDefaults){
                    objectUpdate(r,kw.dragDefaults[fkey]);
                }
                rows.push(r);
            });
            grid.gridEditor.addNewRows(rows);
        }else if(mainpkey){
            genro.serverCall(rpcmethod,kw,function(){},null,'POST');
        }

    }
}
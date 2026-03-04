var genro_plugin_sheetjs = {
    init:async function(){
        return genro.dom.loadResource('/_rsrc/js_libs/xlsx.min.js');
    },

    rowsFromXLSXClipboard:async function(){
        if(!window.XLSX){
            await genro.dom.loadResource('/_rsrc/js_libs/xlsx.min.js');
        }
        const clipboardText = await navigator.clipboard.readText();
        return this.rowsFromXLSXText(clipboardText);
    },

    rowsFromXLSXText:function(text){
        const cleanedText = text.replace(/(\d+),(\d+)\s*€/g, (match, part1, part2) => {
            return `${part1}.${part2}`;
        });
        const workbook = XLSX.read(cleanedText, { type: 'string', cellDates: true,cellNF: true});
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        return XLSX.utils.sheet_to_row_object_array(sheet);
    },

    bagFromXLSXText:function(text){
        let rows = this.rowsFromXLSXText(text);
        let result = new gnr.GnrBag();
        rows.forEach(function(r,idx){
            let row = {};
            for (let k in r){
                row[k.replace('.',' ').trim().replace(/ /g, "_")] = r[k];
            }
            result.addItem('r_'+idx,new gnr.GnrBag(row));
        });
        return result;
    }


};
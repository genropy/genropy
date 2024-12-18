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


};
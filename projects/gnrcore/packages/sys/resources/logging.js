const logging_tree_editor = {};

logging_tree_editor.ondblclick = function(evt) {
    var row = dijit.getEnclosingWidget(evt.target).item.attr;
    console.log(row);

    var fields = [
 	{
	    value: "^.level",
	    tag: "filteringSelect",
	    lbl: "Logging Level",
	    values: genro.getData("logging_levels")
	},
	// {
	//     value: "^.handlers",
	//     tag: "checkboxtext",
	//     popup: true,
	//     lbl: "Handlers",
	//     values: genro.getData("logging_handlers")
	// },
    ]
    
    var action = function(res) {
	var n = genro.getDataNode('logging_conf_bag.'+row.path);
	n.updAttributes(res.asDict());
    }
    
    genro.dlg.prompt("Edit", {widget: fields, action: action,
			      dflt: new gnr.GnrBag(row)});
}

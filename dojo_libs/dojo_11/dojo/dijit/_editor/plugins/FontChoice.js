/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dijit._editor.plugins.FontChoice"]){
dojo._hasResource["dijit._editor.plugins.FontChoice"]=true;
dojo.provide("dijit._editor.plugins.FontChoice");
dojo.require("dijit._editor._Plugin");
dojo.require("dijit.form.FilteringSelect");
dojo.require("dojo.data.ItemFileReadStore");
dojo.require("dojo.i18n");
dojo.requireLocalization("dijit._editor","FontChoice",null,"ar,cs,da,de,el,es,fi,ROOT,fr,he,hu,it,ja,ko,nb,nl,pl,pt,pt-pt,ru,sv,tr,zh,zh-tw");
dojo.declare("dijit._editor.plugins.FontChoice",dijit._editor._Plugin,{_uniqueId:0,buttonClass:dijit.form.FilteringSelect,_initButton:function(){
var _1=this.command;
var _2=this.custom||{fontName:this.generic?["serif","sans-serif","monospace","cursive","fantasy"]:["Arial","Times New Roman","Comic Sans MS","Courier New"],fontSize:[1,2,3,4,5,6,7],formatBlock:["p","h1","h2","h3","pre"]}[_1];
var _3=dojo.i18n.getLocalization("dijit._editor","FontChoice");
var _4=dojo.map(_2,function(_5){
var _6=_3[_5]||_5;
var _7=_6;
switch(_1){
case "fontName":
_7="<div style='font-family: "+_5+"'>"+_6+"</div>";
break;
case "fontSize":
_7="<font size="+_5+"'>"+_6+"</font>";
break;
case "formatBlock":
_7="<"+_5+">"+_6+"</"+_5+">";
}
return {label:_7,name:_6,value:_5};
});
_4.push({label:"",name:"",value:""});
dijit._editor.plugins.FontChoice.superclass._initButton.apply(this,[{labelType:"html",labelAttr:"label",searchAttr:"name",store:new dojo.data.ItemFileReadStore({data:{identifier:"value",items:_4}})}]);
this.button.setValue("");
this.connect(this.button,"onChange",function(_8){
if(this.updating){
return;
}
if(dojo.isIE&&"_savedSelection" in this){
var b=this._savedSelection;
delete this._savedSelection;
this.editor.focus();
this.editor._moveToBookmark(b);
}else{
dijit.focus(this._focusHandle);
}
if(this.command=="fontName"&&_8.indexOf(" ")!=-1){
_8="'"+_8+"'";
}
this.editor.execCommand(this.editor._normalizeCommand(this.command),_8);
});
},updateState:function(){
this.inherited(arguments);
var _e=this.editor;
var _c=this.command;
if(!_e||!_e.isLoaded||!_c.length){
return;
}
if(this.button){
var _c=_e.queryCommandValue(this.editor._normalizeCommand(_c))||"";
var _d=dojo.isString(_c)&&_c.match(/'([^']*)'/);
if(_d){
_c=_d[1];
}
if(this.generic&&_c=="fontName"){
var _e={"Arial":"sans-serif","Helvetica":"sans-serif","Myriad":"sans-serif","Times":"serif","Times New Roman":"serif","Comic Sans MS":"cursive","Apple Chancery":"cursive","Courier":"monospace","Courier New":"monospace","Papyrus":"fantasy"};
_c=_e[_c]||_c;
}else{
if(_c=="fontSize"&&_c.indexOf&&_c.indexOf("px")!=-1){
var _f=parseInt(_c);
_c={10:1,13:2,16:3,18:4,24:5,32:6,48:7}[_f]||_c;
}
}
this.updating=true;
this.button.setValue(_c);
delete this.updating;
}
if(dojo.isIE){
this._savedSelection=this.editor._getBookmark();
}
this._focusHandle=dijit.getFocus(this.editor.iframe);
},setToolbar:function(){
this.inherited(arguments);
var _10=this.button;
if(!_10.id){
_10.id=dijit._scopeName+"EditorButton-"+this.command+(this._uniqueId++);
}
var _11=dojo.doc.createElement("label");
dojo.addClass(_11,"dijit dijitReset dijitLeft dijitInline");
_11.setAttribute("for",_10.id);
var _12=dojo.i18n.getLocalization("dijit._editor","FontChoice");
_11.appendChild(dojo.doc.createTextNode(_12[this.command]));
dojo.place(_11,this.button.domNode,"before");
}});
dojo.subscribe(dijit._scopeName+".Editor.getPlugin",null,function(o){
if(o.plugin){
return;
}
switch(o.args.name){
case "fontName":
case "fontSize":
case "formatBlock":
o.plugin=new dijit._editor.plugins.FontChoice({command:o.args.name});
}
});
}

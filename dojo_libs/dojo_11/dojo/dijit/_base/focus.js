/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dijit._base.focus"]){
dojo._hasResource["dijit._base.focus"]=true;
dojo.provide("dijit._base.focus");
dojo.mixin(dijit,{_curFocus:null,_prevFocus:null,isCollapsed:function(){
var _1=dojo.global;
var _2=dojo.doc;
if(_2.selection){
return !_2.selection.createRange().text;
}else{
var _3=_1.getSelection();
if(dojo.isString(_3)){
return !_3;
}else{
return _3.isCollapsed||!_3.toString();
}
}
},getBookmark:function(){
var _4,_5=dojo.doc.selection;
if(_5){
var _6=_5.createRange();
if(_5.type.toUpperCase()=="CONTROL"){
if(_6.length){
_4=[];
var i=0,_8=_6.length;
while(i<_8){
_4.push(_6.item(i++));
}
}else{
_4=null;
}
}else{
_4=_6.getBookmark();
}
}else{
if(window.getSelection){
_5=dojo.global.getSelection();
if(_5){
_6=_5.getRangeAt(0);
_4=_6.cloneRange();
}
}else{
console.warn("No idea how to store the current selection for this browser!");
}
}
return _4;
},moveToBookmark:function(_9){
var _a=dojo.doc;
if(_a.selection){
var _b;
if(dojo.isArray(_9)){
_b=_a.body.createControlRange();
dojo.forEach(_9,"range.addElement(item)");
}else{
_b=_a.selection.createRange();
_b.moveToBookmark(_9);
}
_b.select();
}else{
var _c=dojo.global.getSelection&&dojo.global.getSelection();
if(_c&&_c.removeAllRanges){
_c.removeAllRanges();
_c.addRange(_9);
}else{
console.warn("No idea how to restore selection for this browser!");
}
}
},getFocus:function(_d,_e){
return {node:_d&&dojo.isDescendant(dijit._curFocus,_d.domNode)?dijit._prevFocus:dijit._curFocus,bookmark:!dojo.withGlobal(_e||dojo.global,dijit.isCollapsed)?dojo.withGlobal(_e||dojo.global,dijit.getBookmark):null,openedForWindow:_e};
},focus:function(_f){
if(!_f){
return;
}
var _10="node" in _f?_f.node:_f,_11=_f.bookmark,_12=_f.openedForWindow;
if(_10){
var _13=(_10.tagName.toLowerCase()=="iframe")?_10.contentWindow:_10;
if(_13&&_13.focus){
try{
_13.focus();
}
catch(e){
}
}
dijit._onFocusNode(_10);
}
if(_11&&dojo.withGlobal(_12||dojo.global,dijit.isCollapsed)){
if(_12){
_12.focus();
}
try{
dojo.withGlobal(_12||dojo.global,dijit.moveToBookmark,null,[_11]);
}
catch(e){
}
}
},_activeStack:[],registerWin:function(_14){
if(!_14){
_14=window;
}
dojo.connect(_14.document,"onmousedown",function(evt){
dijit._justMouseDowned=true;
setTimeout(function(){
dijit._justMouseDowned=false;
},0);
dijit._onTouchNode(evt.target||evt.srcElement);
});
var _16=_14.document.body||_14.document.getElementsByTagName("body")[0];
if(_16){
if(dojo.isIE){
_16.attachEvent("onactivate",function(evt){
if(evt.srcElement.tagName.toLowerCase()!="body"){
dijit._onFocusNode(evt.srcElement);
}
});
_16.attachEvent("ondeactivate",function(evt){
dijit._onBlurNode(evt.srcElement);
});
}else{
_16.addEventListener("focus",function(evt){
dijit._onFocusNode(evt.target);
},true);
_16.addEventListener("blur",function(evt){
dijit._onBlurNode(evt.target);
},true);
}
}
_16=null;
},_onBlurNode:function(_1b){
dijit._prevFocus=dijit._curFocus;
dijit._curFocus=null;
if(dijit._justMouseDowned){
return;
}
if(dijit._clearActiveWidgetsTimer){
clearTimeout(dijit._clearActiveWidgetsTimer);
}
dijit._clearActiveWidgetsTimer=setTimeout(function(){
delete dijit._clearActiveWidgetsTimer;
dijit._setStack([]);
dijit._prevFocus=null;
},100);
},_onTouchNode:function(_1c){
if(dijit._clearActiveWidgetsTimer){
clearTimeout(dijit._clearActiveWidgetsTimer);
delete dijit._clearActiveWidgetsTimer;
}
var _1d=[];
try{
while(_1c){
if(_1c.dijitPopupParent){
_1c=dijit.byId(_1c.dijitPopupParent).domNode;
}else{
if(_1c.tagName&&_1c.tagName.toLowerCase()=="body"){
if(_1c===dojo.body()){
break;
}
_1c=dijit.getDocumentWindow(_1c.ownerDocument).frameElement;
}else{
var id=_1c.getAttribute&&_1c.getAttribute("widgetId");
if(id){
_1d.unshift(id);
}
_1c=_1c.parentNode;
}
}
}
}
catch(e){
}
dijit._setStack(_1d);
},_onFocusNode:function(_1f){
if(_1f&&_1f.tagName&&_1f.tagName.toLowerCase()=="body"){
return;
}
dijit._onTouchNode(_1f);
if(_1f==dijit._curFocus){
return;
}
if(dijit._curFocus){
dijit._prevFocus=dijit._curFocus;
}
dijit._curFocus=_1f;
dojo.publish("focusNode",[_1f]);
},_setStack:function(_20){
var _21=dijit._activeStack;
dijit._activeStack=_20;
for(var _22=0;_22<Math.min(_21.length,_20.length);_22++){
if(_21[_22]!=_20[_22]){
break;
}
}
for(var i=_21.length-1;i>=_22;i--){
var _24=dijit.byId(_21[i]);
if(_24){
_24._focused=false;
_24._hasBeenBlurred=true;
if(_24._onBlur){
_24._onBlur();
}
if(_24._setStateClass){
_24._setStateClass();
}
dojo.publish("widgetBlur",[_24]);
}
}
for(i=_22;i<_20.length;i++){
_24=dijit.byId(_20[i]);
if(_24){
_24._focused=true;
if(_24._onFocus){
_24._onFocus();
}
if(_24._setStateClass){
_24._setStateClass();
}
dojo.publish("widgetFocus",[_24]);
}
}
}});
dojo.addOnLoad(dijit.registerWin);
}

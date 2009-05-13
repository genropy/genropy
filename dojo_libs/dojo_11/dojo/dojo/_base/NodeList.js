/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dojo._base.NodeList"]){
dojo._hasResource["dojo._base.NodeList"]=true;
dojo.provide("dojo._base.NodeList");
dojo.require("dojo._base.lang");
dojo.require("dojo._base.array");
(function(){
var d=dojo;
var _2=function(_3){
_3.constructor=dojo.NodeList;
dojo._mixin(_3,dojo.NodeList.prototype);
return _3;
};
var _4=function(_5,_6){
return function(){
var _a=arguments;
var aa=d._toArray(_a,0,[null]);
var s=this.map(function(i){
aa[0]=i;
return d[_5].apply(d,aa);
});
return (_6||((_a.length>1)||!d.isString(_a[0])))?this:s;
};
};
dojo.NodeList=function(){
return _2(Array.apply(null,arguments));
};
dojo.NodeList._wrap=_2;
dojo.extend(dojo.NodeList,{slice:function(){
var a=dojo._toArray(arguments);
return _2(a.slice.apply(this,a));
},splice:function(){
var a=dojo._toArray(arguments);
return _2(a.splice.apply(this,a));
},concat:function(){
var a=dojo._toArray(arguments,0,[this]);
return _2(a.concat.apply([],a));
},indexOf:function(_e,_f){
return d.indexOf(this,_e,_f);
},lastIndexOf:function(){
return d.lastIndexOf.apply(d,d._toArray(arguments,0,[this]));
},every:function(_10,_11){
return d.every(this,_10,_11);
},some:function(_12,_13){
return d.some(this,_12,_13);
},map:function(_14,obj){
return d.map(this,_14,obj,d.NodeList);
},forEach:function(_16,_17){
d.forEach(this,_16,_17);
return this;
},coords:function(){
return d.map(this,d.coords);
},attr:_4("attr"),style:_4("style"),addClass:_4("addClass",true),removeClass:_4("removeClass",true),toggleClass:_4("toggleClass",true),connect:_4("connect",true),place:function(_18,_19){
var _1a=d.query(_18)[0];
return this.forEach(function(i){
d.place(i,_1a,(_19||"last"));
});
},orphan:function(_1c){
var _1d=_1c?d._filterQueryResult(this,_1c):this;
_1d.forEach(function(_1e){
if(_1e.parentNode){
_1e.parentNode.removeChild(_1e);
}
});
return _1d;
},adopt:function(_1f,_20){
var _21=this[0];
return d.query(_1f).forEach(function(ai){
d.place(ai,_21,_20||"last");
});
},query:function(_23){
if(!_23){
return this;
}
var ret=d.NodeList();
this.forEach(function(_25){
d.query(_23,_25).forEach(function(_26){
if(_26!==undefined){
ret.push(_26);
}
});
});
return ret;
},filter:function(_27){
var _28=this;
var _a=arguments;
var r=d.NodeList();
var rp=function(t){
if(t!==undefined){
r.push(t);
}
};
if(d.isString(_27)){
_28=d._filterQueryResult(this,_a[0]);
if(_a.length==1){
return _28;
}
_a.shift();
}
d.forEach(d.filter(_28,_a[0],_a[1]),rp);
return r;
},addContent:function(_2d,_2e){
var ta=d.doc.createElement("span");
if(d.isString(_2d)){
ta.innerHTML=_2d;
}else{
ta.appendChild(_2d);
}
if(_2e===undefined){
_2e="last";
}
var ct=(_2e=="first"||_2e=="after")?"lastChild":"firstChild";
this.forEach(function(_31){
var tn=ta.cloneNode(true);
while(tn[ct]){
d.place(tn[ct],_31,_2e);
}
});
return this;
},empty:function(){
return this.forEach("item.innerHTML='';");
},instantiate:function(_33,_34){
var c=d.isFunction(_33)?_33:d.getObject(_33);
return this.forEach(function(i){
new c(_34||{},i);
});
}});
d.forEach(["blur","focus","click","keydown","keypress","keyup","mousedown","mouseenter","mouseleave","mousemove","mouseout","mouseover","mouseup"],function(evt){
var _oe="on"+evt;
dojo.NodeList.prototype[_oe]=function(a,b){
return this.connect(_oe,a,b);
};
});
})();
}

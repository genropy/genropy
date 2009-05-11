/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dojo._base.declare"]){
dojo._hasResource["dojo._base.declare"]=true;
dojo.provide("dojo._base.declare");
dojo.require("dojo._base.lang");
dojo.declare=function(_1,_2,_3){
var dd=arguments.callee,_5;
if(dojo.isArray(_2)){
_5=_2;
_2=_5.shift();
}
if(_5){
dojo.forEach(_5,function(m){
if(!m){
throw (_1+": mixin #"+i+" is null");
}
_2=dd._delegate(_2,m);
});
}
var _8=(_3||0).constructor,_9=dd._delegate(_2),fn;
for(var i in _3){
if(dojo.isFunction(fn=_3[i])&&!0[i]){
fn.nom=i;
}
}
dojo.extend(_9,{declaredClass:_1,_constructor:_8,preamble:null},_3||0);
_9.prototype.constructor=_9;
return dojo.setObject(_1,_9);
};
dojo.mixin(dojo.declare,{_delegate:function(_b,_c){
var bp=(_b||0).prototype,mp=(_c||0).prototype;
var _f=dojo.declare._makeCtor();
dojo.mixin(_f,{superclass:bp,mixin:mp,extend:dojo.declare._extend});
if(_b){
_f.prototype=dojo._delegate(bp);
}
dojo.extend(_f,dojo.declare._core,mp||0,{_constructor:null,preamble:null});
_f.prototype.constructor=_f;
_f.prototype.declaredClass=(bp||0).declaredClass+"_"+(mp||0).declaredClass;
return _f;
},_extend:function(_10){
for(var i in _10){
if(dojo.isFunction(fn=_10[i])&&!0[i]){
fn.nom=i;
}
}
dojo.extend(this,_10);
},_makeCtor:function(){
return function(){
this._construct(arguments);
};
},_core:{_construct:function(_12){
var c=_12.callee,s=c.superclass,ct=s&&s.constructor,m=c.mixin,mct=m&&m.constructor,a=_12,ii,fn;
if(a[0]){
if(((fn=a[0].preamble))){
a=fn.apply(this,a)||a;
}
}
if((fn=c.prototype.preamble)){
a=fn.apply(this,a)||a;
}
if(ct&&ct.apply){
ct.apply(this,a);
}
if(mct&&mct.apply){
mct.apply(this,a);
}
if((ii=c.prototype._constructor)){
ii.apply(this,_12);
}
if(this.constructor.prototype==c.prototype&&(ct=this.postscript)){
ct.apply(this,_12);
}
},_findMixin:function(_1b){
var c=this.constructor,p,m;
while(c){
p=c.superclass;
m=c.mixin;
if(m==_1b||(m instanceof _1b.constructor)){
return p;
}
if(m&&(m=m._findMixin(_1b))){
return m;
}
c=p&&p.constructor;
}
},_findMethod:function(_1f,_20,_21,has){
var p=_21,c,m,f;
do{
c=p.constructor;
m=c.mixin;
if(m&&(m=this._findMethod(_1f,_20,m,has))){
return m;
}
if((f=p[_1f])&&(has==(f==_20))){
return p;
}
p=c.superclass;
}while(p);
return !has&&(p=this._findMixin(_21))&&this._findMethod(_1f,_20,p,has);
},inherited:function(_27,_28,_29){
var a=arguments;
if(!dojo.isString(a[0])){
_29=_28;
_28=_27;
_27=_28.callee.nom;
}
a=_29||_28;
var c=_28.callee,p=this.constructor.prototype,fn,mp;
if(this[_27]!=c||p[_27]==c){
mp=this._findMethod(_27,c,p,true);
if(!mp){
throw (this.declaredClass+": inherited method \""+_27+"\" mismatch");
}
p=this._findMethod(_27,c,mp,false);
}
fn=p&&p[_27];
if(!fn){
throw (mp.declaredClass+": inherited method \""+_27+"\" not found");
}
return fn.apply(this,a);
}}});
}

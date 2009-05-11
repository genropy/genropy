/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dojo.foo"]){
dojo._hasResource["dojo.foo"]=true;
(function(){
var d=dojo;
d.mixin(d,{_loadedModules:{},_inFlightCount:0,_hasResource:{},_modulePrefixes:{dojo:{name:"dojo",value:"."},doh:{name:"doh",value:"../util/doh"},tests:{name:"tests",value:"tests"}},_moduleHasPrefix:function(_2){
var mp=this._modulePrefixes;
return !!(mp[_2]&&mp[_2].value);
},_getModulePrefix:function(_4){
var mp=this._modulePrefixes;
if(this._moduleHasPrefix(_4)){
return mp[_4].value;
}
return _4;
},_loadedUrls:[],_postLoad:false,_loaders:[],_unloaders:[],_loadNotifying:false});
dojo._loadPath=function(_6,_7,cb){
var _9=((_6.charAt(0)=="/"||_6.match(/^\w+:/))?"":this.baseUrl)+_6;
try{
return !_7?this._loadUri(_9,cb):this._loadUriAndCheck(_9,_7,cb);
}
catch(e){
console.error(e);
return false;
}
};
dojo._loadUri=function(_a,cb){
if(this._loadedUrls[_a]){
return true;
}
var _c=this._getText(_a,true);
if(!_c){
return false;
}
this._loadedUrls[_a]=true;
this._loadedUrls.push(_a);
if(cb){
_c="("+_c+")";
}else{
_c=this._scopePrefix+_c+this._scopeSuffix;
}
if(d.isMoz){
_c+="\r\n//@ sourceURL="+_a;
}
var _d=d["eval"](_c);
if(cb){
cb(_d);
}
return true;
};
dojo._loadUriAndCheck=function(_e,_f,cb){
var ok=false;
try{
ok=this._loadUri(_e,cb);
}
catch(e){
console.error("failed loading "+_e+" with error: "+e);
}
return !!(ok&&this._loadedModules[_f]);
};
dojo.loaded=function(){
this._loadNotifying=true;
this._postLoad=true;
var mll=d._loaders;
this._loaders=[];
for(var x=0;x<mll.length;x++){
try{
mll[x]();
}
catch(e){
throw e;
console.error("dojo.addOnLoad callback failed: "+e,e);
}
}
this._loadNotifying=false;
if(d._postLoad&&d._inFlightCount==0&&mll.length){
d._callLoaded();
}
};
dojo.unloaded=function(){
var mll=this._unloaders;
while(mll.length){
(mll.pop())();
}
};
var _15=function(arr,obj,fn){
if(!fn){
arr.push(obj);
}else{
if(fn){
var _19=(typeof fn=="string")?obj[fn]:fn;
arr.push(function(){
_19.call(obj);
});
}
}
};
dojo.addOnLoad=function(obj,_1b){
_15(d._loaders,obj,_1b);
if(d._postLoad&&d._inFlightCount==0&&!d._loadNotifying){
d._callLoaded();
}
};
dojo.addOnUnload=function(obj,_1d){
_15(d._unloaders,obj,_1d);
};
dojo._modulesLoaded=function(){
if(d._postLoad){
return;
}
if(d._inFlightCount>0){
console.warn("files still in flight!");
return;
}
d._callLoaded();
};
dojo._callLoaded=function(){
if(typeof setTimeout=="object"||(dojo.config.useXDomain&&d.isOpera)){
if(dojo.isAIR){
setTimeout(function(){
dojo.loaded();
},0);
}else{
setTimeout(dojo._scopeName+".loaded();",0);
}
}else{
d.loaded();
}
};
dojo._getModuleSymbols=function(_1e){
var _1f=_1e.split(".");
for(var i=_1f.length;i>0;i--){
var _21=_1f.slice(0,i).join(".");
if((i==1)&&!this._moduleHasPrefix(_21)){
_1f[0]="../"+_1f[0];
}else{
var _22=this._getModulePrefix(_21);
if(_22!=_21){
_1f.splice(0,i,_22);
break;
}
}
}
return _1f;
};
dojo._global_omit_module_check=false;
dojo._loadModule=dojo.require=function(_23,_24){
_24=this._global_omit_module_check||_24;
var _25=this._loadedModules[_23];
if(_25){
return _25;
}
var _26=this._getModuleSymbols(_23).join("/")+".js";
var _27=(!_24)?_23:null;
var ok=this._loadPath(_26,_27);
if(!ok&&!_24){
throw new Error("Could not load '"+_23+"'; last tried '"+_26+"'");
}
if(!_24&&!this._isXDomain){
_25=this._loadedModules[_23];
if(!_25){
throw new Error("symbol '"+_23+"' is not defined after loading '"+_26+"'");
}
}
return _25;
};
dojo.provide=function(_29){
_29=_29+"";
return (d._loadedModules[_29]=d.getObject(_29,true));
};
dojo.platformRequire=function(_2a){
var _2b=_2a.common||[];
var _2c=_2b.concat(_2a[d._name]||_2a["default"]||[]);
for(var x=0;x<_2c.length;x++){
var _2e=_2c[x];
if(_2e.constructor==Array){
d._loadModule.apply(d,_2e);
}else{
d._loadModule(_2e);
}
}
};
dojo.requireIf=function(_2f,_30){
if(_2f===true){
var _31=[];
for(var i=1;i<arguments.length;i++){
_31.push(arguments[i]);
}
d.require.apply(d,_31);
}
};
dojo.requireAfterIf=d.requireIf;
dojo.registerModulePath=function(_33,_34){
d._modulePrefixes[_33]={name:_33,value:_34};
};
dojo.requireLocalization=function(_35,_36,_37,_38){
d.require("dojo.i18n");
d.i18n._requireLocalization.apply(d.hostenv,arguments);
};
var ore=new RegExp("^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\\?([^#]*))?(#(.*))?$");
var ire=new RegExp("^((([^:]+:)?([^@]+))@)?([^:]*)(:([0-9]+))?$");
dojo._Url=function(){
var n=null;
var _a=arguments;
var uri=[_a[0]];
for(var i=1;i<_a.length;i++){
if(!_a[i]){
continue;
}
var _3f=new d._Url(_a[i]+"");
var _40=new d._Url(uri[0]+"");
if(_3f.path==""&&!_3f.scheme&&!_3f.authority&&!_3f.query){
if(_3f.fragment!=n){
_40.fragment=_3f.fragment;
}
_3f=_40;
}else{
if(!_3f.scheme){
_3f.scheme=_40.scheme;
if(!_3f.authority){
_3f.authority=_40.authority;
if(_3f.path.charAt(0)!="/"){
var _41=_40.path.substring(0,_40.path.lastIndexOf("/")+1)+_3f.path;
var _42=_41.split("/");
for(var j=0;j<_42.length;j++){
if(_42[j]=="."){
if(j==_42.length-1){
_42[j]="";
}else{
_42.splice(j,1);
j--;
}
}else{
if(j>0&&!(j==1&&_42[0]=="")&&_42[j]==".."&&_42[j-1]!=".."){
if(j==(_42.length-1)){
_42.splice(j,1);
_42[j-1]="";
}else{
_42.splice(j-1,2);
j-=2;
}
}
}
}
_3f.path=_42.join("/");
}
}
}
}
uri=[];
if(_3f.scheme){
uri.push(_3f.scheme,":");
}
if(_3f.authority){
uri.push("//",_3f.authority);
}
uri.push(_3f.path);
if(_3f.query){
uri.push("?",_3f.query);
}
if(_3f.fragment){
uri.push("#",_3f.fragment);
}
}
this.uri=uri.join("");
var r=this.uri.match(ore);
this.scheme=r[2]||(r[1]?"":n);
this.authority=r[4]||(r[3]?"":n);
this.path=r[5];
this.query=r[7]||(r[6]?"":n);
this.fragment=r[9]||(r[8]?"":n);
if(this.authority!=n){
r=this.authority.match(ire);
this.user=r[3]||n;
this.password=r[4]||n;
this.host=r[5];
this.port=r[7]||n;
}
};
dojo._Url.prototype.toString=function(){
return this.uri;
};
dojo.moduleUrl=function(_45,url){
var loc=d._getModuleSymbols(_45).join("/");
if(!loc){
return null;
}
if(loc.lastIndexOf("/")!=loc.length-1){
loc+="/";
}
var _48=loc.indexOf(":");
if(loc.charAt(0)!="/"&&(_48==-1||_48>loc.indexOf("/"))){
loc=d.baseUrl+loc;
}
return new d._Url(loc,url);
};
})();
}

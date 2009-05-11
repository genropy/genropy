/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dojo._base.query"]){
dojo._hasResource["dojo._base.query"]=true;
dojo.provide("dojo._base.query");
dojo.require("dojo._base.NodeList");
(function(){
var d=dojo;
var _2=dojo.isIE?"children":"childNodes";
var _3=false;
var _4=function(_5){
if(">~+".indexOf(_5.charAt(_5.length-1))>=0){
_5+=" *";
}
_5+=" ";
var ts=function(s,e){
return d.trim(_5.slice(s,e));
};
var _9=[];
var _a=-1;
var _b=-1;
var _c=-1;
var _d=-1;
var _e=-1;
var _f=-1;
var _10=-1;
var lc="";
var cc="";
var _13;
var x=0;
var ql=_5.length;
var _16=null;
var _cp=null;
var _18=function(){
if(_10>=0){
var tv=(_10==x)?null:ts(_10,x).toLowerCase();
_16[(">~+".indexOf(tv)<0)?"tag":"oper"]=tv;
_10=-1;
}
};
var _1a=function(){
if(_f>=0){
_16.id=ts(_f,x).replace(/\\/g,"");
_f=-1;
}
};
var _1b=function(){
if(_e>=0){
_16.classes.push(ts(_e+1,x).replace(/\\/g,""));
_e=-1;
}
};
var _1c=function(){
_1a();
_18();
_1b();
};
for(;lc=cc,cc=_5.charAt(x),x<ql;x++){
if(lc=="\\"){
continue;
}
if(!_16){
_13=x;
_16={query:null,pseudos:[],attrs:[],classes:[],tag:null,oper:null,id:null};
_10=x;
}
if(_a>=0){
if(cc=="]"){
if(!_cp.attr){
_cp.attr=ts(_a+1,x);
}else{
_cp.matchFor=ts((_c||_a+1),x);
}
var cmf=_cp.matchFor;
if(cmf){
if((cmf.charAt(0)=="\"")||(cmf.charAt(0)=="'")){
_cp.matchFor=cmf.substring(1,cmf.length-1);
}
}
_16.attrs.push(_cp);
_cp=null;
_a=_c=-1;
}else{
if(cc=="="){
var _1e=("|~^$*".indexOf(lc)>=0)?lc:"";
_cp.type=_1e+cc;
_cp.attr=ts(_a+1,x-_1e.length);
_c=x+1;
}
}
}else{
if(_b>=0){
if(cc==")"){
if(_d>=0){
_cp.value=ts(_b+1,x);
}
_d=_b=-1;
}
}else{
if(cc=="#"){
_1c();
_f=x+1;
}else{
if(cc=="."){
_1c();
_e=x;
}else{
if(cc==":"){
_1c();
_d=x;
}else{
if(cc=="["){
_1c();
_a=x;
_cp={};
}else{
if(cc=="("){
if(_d>=0){
_cp={name:ts(_d+1,x),value:null};
_16.pseudos.push(_cp);
}
_b=x;
}else{
if(cc==" "&&lc!=cc){
_1c();
if(_d>=0){
_16.pseudos.push({name:ts(_d+1,x)});
}
_16.hasLoops=(_16.pseudos.length||_16.attrs.length||_16.classes.length);
_16.query=ts(_13,x);
_16.tag=(_16["oper"])?null:(_16.tag||"*");
_9.push(_16);
_16=null;
}
}
}
}
}
}
}
}
}
return _9;
};
var _1f={"*=":function(_20,_21){
return "[contains(@"+_20+", '"+_21+"')]";
},"^=":function(_22,_23){
return "[starts-with(@"+_22+", '"+_23+"')]";
},"$=":function(_24,_25){
return "[substring(@"+_24+", string-length(@"+_24+")-"+(_25.length-1)+")='"+_25+"']";
},"~=":function(_26,_27){
return "[contains(concat(' ',@"+_26+",' '), ' "+_27+" ')]";
},"|=":function(_28,_29){
return "[contains(concat(' ',@"+_28+",' '), ' "+_29+"-')]";
},"=":function(_2a,_2b){
return "[@"+_2a+"='"+_2b+"']";
}};
var _2c=function(_2d,_2e,_2f,_30){
d.forEach(_2e.attrs,function(_31){
var _32;
if(_31.type&&_2d[_31.type]){
_32=_2d[_31.type](_31.attr,_31.matchFor);
}else{
if(_31.attr.length){
_32=_2f(_31.attr);
}
}
if(_32){
_30(_32);
}
});
};
var _33=function(_34){
var _35=".";
var _36=_4(d.trim(_34));
while(_36.length){
var tqp=_36.shift();
var _38;
var _39="";
if(tqp.oper==">"){
_38="/";
tqp=_36.shift();
}else{
if(tqp.oper=="~"){
_38="/following-sibling::";
tqp=_36.shift();
}else{
if(tqp.oper=="+"){
_38="/following-sibling::";
_39="[position()=1]";
tqp=_36.shift();
}else{
_38="//";
}
}
}
_35+=_38+tqp.tag+_39;
if(tqp.id){
_35+="[@id='"+tqp.id+"'][1]";
}
d.forEach(tqp.classes,function(cn){
var cnl=cn.length;
var _3c=" ";
if(cn.charAt(cnl-1)=="*"){
_3c="";
cn=cn.substr(0,cnl-1);
}
_35+="[contains(concat(' ',@class,' '), ' "+cn+_3c+"')]";
});
_2c(_1f,tqp,function(_3d){
return "[@"+_3d+"]";
},function(_3e){
_35+=_3e;
});
}
return _35;
};
var _3f={};
var _40=function(_41){
if(_3f[_41]){
return _3f[_41];
}
var doc=d.doc;
var _43=_33(_41);
var tf=function(_45){
var ret=[];
var _47;
try{
_47=doc.evaluate(_43,_45,null,XPathResult.ANY_TYPE,null);
}
catch(e){
console.debug("failure in exprssion:",_43,"under:",_45);
console.debug(e);
}
var _48=_47.iterateNext();
while(_48){
ret.push(_48);
_48=_47.iterateNext();
}
return ret;
};
return _3f[_41]=tf;
};
var _49={};
var _4a={};
var _4b=function(_4c,_4d){
if(!_4c){
return _4d;
}
if(!_4d){
return _4c;
}
return function(){
return _4c.apply(window,arguments)&&_4d.apply(window,arguments);
};
};
var _4e=function(_4f){
var ret=[];
var te,x=0,_53=_4f[_2];
while(te=_53[x++]){
if(te.nodeType==1){
ret.push(te);
}
}
return ret;
};
var _54=function(_55,_56){
var ret=[];
var te=_55;
while(te=te.nextSibling){
if(te.nodeType==1){
ret.push(te);
if(_56){
break;
}
}
}
return ret;
};
var _59=function(_5a,_5b,_5c,idx){
var _5e=idx+1;
var _5f=(_5b.length==_5e);
var tqp=_5b[idx];
if(tqp.oper){
var ecn=(tqp.oper==">")?_4e(_5a):_54(_5a,(tqp.oper=="+"));
if(!ecn||!ecn.length){
return;
}
_5e++;
_5f=(_5b.length==_5e);
var tf=_63(_5b[idx+1]);
for(var x=0,_65=ecn.length,te;x<_65,te=ecn[x];x++){
if(tf(te)){
if(_5f){
_5c.push(te);
}else{
_59(te,_5b,_5c,_5e);
}
}
}
}
var _67=_68(tqp)(_5a);
if(_5f){
while(_67.length){
_5c.push(_67.shift());
}
}else{
while(_67.length){
_59(_67.shift(),_5b,_5c,_5e);
}
}
};
var _69=function(_6a,_6b){
var ret=[];
var x=_6a.length-1,te;
while(te=_6a[x--]){
_59(te,_6b,ret,0);
}
return ret;
};
var _63=function(q){
if(_49[q.query]){
return _49[q.query];
}
var ff=null;
if(q.tag){
if(q.tag=="*"){
ff=_4b(ff,function(_71){
return (_71.nodeType==1);
});
}else{
ff=_4b(ff,function(_72){
return ((_72.nodeType==1)&&(q.tag==_72.tagName.toLowerCase()));
});
}
}
if(q.id){
ff=_4b(ff,function(_73){
return ((_73.nodeType==1)&&(_73.id==q.id));
});
}
if(q.hasLoops){
ff=_4b(ff,_74(q));
}
return _49[q.query]=ff;
};
var _75=function(_76){
var pn=_76.parentNode;
var pnc=pn.childNodes;
var _79=-1;
var _7a=pn.firstChild;
if(!_7a){
return _79;
}
var ci=_76["__cachedIndex"];
var cl=pn["__cachedLength"];
if(((typeof cl=="number")&&(cl!=pnc.length))||(typeof ci!="number")){
pn["__cachedLength"]=pnc.length;
var idx=1;
do{
if(_7a===_76){
_79=idx;
}
if(_7a.nodeType==1){
_7a["__cachedIndex"]=idx;
idx++;
}
_7a=_7a.nextSibling;
}while(_7a);
}else{
_79=ci;
}
return _79;
};
var _7e=0;
var _7f="";
var _80=function(_81,_82){
if(_82=="class"){
return _81.className||_7f;
}
if(_82=="for"){
return _81.htmlFor||_7f;
}
return _81.getAttribute(_82,2)||_7f;
};
var _83={"*=":function(_84,_85){
return function(_86){
return (_80(_86,_84).indexOf(_85)>=0);
};
},"^=":function(_87,_88){
return function(_89){
return (_80(_89,_87).indexOf(_88)==0);
};
},"$=":function(_8a,_8b){
var _8c=" "+_8b;
return function(_8d){
var ea=" "+_80(_8d,_8a);
return (ea.lastIndexOf(_8b)==(ea.length-_8b.length));
};
},"~=":function(_8f,_90){
var _91=" "+_90+" ";
return function(_92){
var ea=" "+_80(_92,_8f)+" ";
return (ea.indexOf(_91)>=0);
};
},"|=":function(_94,_95){
var _96=" "+_95+"-";
return function(_97){
var ea=" "+(_97.getAttribute(_94,2)||"");
return ((ea==_95)||(ea.indexOf(_96)==0));
};
},"=":function(_99,_9a){
return function(_9b){
return (_80(_9b,_99)==_9a);
};
}};
var _9c={"first-child":function(_9d,_9e){
return function(_9f){
if(_9f.nodeType!=1){
return false;
}
var fc=_9f.previousSibling;
while(fc&&(fc.nodeType!=1)){
fc=fc.previousSibling;
}
return (!fc);
};
},"last-child":function(_a1,_a2){
return function(_a3){
if(_a3.nodeType!=1){
return false;
}
var nc=_a3.nextSibling;
while(nc&&(nc.nodeType!=1)){
nc=nc.nextSibling;
}
return (!nc);
};
},"empty":function(_a5,_a6){
return function(_a7){
var cn=_a7.childNodes;
var cnl=_a7.childNodes.length;
for(var x=cnl-1;x>=0;x--){
var nt=cn[x].nodeType;
if((nt==1)||(nt==3)){
return false;
}
}
return true;
};
},"contains":function(_ac,_ad){
return function(_ae){
return (_ae.innerHTML.indexOf(_ad)>=0);
};
},"not":function(_af,_b0){
var ntf=_63(_4(_b0)[0]);
return function(_b2){
return (!ntf(_b2));
};
},"nth-child":function(_b3,_b4){
var pi=parseInt;
if(_b4=="odd"){
return function(_b6){
return (((_75(_b6))%2)==1);
};
}else{
if((_b4=="2n")||(_b4=="even")){
return function(_b7){
return ((_75(_b7)%2)==0);
};
}else{
if(_b4.indexOf("0n+")==0){
var _b8=pi(_b4.substr(3));
return function(_b9){
return (_b9.parentNode[_2][_b8-1]===_b9);
};
}else{
if((_b4.indexOf("n+")>0)&&(_b4.length>3)){
var _ba=_b4.split("n+",2);
var _bb=pi(_ba[0]);
var idx=pi(_ba[1]);
return function(_bd){
return ((_75(_bd)%_bb)==idx);
};
}else{
if(_b4.indexOf("n")==-1){
var _b8=pi(_b4);
return function(_be){
return (_75(_be)==_b8);
};
}
}
}
}
}
}};
var _bf=(d.isIE)?function(_c0){
var clc=_c0.toLowerCase();
return function(_c2){
return _c2[_c0]||_c2[clc];
};
}:function(_c3){
return function(_c4){
return (_c4&&_c4.getAttribute&&_c4.hasAttribute(_c3));
};
};
var _74=function(_c5){
var _c6=(_4a[_c5.query]||_49[_c5.query]);
if(_c6){
return _c6;
}
var ff=null;
if(_c5.id){
if(_c5.tag!="*"){
ff=_4b(ff,function(_c8){
return (_c8.tagName.toLowerCase()==_c5.tag);
});
}
}
d.forEach(_c5.classes,function(_c9,idx,arr){
var _cc=_c9.charAt(_c9.length-1)=="*";
if(_cc){
_c9=_c9.substr(0,_c9.length-1);
}
var re=new RegExp("(?:^|\\s)"+_c9+(_cc?".*":"")+"(?:\\s|$)");
ff=_4b(ff,function(_ce){
return re.test(_ce.className);
});
ff.count=idx;
});
d.forEach(_c5.pseudos,function(_cf){
if(_9c[_cf.name]){
ff=_4b(ff,_9c[_cf.name](_cf.name,_cf.value));
}
});
_2c(_83,_c5,_bf,function(_d0){
ff=_4b(ff,_d0);
});
if(!ff){
ff=function(){
return true;
};
}
return _4a[_c5.query]=ff;
};
var _d1={};
var _68=function(_d2,_d3){
var _d4=_d1[_d2.query];
if(_d4){
return _d4;
}
if(_d2.id&&!_d2.hasLoops&&!_d2.tag){
return _d1[_d2.query]=function(_d5){
return [d.byId(_d2.id)];
};
}
var _d6=_74(_d2);
var _d7;
if(_d2.tag&&_d2.id&&!_d2.hasLoops){
_d7=function(_d8){
var te=d.byId(_d2.id);
if(_d6(te)){
return [te];
}
};
}else{
var _da;
if(!_d2.hasLoops){
_d7=function(_db){
var ret=[];
var te,x=0,_da=_db.getElementsByTagName(_d2.tag);
while(te=_da[x++]){
ret.push(te);
}
return ret;
};
}else{
_d7=function(_df){
var ret=[];
var te,x=0,_da=_df.getElementsByTagName(_d2.tag);
while(te=_da[x++]){
if(_d6(te)){
ret.push(te);
}
}
return ret;
};
}
}
return _d1[_d2.query]=_d7;
};
var _e3={};
var _e4={"*":d.isIE?function(_e5){
return _e5.all;
}:function(_e6){
return _e6.getElementsByTagName("*");
},"~":_54,"+":function(_e7){
return _54(_e7,true);
},">":_4e};
var _e8=function(_e9){
var _ea=_4(d.trim(_e9));
if(_ea.length==1){
var tt=_68(_ea[0]);
tt.nozip=true;
return tt;
}
var sqf=function(_ed){
var _ee=_ea.slice(0);
var _ef;
if(_ee[0].oper==">"){
_ef=[_ed];
}else{
_ef=_68(_ee.shift())(_ed);
}
return _69(_ef,_ee);
};
return sqf;
};
var _f0=((document["evaluate"]&&!d.isSafari)?function(_f1){
var _f2=_f1.split(" ");
if((document["evaluate"])&&(_f1.indexOf(":")==-1)&&(_f1.indexOf("+")==-1)){
if(((_f2.length>2)&&(_f1.indexOf(">")==-1))||(_f2.length>3)||(_f1.indexOf("[")>=0)||((1==_f2.length)&&(0<=_f1.indexOf(".")))){
return _40(_f1);
}
}
return _e8(_f1);
}:_e8);
var _f3=function(_f4){
var qcz=_f4.charAt(0);
if(d.doc["querySelectorAll"]&&((!d.isSafari)||(d.isSafari>3.1))&&(">+~".indexOf(qcz)==-1)){
return function(_f6){
var r=_f6.querySelectorAll(_f4);
r.nozip=true;
return r;
};
}
if(_e4[_f4]){
return _e4[_f4];
}
if(0>_f4.indexOf(",")){
return _e4[_f4]=_f0(_f4);
}else{
var _f8=_f4.split(/\s*,\s*/);
var tf=function(_fa){
var _fb=0;
var ret=[];
var tp;
while(tp=_f8[_fb++]){
ret=ret.concat(_f0(tp,tp.indexOf(" "))(_fa));
}
return ret;
};
return _e4[_f4]=tf;
}
};
var _fe=0;
var _ff=function(arr){
if(arr&&arr.nozip){
return d.NodeList._wrap(arr);
}
var ret=new d.NodeList();
if(!arr){
return ret;
}
if(arr[0]){
ret.push(arr[0]);
}
if(arr.length<2){
return ret;
}
_fe++;
arr[0]["_zipIdx"]=_fe;
for(var x=1,te;te=arr[x];x++){
if(arr[x]["_zipIdx"]!=_fe){
ret.push(te);
}
te["_zipIdx"]=_fe;
}
return ret;
};
d.query=function(_104,root){
if(_104.constructor==d.NodeList){
return _104;
}
if(!d.isString(_104)){
return new d.NodeList(_104);
}
if(d.isString(root)){
root=d.byId(root);
}
return _ff(_f3(_104)(root||d.doc));
};
d.query.pseudos=_9c;
d._filterQueryResult=function(_106,_107){
var tnl=new d.NodeList();
var ff=(_107)?_63(_4(_107)[0]):function(){
return true;
};
for(var x=0,te;te=_106[x];x++){
if(ff(te)){
tnl.push(te);
}
}
return tnl;
};
})();
}

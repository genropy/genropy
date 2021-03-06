/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dojo.date.locale"]){
dojo._hasResource["dojo.date.locale"]=true;
dojo.provide("dojo.date.locale");
dojo.require("dojo.date");
dojo.require("dojo.cldr.supplemental");
dojo.require("dojo.regexp");
dojo.require("dojo.string");
dojo.require("dojo.i18n");
dojo.requireLocalization("dojo.cldr","gregorian",null,"de,en,en-au,en-ca,en-gb,es,es-es,fr,ROOT,it,it-it,ja,ko,ko-kr,pt,pt-br,zh,zh-cn,zh-tw");
(function(){
function formatPattern(_1,_2,_3,_4){
return _4.replace(/([a-z])\1*/ig,function(_5){
var s,_7;
var c=_5.charAt(0);
var l=_5.length;
var _a=["abbr","wide","narrow"];
switch(c){
case "G":
s=_2[(l<4)?"eraAbbr":"eraNames"][_1.getFullYear()<0?0:1];
break;
case "y":
s=_1.getFullYear();
switch(l){
case 1:
break;
case 2:
if(!_3){
s=String(s);
s=s.substr(s.length-2);
break;
}
default:
_7=true;
}
break;
case "Q":
case "q":
s=Math.ceil((_1.getMonth()+1)/3);
_7=true;
break;
case "M":
case "L":
var m=_1.getMonth();
var _c;
switch(l){
case 1:
case 2:
s=m+1;
_7=true;
break;
case 3:
case 4:
case 5:
_c=_a[l-3];
break;
}
if(_c){
var _d=(c=="L")?"standalone":"format";
var _e=["months",_d,_c].join("-");
s=_2[_e][m];
}
break;
case "w":
var _f=0;
s=dojo.date.locale._getWeekOfYear(_1,_f);
_7=true;
break;
case "d":
s=_1.getDate();
_7=true;
break;
case "D":
s=dojo.date.locale._getDayOfYear(_1);
_7=true;
break;
case "E":
case "e":
case "c":
var d=_1.getDay();
var _11;
switch(l){
case 1:
case 2:
if(c=="e"){
var _12=dojo.cldr.supplemental.getFirstDayOfWeek(options.locale);
d=(d-_12+7)%7;
}
if(c!="c"){
s=d+1;
_7=true;
break;
}
case 3:
case 4:
case 5:
_11=_a[l-3];
break;
}
if(_11){
var _13=(c=="c")?"standalone":"format";
var _14=["days",_13,_11].join("-");
s=_2[_14][d];
}
break;
case "a":
var _15=(_1.getHours()<12)?"am":"pm";
s=_2[_15];
break;
case "h":
case "H":
case "K":
case "k":
var h=_1.getHours();
switch(c){
case "h":
s=(h%12)||12;
break;
case "H":
s=h;
break;
case "K":
s=(h%12);
break;
case "k":
s=h||24;
break;
}
_7=true;
break;
case "m":
s=_1.getMinutes();
_7=true;
break;
case "s":
s=_1.getSeconds();
_7=true;
break;
case "S":
s=Math.round(_1.getMilliseconds()*Math.pow(10,l-3));
_7=true;
break;
case "v":
case "z":
s=dojo.date.getTimezoneName(_1);
if(s){
break;
}
l=4;
case "Z":
var _17=_1.getTimezoneOffset();
var tz=[(_17<=0?"+":"-"),dojo.string.pad(Math.floor(Math.abs(_17)/60),2),dojo.string.pad(Math.abs(_17)%60,2)];
if(l==4){
tz.splice(0,0,"GMT");
tz.splice(3,0,":");
}
s=tz.join("");
break;
default:
throw new Error("dojo.date.locale.format: invalid pattern char: "+_4);
}
if(_7){
s=dojo.string.pad(s,l);
}
return s;
});
};
dojo.date.locale.format=function(_19,_1a){
_1a=_1a||{};
var _1b=dojo.i18n.normalizeLocale(_1a.locale);
var _1c=_1a.formatLength||"short";
var _1d=dojo.date.locale._getGregorianBundle(_1b);
var str=[];
var _1f=dojo.hitch(this,formatPattern,_19,_1d,_1a.fullYear);
if(_1a.selector=="year"){
var _20=_19.getFullYear();
if(_1b.match(/^zh|^ja/)){
_20+="???";
}
return _20;
}
if(_1a.selector!="time"){
var _21=_1a.datePattern||_1d["dateFormat-"+_1c];
if(_21){
str.push(_processPattern(_21,_1f));
}
}
if(_1a.selector!="date"){
var _22=_1a.timePattern||_1d["timeFormat-"+_1c];
if(_22){
str.push(_processPattern(_22,_1f));
}
}
var _23=str.join(" ");
return _23;
};
dojo.date.locale.regexp=function(_24){
return dojo.date.locale._parseInfo(_24).regexp;
};
dojo.date.locale._parseInfo=function(_25){
_25=_25||{};
var _26=dojo.i18n.normalizeLocale(_25.locale);
var _27=dojo.date.locale._getGregorianBundle(_26);
var _28=_25.formatLength||"short";
var _29=_25.datePattern||_27["dateFormat-"+_28];
var _2a=_25.timePattern||_27["timeFormat-"+_28];
var _2b;
if(_25.selector=="date"){
_2b=_29;
}else{
if(_25.selector=="time"){
_2b=_2a;
}else{
_2b=_29+" "+_2a;
}
}
var _2c=[];
var re=_processPattern(_2b,dojo.hitch(this,_buildDateTimeRE,_2c,_27,_25));
return {regexp:re,tokens:_2c,bundle:_27};
};
dojo.date.locale.parse=function(_2e,_2f){
var _30=dojo.date.locale._parseInfo(_2f);
var _31=_30.tokens,_32=_30.bundle;
var re=new RegExp("^"+_30.regexp+"$");
var _34=re.exec(_2e);
if(!_34){
return null;
}
var _35=["abbr","wide","narrow"];
var _36=[1970,0,1,0,0,0,0];
var _37="";
var _38=dojo.every(_34,function(v,i){
if(!i){
return true;
}
var _3b=_31[i-1];
var l=_3b.length;
switch(_3b.charAt(0)){
case "y":
if(l!=2&&_2f.strict){
_36[0]=v;
}else{
if(v<100){
v=Number(v);
var _3d=""+new Date().getFullYear();
var _3e=_3d.substring(0,2)*100;
var _3f=Math.min(Number(_3d.substring(2,4))+20,99);
var num=(v<_3f)?_3e+v:_3e-100+v;
_36[0]=num;
}else{
if(_2f.strict){
return false;
}
_36[0]=v;
}
}
break;
case "M":
if(l>2){
var _41=_32["months-format-"+_35[l-3]].concat();
if(!_2f.strict){
v=v.replace(".","").toLowerCase();
_41=dojo.map(_41,function(s){
return s.replace(".","").toLowerCase();
});
}
v=dojo.indexOf(_41,v);
if(v==-1){
return false;
}
}else{
v--;
}
_36[1]=v;
break;
case "E":
case "e":
var _43=_32["days-format-"+_35[l-3]].concat();
if(!_2f.strict){
v=v.toLowerCase();
_43=dojo.map(_43,function(d){
return d.toLowerCase();
});
}
v=dojo.indexOf(_43,v);
if(v==-1){
return false;
}
break;
case "D":
_36[1]=0;
case "d":
_36[2]=v;
break;
case "a":
var am=_2f.am||_32.am;
var pm=_2f.pm||_32.pm;
if(!_2f.strict){
var _47=/\./g;
v=v.replace(_47,"").toLowerCase();
am=am.replace(_47,"").toLowerCase();
pm=pm.replace(_47,"").toLowerCase();
}
if(_2f.strict&&v!=am&&v!=pm){
return false;
}
_37=(v==pm)?"p":(v==am)?"a":"";
break;
case "K":
if(v==24){
v=0;
}
case "h":
case "H":
case "k":
if(v>23){
return false;
}
_36[3]=v;
break;
case "m":
_36[4]=v;
break;
case "s":
_36[5]=v;
break;
case "S":
_36[6]=v;
}
return true;
});
var _48=+_36[3];
if(_37==="p"&&_48<12){
_36[3]=_48+12;
}else{
if(_37==="a"&&_48==12){
_36[3]=0;
}
}
var _49=new Date(_36[0],_36[1],_36[2],_36[3],_36[4],_36[5],_36[6]);
if(_2f.strict){
_49.setFullYear(_36[0]);
}
var _4a=_31.join("");
if(!_38||(_4a.indexOf("M")!=-1&&_49.getMonth()!=_36[1])||(_4a.indexOf("d")!=-1&&_49.getDate()!=_36[2])){
return null;
}
return _49;
};
function _processPattern(_4b,_4c,_4d,_4e){
var _4f=function(x){
return x;
};
_4c=_4c||_4f;
_4d=_4d||_4f;
_4e=_4e||_4f;
var _51=_4b.match(/(''|[^'])+/g);
var _52=false;
dojo.forEach(_51,function(_53,i){
if(!_53){
_51[i]="";
}else{
_51[i]=(_52?_4d:_4c)(_53);
_52=!_52;
}
});
return _4e(_51.join(""));
};
function _buildDateTimeRE(_55,_56,_57,_58){
_58=dojo.regexp.escapeString(_58);
if(!_57.strict){
_58=_58.replace(" a"," ?a");
}
return _58.replace(/([a-z])\1*/ig,function(_59){
var s;
var c=_59.charAt(0);
var l=_59.length;
var p2="",p3="";
if(_57.strict){
if(l>1){
p2="0"+"{"+(l-1)+"}";
}
if(l>2){
p3="0"+"{"+(l-2)+"}";
}
}else{
p2="0?";
p3="0{0,2}";
}
switch(c){
case "y":
s="\\d{2,4}";
break;
case "M":
s=(l>2)?"\\S+":p2+"[1-9]|1[0-2]";
break;
case "D":
s=p2+"[1-9]|"+p3+"[1-9][0-9]|[12][0-9][0-9]|3[0-5][0-9]|36[0-6]";
break;
case "d":
s=p2+"[1-9]|[12]\\d|3[01]";
break;
case "w":
s=p2+"[1-9]|[1-4][0-9]|5[0-3]";
break;
case "E":
s="\\S+";
break;
case "h":
s=p2+"[1-9]|1[0-2]";
break;
case "k":
s=p2+"\\d|1[01]";
break;
case "H":
s=p2+"\\d|1\\d|2[0-3]";
break;
case "K":
s=p2+"[1-9]|1\\d|2[0-4]";
break;
case "m":
case "s":
s="[0-5]\\d";
break;
case "S":
s="\\d{"+l+"}";
break;
case "a":
var am=_57.am||_56.am||"AM";
var pm=_57.pm||_56.pm||"PM";
if(_57.strict){
s=am+"|"+pm;
}else{
s=am+"|"+pm;
if(am!=am.toLowerCase()){
s+="|"+am.toLowerCase();
}
if(pm!=pm.toLowerCase()){
s+="|"+pm.toLowerCase();
}
}
break;
default:
s=".*";
}
if(_55){
_55.push(_59);
}
return "("+s+")";
}).replace(/[\xa0 ]/g,"[\\s\\xa0]");
};
})();
(function(){
var _61=[];
dojo.date.locale.addCustomFormats=function(_62,_63){
_61.push({pkg:_62,name:_63});
};
dojo.date.locale._getGregorianBundle=function(_64){
var _65={};
dojo.forEach(_61,function(_66){
var _67=dojo.i18n.getLocalization(_66.pkg,_66.name,_64);
_65=dojo.mixin(_65,_67);
},this);
return _65;
};
})();
dojo.date.locale.addCustomFormats("dojo.cldr","gregorian");
dojo.date.locale.getNames=function(_68,_69,use,_6b){
var _6c;
var _6d=dojo.date.locale._getGregorianBundle(_6b);
var _6e=[_68,use,_69];
if(use=="standAlone"){
_6c=_6d[_6e.join("-")];
}
_6e[1]="format";
return (_6c||_6d[_6e.join("-")]).concat();
};
dojo.date.locale.isWeekend=function(_6f,_70){
var _71=dojo.cldr.supplemental.getWeekend(_70);
var day=(_6f||new Date()).getDay();
if(_71.end<_71.start){
_71.end+=7;
if(day<_71.start){
day+=7;
}
}
return day>=_71.start&&day<=_71.end;
};
dojo.date.locale._getDayOfYear=function(_73){
return dojo.date.difference(new Date(_73.getFullYear(),0,1),_73)+1;
};
dojo.date.locale._getWeekOfYear=function(_74,_75){
if(arguments.length==1){
_75=0;
}
var _76=new Date(_74.getFullYear(),0,1).getDay();
var adj=(_76-_75+7)%7;
var _78=Math.floor((dojo.date.locale._getDayOfYear(_74)+adj-1)/7);
if(_76==_75){
_78++;
}
return _78;
};
}

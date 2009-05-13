/*
	Copyright (c) 2004-2008, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/book/dojo-book-0-9/introduction/licensing
*/


if(!dojo._hasResource["dojo._base.html"]){
dojo._hasResource["dojo._base.html"]=true;
dojo.require("dojo._base.lang");
dojo.provide("dojo._base.html");
try{
document.execCommand("BackgroundImageCache",false,true);
}
catch(e){
}
if(dojo.isIE||dojo.isOpera){
dojo.byId=function(id,_2){
if(dojo.isString(id)){
var _d=_2||dojo.doc;
var te=_d.getElementById(id);
if(te&&te.attributes.id.value==id){
return te;
}else{
var _5=_d.all[id];
if(!_5||!_5.length){
return _5;
}
var i=0;
while((te=_5[i++])){
if(te.attributes.id.value==id){
return te;
}
}
}
}else{
return id;
}
};
}else{
dojo.byId=function(id,_8){
return dojo.isString(id)?(_8||dojo.doc).getElementById(id):id;
};
}
(function(){
var d=dojo;
var _a=null;
dojo.addOnUnload(function(){
_a=null;
});
dojo._destroyElement=function(_b){
_b=d.byId(_b);
try{
if(!_a){
_a=document.createElement("div");
}
_a.appendChild(_b.parentNode?_b.parentNode.removeChild(_b):_b);
_a.innerHTML="";
}
catch(e){
}
};
dojo.isDescendant=function(_c,_d){
try{
_c=d.byId(_c);
_d=d.byId(_d);
while(_c){
if(_c===_d){
return true;
}
_c=_c.parentNode;
}
}
catch(e){
}
return false;
};
dojo.setSelectable=function(_e,_f){
_e=d.byId(_e);
if(d.isMozilla){
_e.style.MozUserSelect=_f?"":"none";
}else{
if(d.isKhtml){
_e.style.KhtmlUserSelect=_f?"auto":"none";
}else{
if(d.isIE){
_e.unselectable=_f?"":"on";
d.query("*",_e).forEach(function(_10){
_10.unselectable=_f?"":"on";
});
}
}
}
};
var _11=function(_12,ref){
ref.parentNode.insertBefore(_12,ref);
return true;
};
var _14=function(_15,ref){
var pn=ref.parentNode;
if(ref==pn.lastChild){
pn.appendChild(_15);
}else{
return _11(_15,ref.nextSibling);
}
return true;
};
dojo.place=function(_18,_19,_1a){
if(!_18||!_19||_1a===undefined){
return false;
}
_18=d.byId(_18);
_19=d.byId(_19);
if(typeof _1a=="number"){
var cn=_19.childNodes;
if((_1a==0&&cn.length==0)||cn.length==_1a){
_19.appendChild(_18);
return true;
}
if(_1a==0){
return _11(_18,_19.firstChild);
}
return _14(_18,cn[_1a-1]);
}
switch(_1a.toLowerCase()){
case "before":
return _11(_18,_19);
case "after":
return _14(_18,_19);
case "first":
if(_19.firstChild){
return _11(_18,_19.firstChild);
}
default:
_19.appendChild(_18);
return true;
}
};
dojo.boxModel="content-box";
if(d.isIE){
var _1c=document.compatMode;
d.boxModel=_1c=="BackCompat"||_1c=="QuirksMode"||d.isIE<6?"border-box":"content-box";
}
var gcs,dv=document.defaultView;
if(d.isSafari){
gcs=function(_1f){
var s=dv.getComputedStyle(_1f,null);
if(!s&&_1f.style){
_1f.style.display="";
s=dv.getComputedStyle(_1f,null);
}
return s||{};
};
}else{
if(d.isIE){
gcs=function(_21){
return _21.currentStyle;
};
}else{
gcs=function(_22){
return dv.getComputedStyle(_22,null);
};
}
}
dojo.getComputedStyle=gcs;
if(!d.isIE){
dojo._toPixelValue=function(_23,_24){
return parseFloat(_24)||0;
};
}else{
dojo._toPixelValue=function(_25,_26){
if(!_26){
return 0;
}
if(_26=="medium"){
return 4;
}
if(_26.slice&&(_26.slice(-2)=="px")){
return parseFloat(_26);
}
with(_25){
var _27=style.left;
var _28=runtimeStyle.left;
runtimeStyle.left=currentStyle.left;
try{
style.left=_26;
_26=style.pixelLeft;
}
catch(e){
_26=0;
}
style.left=_27;
runtimeStyle.left=_28;
}
return _26;
};
}
var px=d._toPixelValue;
dojo._getOpacity=d.isIE?function(_2a){
try{
return _2a.filters.alpha.opacity/100;
}
catch(e){
return 1;
}
}:function(_2b){
return gcs(_2b).opacity;
};
dojo._setOpacity=d.isIE?function(_2c,_2d){
if(_2d==1){
var _2e=/FILTER:[^;]*;?/i;
_2c.style.cssText=_2c.style.cssText.replace(_2e,"");
if(_2c.nodeName.toLowerCase()=="tr"){
d.query("> td",_2c).forEach(function(i){
i.style.cssText=i.style.cssText.replace(_2e,"");
});
}
}else{
var o="Alpha(Opacity="+_2d*100+")";
_2c.style.filter=o;
}
if(_2c.nodeName.toLowerCase()=="tr"){
d.query("> td",_2c).forEach(function(i){
i.style.filter=o;
});
}
return _2d;
}:function(_32,_33){
return _32.style.opacity=_33;
};
var _34={left:true,top:true};
var _35=/margin|padding|width|height|max|min|offset/;
var _36=function(_37,_38,_39){
_38=_38.toLowerCase();
if(d.isIE&&_39=="auto"){
if(_38=="height"){
return _37.offsetHeight;
}
if(_38=="width"){
return _37.offsetWidth;
}
}
if(!(_38 in _34)){
_34[_38]=_35.test(_38);
}
return _34[_38]?px(_37,_39):_39;
};
var _3a=d.isIE?"styleFloat":"cssFloat";
var _3b={"cssFloat":_3a,"styleFloat":_3a,"float":_3a};
dojo.style=function(_3c,_3d,_3e){
var n=d.byId(_3c),_40=arguments.length,op=(_3d=="opacity");
_3d=_3b[_3d]||_3d;
if(_40==3){
return op?d._setOpacity(n,_3e):n.style[_3d]=_3e;
}
if(_40==2&&op){
return d._getOpacity(n);
}
var s=gcs(n);
if(_40==2&&!d.isString(_3d)){
for(var x in _3d){
d.style(_3c,x,_3d[x]);
}
return s;
}
return (_40==1)?s:_36(n,_3d,s[_3d]);
};
dojo._getPadExtents=function(n,_45){
var s=_45||gcs(n),l=px(n,s.paddingLeft),t=px(n,s.paddingTop);
return {l:l,t:t,w:l+px(n,s.paddingRight),h:t+px(n,s.paddingBottom)};
};
dojo._getBorderExtents=function(n,_4a){
var ne="none",s=_4a||gcs(n),bl=(s.borderLeftStyle!=ne?px(n,s.borderLeftWidth):0),bt=(s.borderTopStyle!=ne?px(n,s.borderTopWidth):0);
return {l:bl,t:bt,w:bl+(s.borderRightStyle!=ne?px(n,s.borderRightWidth):0),h:bt+(s.borderBottomStyle!=ne?px(n,s.borderBottomWidth):0)};
};
dojo._getPadBorderExtents=function(n,_50){
var s=_50||gcs(n),p=d._getPadExtents(n,s),b=d._getBorderExtents(n,s);
return {l:p.l+b.l,t:p.t+b.t,w:p.w+b.w,h:p.h+b.h};
};
dojo._getMarginExtents=function(n,_55){
var s=_55||gcs(n),l=px(n,s.marginLeft),t=px(n,s.marginTop),r=px(n,s.marginRight),b=px(n,s.marginBottom);
if(d.isSafari&&(s.position!="absolute")){
r=l;
}
return {l:l,t:t,w:l+r,h:t+b};
};
dojo._getMarginBox=function(_5b,_5c){
var s=_5c||gcs(_5b),me=d._getMarginExtents(_5b,s);
var l=_5b.offsetLeft-me.l,t=_5b.offsetTop-me.t;
if(d.isMoz){
var sl=parseFloat(s.left),st=parseFloat(s.top);
if(!isNaN(sl)&&!isNaN(st)){
l=sl,t=st;
}else{
var p=_5b.parentNode;
if(p&&p.style){
var pcs=gcs(p);
if(pcs.overflow!="visible"){
var be=d._getBorderExtents(p,pcs);
l+=be.l,t+=be.t;
}
}
}
}else{
if(d.isOpera){
var p=_5b.parentNode;
if(p){
var be=d._getBorderExtents(p);
l-=be.l,t-=be.t;
}
}
}
return {l:l,t:t,w:_5b.offsetWidth+me.w,h:_5b.offsetHeight+me.h};
};
dojo._getContentBox=function(_66,_67){
var s=_67||gcs(_66),pe=d._getPadExtents(_66,s),be=d._getBorderExtents(_66,s),w=_66.clientWidth,h;
if(!w){
w=_66.offsetWidth,h=_66.offsetHeight;
}else{
h=_66.clientHeight,be.w=be.h=0;
}
if(d.isOpera){
pe.l+=be.l;
pe.t+=be.t;
}
return {l:pe.l,t:pe.t,w:w-pe.w-be.w,h:h-pe.h-be.h};
};
dojo._getBorderBox=function(_6d,_6e){
var s=_6e||gcs(_6d),pe=d._getPadExtents(_6d,s),cb=d._getContentBox(_6d,s);
return {l:cb.l-pe.l,t:cb.t-pe.t,w:cb.w+pe.w,h:cb.h+pe.h};
};
dojo._setBox=function(_72,l,t,w,h,u){
u=u||"px";
var s=_72.style;
if(!isNaN(l)){
s.left=l+u;
}
if(!isNaN(t)){
s.top=t+u;
}
if(w>=0){
s.width=w+u;
}
if(h>=0){
s.height=h+u;
}
};
dojo._usesBorderBox=function(_79){
var n=_79.tagName;
return d.boxModel=="border-box"||n=="TABLE"||n=="BUTTON";
};
dojo._setContentSize=function(_7b,_7c,_7d,_7e){
if(d._usesBorderBox(_7b)){
var pb=d._getPadBorderExtents(_7b,_7e);
if(_7c>=0){
_7c+=pb.w;
}
if(_7d>=0){
_7d+=pb.h;
}
}
d._setBox(_7b,NaN,NaN,_7c,_7d);
};
dojo._setMarginBox=function(_80,_81,_82,_83,_84,_85){
var s=_85||gcs(_80);
var bb=d._usesBorderBox(_80),pb=bb?_89:d._getPadBorderExtents(_80,s),mb=d._getMarginExtents(_80,s);
if(_83>=0){
_83=Math.max(_83-pb.w-mb.w,0);
}
if(_84>=0){
_84=Math.max(_84-pb.h-mb.h,0);
}
d._setBox(_80,_81,_82,_83,_84);
};
var _89={l:0,t:0,w:0,h:0};
dojo.marginBox=function(_8b,box){
var n=d.byId(_8b),s=gcs(n),b=box;
return !b?d._getMarginBox(n,s):d._setMarginBox(n,b.l,b.t,b.w,b.h,s);
};
dojo.contentBox=function(_90,box){
var n=dojo.byId(_90),s=gcs(n),b=box;
return !b?d._getContentBox(n,s):d._setContentSize(n,b.w,b.h,s);
};
var _95=function(_96,_97){
if(!(_96=(_96||0).parentNode)){
return 0;
}
var val,_99=0,_b=d.body();
while(_96&&_96.style){
if(gcs(_96).position=="fixed"){
return 0;
}
val=_96[_97];
if(val){
_99+=val-0;
if(_96==_b){
break;
}
}
_96=_96.parentNode;
}
return _99;
};
dojo._docScroll=function(){
var _b=d.body(),_w=d.global,de=d.doc.documentElement;
return {y:(_w.pageYOffset||de.scrollTop||_b.scrollTop||0),x:(_w.pageXOffset||d._fixIeBiDiScrollLeft(de.scrollLeft)||_b.scrollLeft||0)};
};
dojo._isBodyLtr=function(){
return !("_bodyLtr" in d)?d._bodyLtr=gcs(d.body()).direction=="ltr":d._bodyLtr;
};
dojo._getIeDocumentElementOffset=function(){
var de=d.doc.documentElement;
return (d.isIE>=7)?{x:de.getBoundingClientRect().left,y:de.getBoundingClientRect().top}:{x:d._isBodyLtr()||window.parent==window?de.clientLeft:de.offsetWidth-de.clientWidth-de.clientLeft,y:de.clientTop};
};
dojo._fixIeBiDiScrollLeft=function(_9f){
var dd=d.doc;
if(d.isIE&&!dojo._isBodyLtr()){
var de=dd.compatMode=="BackCompat"?dd.body:dd.documentElement;
return _9f+de.clientWidth-de.scrollWidth;
}
return _9f;
};
dojo._abs=function(_a2,_a3){
var _a4=_a2.ownerDocument;
var ret={x:0,y:0};
var db=d.body();
if(d.isIE||(d.isFF>=3)){
var _a7=_a2.getBoundingClientRect();
var _a8=(d.isIE)?d._getIeDocumentElementOffset():{x:0,y:0};
ret.x=_a7.left-_a8.x;
ret.y=_a7.top-_a8.y;
}else{
if(_a4["getBoxObjectFor"]){
var bo=_a4.getBoxObjectFor(_a2),b=d._getBorderExtents(_a2);
ret.x=bo.x-b.l-_95(_a2,"scrollLeft");
ret.y=bo.y-b.t-_95(_a2,"scrollTop");
}else{
if(_a2["offsetParent"]){
var _ab;
if(d.isSafari&&(gcs(_a2).position=="absolute")&&(_a2.parentNode==db)){
_ab=db;
}else{
_ab=db.parentNode;
}
if(_a2.parentNode!=db){
var nd=_a2;
if(d.isOpera){
nd=db;
}
ret.x-=_95(nd,"scrollLeft");
ret.y-=_95(nd,"scrollTop");
}
var _ad=_a2;
do{
var n=_ad.offsetLeft;
if(!d.isOpera||n>0){
ret.x+=isNaN(n)?0:n;
}
var t=_ad.offsetTop;
ret.y+=isNaN(t)?0:t;
if(d.isSafari&&_ad!=_a2){
var cs=gcs(_ad);
ret.x+=px(_ad,cs.borderLeftWidth);
ret.y+=px(_ad,cs.borderTopWidth);
}
_ad=_ad.offsetParent;
}while((_ad!=_ab)&&_ad);
}else{
if(_a2.x&&_a2.y){
ret.x+=isNaN(_a2.x)?0:_a2.x;
ret.y+=isNaN(_a2.y)?0:_a2.y;
}
}
}
}
if(_a3){
var _b1=d._docScroll();
ret.y+=_b1.y;
ret.x+=_b1.x;
}
return ret;
};
dojo.coords=function(_b2,_b3){
var n=d.byId(_b2),s=gcs(n),mb=d._getMarginBox(n,s);
var abs=d._abs(n,_b3);
mb.x=abs.x;
mb.y=abs.y;
return mb;
};
var _b8=function(_b9){
switch(_b9.toLowerCase()){
case "tabindex":
return (d.isIE&&d.isIE<8)?"tabIndex":"tabindex";
default:
return _b9;
}
};
var _ba={colspan:"colSpan",enctype:"enctype",frameborder:"frameborder",method:"method",rowspan:"rowSpan",scrolling:"scrolling",shape:"shape",span:"span",type:"type",valuetype:"valueType"};
dojo.hasAttr=function(_bb,_bc){
var _bd=d.byId(_bb).getAttributeNode(_b8(_bc));
return _bd?_bd.specified:false;
};
var _be={};
var _bf=0;
var _c0=dojo._scopeName+"attrid";
dojo.attr=function(_c1,_c2,_c3){
var _c4=arguments.length;
if(_c4==2&&!d.isString(_c2)){
for(var x in _c2){
d.attr(_c1,x,_c2[x]);
}
return;
}
_c1=d.byId(_c1);
_c2=_b8(_c2);
if(_c4==3){
if(d.isFunction(_c3)){
var _c6=d.attr(_c1,_c0);
if(!_c6){
_c6=_bf++;
d.attr(_c1,_c0,_c6);
}
if(!_be[_c6]){
_be[_c6]={};
}
var h=_be[_c6][_c2];
if(h){
d.disconnect(h);
}else{
try{
delete _c1[_c2];
}
catch(e){
}
}
_be[_c6][_c2]=d.connect(_c1,_c2,_c3);
}else{
if(typeof _c3=="boolean"){
_c1[_c2]=_c3;
}else{
_c1.setAttribute(_c2,_c3);
}
}
return;
}else{
var _c8=_ba[_c2.toLowerCase()];
if(_c8){
return _c1[_c8];
}else{
var _c3=_c1[_c2];
return (typeof _c3=="boolean"||typeof _c3=="function")?_c3:(d.hasAttr(_c1,_c2)?_c1.getAttribute(_c2):null);
}
}
};
dojo.removeAttr=function(_c9,_ca){
d.byId(_c9).removeAttribute(_b8(_ca));
};
})();
dojo.hasClass=function(_cb,_cc){
return ((" "+dojo.byId(_cb).className+" ").indexOf(" "+_cc+" ")>=0);
};
dojo.addClass=function(_cd,_ce){
_cd=dojo.byId(_cd);
var cls=_cd.className;
if((" "+cls+" ").indexOf(" "+_ce+" ")<0){
_cd.className=cls+(cls?" ":"")+_ce;
}
};
dojo.removeClass=function(_d0,_d1){
_d0=dojo.byId(_d0);
var t=dojo.trim((" "+_d0.className+" ").replace(" "+_d1+" "," "));
if(_d0.className!=t){
_d0.className=t;
}
};
dojo.toggleClass=function(_d3,_d4,_d5){
if(_d5===undefined){
_d5=!dojo.hasClass(_d3,_d4);
}
dojo[_d5?"addClass":"removeClass"](_d3,_d4);
};
}

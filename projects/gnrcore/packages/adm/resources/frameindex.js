var loginManager = {
    notificationManager:function(notification_id){
        genro.setData('notification.confirm',null);
        var notification_data = genro.serverCall('_table.adm.user_notification.getNotification',{pkey:notification_id});
        var dlg = genro.dlg.quickDialog(notification_data['title'],{_showParent:true,max_width:'900px',datapath:'notification',background:'white'});
        var box = dlg.center._('div',{overflow:'auto',height:'500px',overflow:'auto',padding:'10px'});
        box._('div',{innerHTML:notification_data.notification,border:'1px solid transparent',padding:'10px'});
        var bar = dlg.bottom._('slotBar',{slots:'cancel,*,confirm_checkbox,2,confirm',height:'22px'});
        bar._('button','cancel',{'label':'Cancel',command:'cancel',action:function(){genro.logout();}});
        bar._('checkbox','confirm_checkbox',{value:'^.confirm',label:(notification_data.confirm_label || 'Confirm')})
        bar._('button','confirm',{'label':'Confirm',command:'confirm',disabled:'^.confirm?=!#v',action:function(){
                                                    genro.serverCall('_table.adm.user_notification.confirmNotification',{pkey:notification_id},
                                                            function(n_id){
                                                                dlg.close_action();
                                                                if(n_id){
                                                                    loginManager.notificationManager(n_id);
                                                                }else{
                                                                    genro.publish('end_notification')
                                                                }
                                                            }
                                                    )

                                                }});
        dlg.show_action();
    },

}


dojo.declare("gnr.FramedIndexManager", null, {
    constructor:function(stackSourceNode){
        genro.ping_classes = true;
        this.stackSourceNode = stackSourceNode;
        this.dbstore =  genro.getData('gnr.dbstore');
        this.default_uri =  genro.getData('gnr.defaultUrl')||'/';
        genro.externalWindowsObjects = {};
        var that = this;
        genro.childrenHasPendingChanges_replaced = genro.childrenHasPendingChanges;
        genro.childrenHasPendingChanges = function(){
            if(!genro.childrenHasPendingChanges_replaced()){
                for(var k in genro.externalWindowsObjects){
                    if(genro.externalWindowsObjects[k].genro.hasPendingChanges()){
                        return true
                    }
                }
            }else{
                return true;
            }
        };
        genro.onWindowUnload_replaced = genro.onWindowUnload;
        genro.onWindowUnload = function(){
            that.closeAllExternalWindows();
            genro.onWindowUnload_replaced();
        }
        this.stackSourceNode.registerSubscription('closeExternalWindow',function(kw){
            that.onExternalWindowClosed(kw.windowKey);
        });
        

    },
    
    createIframeRootPage:function(kw){
        this.finalizePageUrl(kw);
        var stackSourceNode = this.stackSourceNode;
        var rootPageName = kw.rootPageName;
        var stackWidget=this.stackSourceNode.widget;
        if(stackWidget.hasPageName(rootPageName)){
            this.iframesbag.getNode(rootPageName,null,true).updAttributes(this.iframeBagNodeAttr(kw));
            return rootPageName;
        }
        this.iframesbag = genro.getData('iframes');
        if(!this.iframesbag){
            this.iframesbag = new gnr.GnrBag();
            genro._data.setItem('iframes',this.iframesbag);
        }
        var multipageStack = this.makeMultiPageStack(stackSourceNode.getValue(),kw);
        var node = this.createIframePage(kw);
        multipageStack.setItem(node.label,node);
        let rootkw = this.iframeBagNodeAttr(kw);
        rootkw.selectedPage = node.attr.pageName;
        this.iframesbag.setItem(rootPageName,null,rootkw);
        return rootPageName;
    },

    iframeBagNodeAttr:function(kw){
        let startKw =  objectExtract(kw,'start_*');
        let openKw = kw.openKw || {};
        objectUpdate(openKw,startKw)
        return {fullname:kw.title || kw.label,
                pageName:kw.rootPageName,
                rootPageName:kw.rootPageName,
                fullpath:kw.fullpath,url:kw.url,
                subtab:kw.subtab,branchPage:kw.branchPage,
                openKw:openKw}
    },

    makeMultiPageStack:function(parentStack,kw){
        var root = genro.src.newRoot();
        var rootPageName = kw.rootPageName;
        var fp = root._('framePane',rootPageName,{frameCode:kw.name+'_#',pageName:rootPageName,title:kw.label});
        this.framePageTop(fp,kw);
        var sc = fp._('StackContainer',{side:'center',nodeId:rootPageName+'_multipage',selectedPage:'^iframes.'+rootPageName+'?selectedPage'}); 
        var frameNode = root.popNode('#0');
        parentStack.setItem(frameNode.label,frameNode._value,frameNode.attr);
        return sc;
    },

    createIframePage:function(kw){
        var label = kw.label;
        var that = this;
        var root = genro.src.newRoot();
        var rootPageName = kw.rootPageName;
        var url = kw.url;
        var iframePageName,pane_kw;
        var iframeattr = {'height':'100%','width':'100%','border':0,src:url,rootPageName:rootPageName};   
        if(genro.isMobile){
            iframeattr.width ='1px';
            iframeattr.min_width='100%';
            iframeattr.height ='1px';
            iframeattr.min_height='100%';
        }
        if(kw.externalSite){
            iframeattr.externalSite = kw.externalSite;
        }
        if(kw.subtab){
            iframePageName = rootPageName;
            pane_kw = {_lazyBuild:true,overflow:'hidden',title:kw.title,pageName:rootPageName};
            objectUpdate(iframeattr,{'id':'iframe_'+rootPageName,frameName:rootPageName});
        }else{
            iframePageName = 'm_'+genro.getCounter();
            var multipageIframePagePath = 'iframes.'+rootPageName+'.'+iframePageName;
            pane_kw = {_lazyBuild:true,overflow:'hidden',title:'^'+multipageIframePagePath+'.title',
                      pageName:iframePageName,closable:true,
                      stackbutton_tooltip:'^'+multipageIframePagePath+'.title?titleFullDesc'};
            genro.setData(multipageIframePagePath+'.title',label+'...');
            objectUpdate(iframeattr,{'id':'iframe_'+rootPageName+'_'+iframePageName,treeMenuPath:kw.fullpath,
                            frameName:rootPageName+'_'+iframePageName,multipage_childpath:multipageIframePagePath});
        }
        pane_kw.onClosingCb = function(evt){
            if(evt.shiftKey){
                return true;
            }
            var iframeSourceNode = this.getValue().getNode('iframecontainer.iframenode');
            return iframeSourceNode.domNode.contentWindow.genro.checkBeforeUnload();
        };

        var center = root._('ContentPane',iframePageName,pane_kw);
        var onStartCallbacks = objectPop(kw,'onStartCallbacks') || [];
        iframeattr.onStarted = function(){
            for (let cb of onStartCallbacks) {
                cb.call(this,this._genro);
            }
            that.checkStartsArgs(rootPageName)
        };

        var iframe = center._('div','iframecontainer',{'height':'100%','width':'100%',overflow:'hidden'})._('iframe','iframenode',iframeattr);
        return root.popNode('#0');
    },


    framePageTop:function(fp,kw){
        var bar = fp._('SlotBar',{slots:'multipageButtons,*',side:'top',toolbar:true,
                                        _class:'iframeroot_bar',
                                        closable:'close',closable_background:'white',
                                        closable_display:!kw.multipage?'none':null});
        var stackNodeId = kw.rootPageName+'_multipage';
        var sbuttons = bar._('StackButtons','multipageButtons',{stackNodeId:stackNodeId,margin_left:'4px'});
        var that = this;
        sbuttons._('div',{innerHTML:'<div class="multipage_add">&nbsp;</div>',_class:'multibutton',
                         connect_onclick:function(){
                            var sc = genro.nodeById(stackNodeId);
                            var node = that.createIframePage(kw);
                            var iframePageName = node.attr.pageName;
                            sc._value.setItem(node.label,node);
                            setTimeout(function(){sc.widget.switchPage(iframePageName);},100);
                         }
                     });
        //div('<div class="multipage_add">&nbsp;</div>',connect_onclick="""FIRE gnr.multipage.new = genro.dom.getEventModifiers($1);""",_class='multibutton')
    },

    checkStartsArgs:function(rootPageName){
        var iframeDataNode = this.iframesbag.getNode(rootPageName);
        let attr = iframeDataNode.attr
        let openKw = attr.openKw || {};
        var iframe = this.getCurrentIframe(rootPageName);
        if(openKw){
            openKw.topic = openKw.topic || 'changedStartArgs';
            iframe.gnr.postMessage(iframe.sourceNode,openKw);
        }
    },

    selectIframePage:function(kw){
        if(kw.newWindow){
            return this.newBrowserWindowPage(kw);
        }
        if(kw.newPanel){
            return this.newBrowserPanel(kw);
        }
        if(kw.redirect){
            return this.redirect(kw);
        }
        var rootPageName = this.createIframeRootPage(kw);
        var iframeDataNode = this.iframesbag.getNode(kw.rootPageName);
        var that = this;
        var cb = function(){
            that.addToPageHistory();
            that.stackSourceNode.setRelativeData('selectedFrame',rootPageName);
            if(that.getCurrentIframe(rootPageName)){
                that.checkStartsArgs(rootPageName);
            }
            that.stackSourceNode.fireEvent('refreshTablist',true);
        };
        var hasBeenSelected = iframeDataNode.attr.hasBeenCreated;
        if(!hasBeenSelected){
            genro.callAfter(function(){
                iframeDataNode.attr.hasBeenCreated = true;
            },1);
            genro.callAfter(cb,500,this,'creatingFramePage_'+iframeDataNode.label);
        }else{
            cb();
        }
    },

    onSelectedFrame:function(rootPageName){
        if(rootPageName=='indexpage'){
            return;
        }
        var that = this;
        this.stackSourceNode.watch('pageReady',function(){
            var iframe = that.getCurrentIframe(rootPageName);
            if(iframe && iframe.sourceNode.attr.externalSite){
                return true;
            }
            if(iframe && iframe.contentWindow && iframe.contentWindow.genro && iframe.contentWindow.genro._pageStarted){
                return true;
            }
        },function(){
             genro.publish({extWin:'DOCUMENTATION',topic:'onSelectedFrame'});
             setTimeout(function(){
                var iframe = that.getCurrentIframe(rootPageName);
                if (iframe.contentWindow.genro){
                    iframe.contentWindow.genro.resizeAll();
                }
            },1);
        })
        
    },
    newBrowserWindowPage:function(kw){
        this.finalizePageUrl(kw);
        if(kw.rootPageName in genro.externalWindowsObjects){
            genro.externalWindowsObjects[kw.rootPageName].focus();
            return;
        }
        var dn = this.stackSourceNode.widget.domNode;
        var externalWindowKw = {height:dn.clientHeight,width:dn.clientWidth,
                                left:window.screenLeft+dn.offsetLeft+20,top:window.screenTop+dn.offsetTop+(window.outerHeight-window.innerHeight)+20};
        objectUpdate(externalWindowKw,objectExtract(kw,'externalWindow_*'));
        var w = genro.openWindow(kw.url,kw.label,{location:externalWindowKw.location || 'no',menubar:externalWindowKw.menubar || 'no'});
        w.moveTo(externalWindowKw.left,externalWindowKw.top);
        w.resizeTo(externalWindowKw.width,externalWindowKw.height);
        var url = kw.url;
        var windowKey = kw.rootPageName;
        this.subscribeExternalWindow(w,windowKey);
        var b = this.externalWindowsBag();
        b.setItem(windowKey, null,{caption:kw.label,url:url,windowKey:windowKey});
        this.stackSourceNode.fireEvent('refreshTablist',true);
    },

    newBrowserPanel:function(kw){
        objectExtract(kw,'title,label')
        this.finalizePageUrl(kw);
        window.open(kw.url);
    },
    redirect:function(kw){
        objectExtract(kw,'title,label')
        this.finalizePageUrl(kw);
        genro.gotoURL(kw.url);
    },

    selectWindow:function(menuitem,ctxSourceNode,event){
        genro.externalWindowsObjects[menuitem.windowKey].focus()
    },


    subscribeExternalWindow:function(w,windowKey){
        genro.externalWindowsObjects[windowKey] = w;
        var parentGenro = genro;
        var parentWindow = window;
        w.addEventListener('load',function(){
            var wg = this.genro;       
            wg.externalParentWindow = parentWindow;
            wg.root_page_id = parentGenro.page_id;
            wg.parent_page_id = parentGenro.page_id;
            wg.startArgs['_root_page_id'] = wg.root_page_id;
            wg.startArgs['_parent_page_id'] = wg.parent_page_id;
            wg.external_window_key = windowKey;
        });
    },

    closeAllExternalWindows:function(){
        for(var k in genro.externalWindowsObjects){
            var closingWindow = genro.externalWindowsObjects[k];
            closingWindow.close();
        }
        if(!genro._windowClosing){
            this.stackSourceNode.fireEvent('refreshTablist',true);
        }
    },

    addToPageHistory:function(){
        let pageHistory = genro.getData('pageHistory') || []
        pageHistory.push(this.selectedFrame());
        genro.setData('pageHistory',pageHistory);
    },

    historyBack:function(){
        let pageHistory = genro.getData('pageHistory') || []
        let backToPage = pageHistory.pop();
        genro.setData('pageHistory',pageHistory.length?pageHistory:null);
        this.stackSourceNode.setRelativeData('selectedFrame',backToPage);
    },

    onExternalWindowClosed:function(windowKey){
        if(genro._windowClosing){
            return;
        }
        delete genro.externalWindowsObjects[windowKey];
        this.externalWindowsBag().popNode(windowKey);
        this.stackSourceNode.fireEvent('refreshTablist',true);
    },

    externalWindowsBag:function(){
        var b = genro.getData('externalWindows');
        if(!b){
            b = new gnr.GnrBag();
            genro.setData('externalWindows',b);
        }
        return b;
    },

    finalizePageUrl:function(kw){
        let urlPars = {};
        let urlkw = objectExtract(kw,'url_*',true);
        let baseurl = kw.webpage || kw.file || kw.filepath;
        if(this.dbstore && !kw.aux_instance && baseurl && baseurl.indexOf('/')===0){
            if(baseurl.slice(1).split('/')[0]!=this.dbstore){
                baseurl = `/${this.dbstore}${baseurl}`;
            }
        }
        if(kw.unique){
            urlPars.ts = new Date().getMilliseconds();
        }
        let title = kw.title || kw.label;
        if(title){
            urlPars.windowTitle = title;
        }
        urlPars = objectUpdate(urlPars,urlkw);
        kw.url = genro.addParamsToUrl(baseurl,urlPars);
        kw.rootPageName = kw.pageName || kw.url.replace(/\W/g,'_');
    },
    
    
    closeRootFramPage:function(frameName,title,evt){
        var that = this;
        var finalizeCb = function(){
            that.deleteFramePage(frameName);
        }
        if(evt.shiftKey){
            finalizeCb();
        }
        var iframes = dojo.query('iframe',this.stackSourceNode.getValue().getNode(frameName).getWidget().domNode);
        if(iframes.some(function(n){
            if(n.sourceNode.attr.externalSite){return false;}
            return n.contentWindow.genro.checkBeforeUnload();
        })){
            genro.dlg.ask(_T('Closing ')+title,_T("There is a pending operation in this tab"),{confirm:_T('Close anyway'),cancel:_T('Cancel')},
                            {confirm:function(){ finalizeCb();}})
        }else{
            finalizeCb();
        }
    },

    createTablist:function(sourceNode,data,onCreatingTablist){
        var root = genro.src.newRoot();
        var selectedFrame = this.selectedFrame();
        var button,kw,pageName;
        var deleteSelectedOnly = false;
        var that = this;
        var cb = function(n){
            pageName = n.attr.pageName;
            kw = {'_class':'iframetab',pageName:pageName};
            if (n.attr.subtab){
                kw['_class']+=' iframesubtab';
            }
            if(n.attr.hiddenPage){
                return;
            }
            if(pageName==selectedFrame){
                kw._class+=' iframetab_selected';
            }
            button = root._('div',pageName,kw);
            
            button._('div',{'innerHTML':n.attr.fullname || _T('Loading...'),'_class':'iframetab_caption',connectedMenu:'_menu_tab_opt_'});
            button._('div',{_class:'framecloser framecloserIcon',
                                    connect_onclick:function(e){
                                       dojo.stopEvent(e);
                                       that.closeRootFramPage(n.label,n.attr.fullname,e);
                                    }
                            })


        }
        if(data){
            data.forEach(cb,'static');
            if(onCreatingTablist){
                onCreatingTablist = funcCreate(onCreatingTablist,'root,selectedPage',this)
                onCreatingTablist(root,selectedFrame);
            }
        }
        if(this.externalWindowsBag().len()){
            var m = root._('div','externalPagesMenu',{_class:'iframetab windowmenu',connectedMenu:'_menu_open_windows_'})._('div',{innerHTML:'&nbsp;',_class:'iframetab_caption windowmenuIcon',
                                                                                            width:'18px'});
        }
        sourceNode.setValue(root, true);
    },
    

    selectedFrame:function(){
        return genro.getData('selectedFrame');
    },


    changeFrameLabel:function(kw){
        if(kw.pageName && this.iframesbag.getNode(kw.pageName)){
            this.iframesbag.getNode(kw.pageName).updAttributes({fullname:kw.title});
            this.stackSourceNode.fireEvent('refreshTablist',true);
        }
    },

    deleteFramePage:function(pageName){
        var sc = this.stackSourceNode.widget;
        var selected = sc.getSelectedIndex()-1;
        var iframesbag= genro.getData('iframes');
        var node = iframesbag.popNode(pageName);
        genro.publish({topic:'onDeletingIframePage',iframe:'iframe_'+pageName},pageName);
        if(node.attr.subtab=='recyclable'){
            node.updAttributes({'hiddenPage':true});
        }else{
            iframesbag.popNode(pageName);
            this.stackSourceNode.getValue().popNode(pageName);
            var treeItem = genro.getDataNode(node.attr.fullpath);
            if(treeItem){
                var itemclass = treeItem.attr.labelClass.replace('menu_existing_page','');
                itemclass = itemclass.replace('menu_current_page','');
                treeItem.setAttribute('labelClass',itemclass);
            }
        }
        if(this.stackSourceNode.getRelativeData('selectedFrame')==pageName){
            var curlen = iframesbag.len();
            curlen = this.externalWindowsBag().len()>0?curlen-1:curlen;
            selected = selected>=curlen? curlen-1:selected;
            var nextPageName = 'indexpage';
            let pageHistory = genro.getData('pageHistory') || [];
            if(pageHistory){
                pageHistory.pop()
            }
            if(pageHistory.length){
                nextPageName = pageHistory.pop()
            }
            else if(selected>=0){
                nextPageName = iframesbag.getNode('#'+selected)? iframesbag.getNode('#'+selected).attr.pageName:'indexpage';
            }
            this.stackSourceNode.setRelativeData('selectedFrame',nextPageName); //PUT
        }
  
        this.stackSourceNode.fireEvent('refreshTablist',true);

    },

    reloadSelectedIframe:function(rootPageName,modifiers){
        var iframe = this.getCurrentIframe(rootPageName);
        if(iframe){
            var finalizeCb = function(){
                iframe.sourceNode.reloadIframe();
            }
            if(iframe.sourceNode._genro && iframe.sourceNode._genro.checkBeforeUnload()){
                genro.dlg.ask(_T('Reloading current frame'),_T("There is a pending operation in this tab"),{confirm:_T('Close anyway'),cancel:_T('Cancel')},
                            {confirm:function(){ 
                                iframe.sourceNode._genro._checkedUnload = true;
                                finalizeCb();
                            }});
            }else{
                finalizeCb();
            }
        }
    },
    openUserPreferences:function(){
        genro.selectIframePage({webpage:'/adm/user_preference'});
    },

    openAppPreferences:function(){
        genro.selectIframePage({webpage:'/adm/app_preference'});
    },

    openHelpForCurrentIframe:function(){
        var iframe = this.getCurrentIframe(this.stackSourceNode.getRelativeData('selectedFrame'));
        if(!iframe){
            genro.dev.openHelpDesk(true);
        }else if(iframe.sourceNode && iframe.sourceNode._genro){
            iframe.sourceNode._genro.dev.openHelpDesk();
        }else{
            genro.dev.openHelpDesk(true);
        }
        
    },


    openGnrIDE:function(){
        this.newBrowserWindowPage({
            pageName:'GNRIDE',
            file:'/sys/gnride',
            label: _T("Genro IDE")
        });
    },

    callOnCurrentIframe:function(objpath,method,args){
        var rootPageName = this.stackSourceNode.getRelativeData('selectedFrame');
        var selectedIframe =  rootPageName && rootPageName!='indexpage'?this.getCurrentIframe(rootPageName):null; //documentazione della index da vedere poi
        if(!selectedIframe){
            //da verificare
            return;
        }
        var result = {};
        var cw = selectedIframe.contentWindow;
        var scope = cw.genro;
        var l = objpath?objpath.split('.'):[];
        l.forEach(function(chunk){
            scope = scope[chunk];
        });
        if(scope){
            return scope[method].apply(scope,args);
        }
    },

    getCurrentIframe:function(rootPageName){
        var iframesbag= genro.getData('iframes');
        if(!iframesbag){
            return;
        }
        var iframePageId = iframesbag.getItem(rootPageName+'?selectedPage');
        var iframeId = iframePageId;
        if(rootPageName!=iframePageId){
            iframeId = rootPageName+'_'+iframePageId;
        }
        return dojo.byId("iframe_"+iframeId);
    },


    menuAction:function(menuitem,ctxSourceNode,event){
        var action = menuitem.code;
        var pageattr = ctxSourceNode.getParentNode().attr;
        var title = ctxSourceNode.attr.innerHTML;
        var fullpath = this.iframesbag.getNode(pageattr.pageName).attr['fullpath'];
        if(action =='detach'){
            this.detachPage(pageattr,title,event);
        }else if(action=='remove'){
            this.removeFromFavorite(fullpath);
        }
        else if(action=='clearfav'){
            this.removeFromFavorite(true);
        }else if(action=='reload'){
            this.reloadSelectedIframe(pageattr.pageName);
        }
        else{
            if(fullpath){
                this.addToFavorite(fullpath,action=='start');
            }
        }
    },
    removeFromFavorite:function(fullpath){
        var favorite_pages = genro.userPreference('adm.index.favorite_pages') || new gnr.GnrBag();
        if(fullpath==true){
            favorite_pages = null;
        }else{
            var l = fullpath.replace(/\W/g,'_');
            favorite_pages.popNode(l);      
        }
        genro.setUserPreference('index.favorite_pages',favorite_pages,'adm')
    },

    addToFavorite:function(fullpath,start){
        var favorite_pages = genro.userPreference('adm.index.favorite_pages') || new gnr.GnrBag();
        var l = fullpath.replace(/\W/g,'_');
        if(favorite_pages.len() && start){
            favorite_pages.forEach(function(n){
                n._value.setItem('start',false);
            },'static')
        }else{
            start=true;
        }
        favorite_pages.setItem(l,new gnr.GnrBag({pagepath:fullpath,start:start}));
        genro.setUserPreference('index.favorite_pages',favorite_pages,'adm')
    },

    loadFavorites:function(cb){
        var favorite_pages = genro.userPreference('adm.index.favorite_pages');
        if(favorite_pages){
            var that = this;
            var v;
            var startPage;
            var kw,inattr;
            var pageName;
            var treenode;
            if(favorite_pages){
                favorite_pages.forEach(function(n){
                    v = n.getValue();
                    treenode = genro.getDataNode(v.getItem('pagepath'))
                    if(!treenode){
                        return;
                    }
                    kw = treenode.attr;

                    var labelClass= treenode.attr.labelClass;
                    if(labelClass.indexOf('menu_existing_page')<0 && !treenode.attr.branchPage){
                        treenode.setAttribute('labelClass',labelClass+' menu_existing_page');
                    }                
                    inattr = treenode.getInheritedAttributes();    
                    kw = objectUpdate({name:treenode.label,pkg_menu:inattr.pkg_menu,"file":null,
                                        table:null,formResource:null,viewResource:null,
                                        fullpath:v.getItem('pagepath'),modifiers:null},
                                        treenode.attr)
                    pageName = that.createIframeRootPage(kw);
                    if(v.getItem('start')){
                        startPage = pageName;
                    }
                },'static');
            }
            setTimeout(function(){
                that.stackSourceNode.setRelativeData('selectedFrame',startPage || pageName);
                that.stackSourceNode.fireEvent('refreshTablist',true);
            },100);
        }
    },
    handleExternalMenuCode:function(external_menucode,runKwargs){
        runKwargs = runKwargs || {}
        let menubag = genro.getData('gnr.appmenu.root');
        let n = menubag.getNodeByAttr('menucode',external_menucode);
        inattr = n.getInheritedAttributes()
        let kw = {name:n.label,pkg_menu:inattr.pkg_menu,"file":null,table:null,formResource:null,
                                viewResource:null,fullpath:n.getFullpath(null,true),modifiers:null,
                    ...n.attr,...objectExtract(runKwargs,'url_*',null,true)};
        kw.openKw = kw.openKw || {};
        objectUpdate(kw.openKw,runKwargs);
        objectUpdate(kw.openKw,{topic:'frameindex_external'});
        genro.publish('selectIframePage',kw);
    },

    detachPage:function(attr,title,evt){
        var that = this;
        var iframenode = this.stackSourceNode._value.getItem(attr.pageName).getNode('#0');
        var iframedomnode = iframenode.domNode;
        var paletteCode = attr.pageName;
        var kw = {height:_px(iframedomnode.clientHeight),width:_px(iframedomnode.clientWidth),maxable:true,evt:evt,
                title:title,palette__class:'detachPalette',dockTo:false};
        kw.palette_connect_close = function(){
            that.stackSourceNode._value.getNode(attr.pageName).widget.domNode.appendChild(iframedomnode);
        }
        var paletteNode = genro.dlg.quickPalette(paletteCode,kw);
        var newparentNode = paletteNode.getValue().getNode('#0.#0.#0').widget.domNode;
        newparentNode.appendChild(iframedomnode);
    }
});

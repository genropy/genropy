var AttachManager = {
    onDropFiles:function(sourceNode,files,onResult){
        var uploadKw =  objectExtract(sourceNode.attr,'_uploader_*',true)
        uploadKw = sourceNode.evaluateOnNode(uploadKw);
        var params = {attachment_table:sourceNode.getInheritedAttributes()['table'],maintable_id:uploadKw.fkey,
                      onUploadingMethod:uploadKw['onUploadingMethod'],
                      onUploadedMethod:uploadKw['onUploadedMethod']};
        var kw = {uploaderId:sourceNode.attr.nodeId || 'attachmentManager',
                  onProgress:function(e){console.log('onProgress',e)},
                  onResult:function(e){console.log('onResult',e)}
                }
        if(onResult){
            kw.onResult = funcCreate(onResult,'event',sourceNode);
        }
        var sendKw,sendParams;
        dojo.forEach(files,function(file){
            sendKw = objectUpdate({filename:file.name},kw);
            sendParams = objectUpdate({mimetype:file.type},params);
            genro.rpc.uploadMultipart_oneFile(file, sendParams, sendKw);
        });
    }
};
AttachManager.zoomSteps = [0.25,0.5,0.75,1,1.5,2,3];

AttachManager.zoomStep = function(sourceNode,direction){
    var zoom = sourceNode.getRelativeData('#FORM.currentPreviewZoom') || 0;
    var steps = AttachManager.zoomSteps;
    if(direction>0){
        zoom = zoom? (steps.find(s=>s>zoom) || zoom) : 1;
    }else if(direction<0){
        zoom = zoom? ([...steps].reverse().find(s=>s<zoom) || zoom) : 0.5;
    }else{
        zoom = 0;
    }
    sourceNode.setRelativeData('#FORM.currentPreviewZoom',zoom);
    sourceNode.setRelativeData('#FORM.chips.zoomLabel',zoom? Math.round(zoom*100)+'%' : _T('Fit'));
};

AttachManager.chipsLoaded = function(formId){
    AttachManager.openChipsForm = formId;
    if(AttachManager._chipsKeyHandler){
        return;
    }
    var commands = {ArrowLeft:'prev',ArrowRight:'next',Escape:'dismiss'};
    AttachManager._chipsKeyHandler = dojo.connect(document,'onkeydown',function(e){
        var openFormId = AttachManager.openChipsForm;
        var tag = e.target && e.target.tagName;
        var command = commands[e.key];
        if(!openFormId || !command || tag=='INPUT' || tag=='TEXTAREA'){
            return;
        }
        dojo.stopEvent(e);
        genro.formById(openFormId).publish('navigationEvent',{command:command});
    });
};

AttachManager.chipsDismissed = function(chipsNode,formId){
    if(AttachManager.openChipsForm==formId){
        AttachManager.openChipsForm = null;
    }
    chipsNode.fireEvent('.reload',true);
};

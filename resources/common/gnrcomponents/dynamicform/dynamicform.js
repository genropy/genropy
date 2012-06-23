var dynamicFormHandler = {
    onDataTypeChange:function(sourceNode,data_type,reason,newrecord){
        var allowedWidget,allowedFormat,defaults;
        if(data_type=='T'){
            allowedWidget = 'textbox:TextBox,simpletextarea:TextArea,filteringselect:Filtering Select,combobox:ComboBox,dbselect:DbSelect,checkboxtext_nopopup:Checkboxtext,checkboxtext:Popup Checkboxtext,geocoderfield:GeoCoderField';
            allowedFormat = '';
            defaults = {wdg_tag:'textbox',format:''};
        }else if(data_type=='L'){
            allowedWidget = 'numbertextbox:NumberTextBox,numberspinner:NumberSpinner,horizontalslider:Slider,filteringselect:Filtering Select,combobox:Combobox';
            allowedFormat = '###0\n0000';
            defaults = {wdg_tag:'numbertextbox',format:''};
        }else if(data_type=='N'){
            allowedWidget = 'numbertextbox:NumberTextBox,currencytextbox:CurrencyTextBox,numberspinner:NumberSpinner,horizontalslider:Slider,filteringselect:Filtering Select,combobox:Combobox';
            allowedFormat = '###0\n0000.000';
            defaults = {wdg_tag:'numbertextbox',format:''};
        }else if(data_type=='D'){
            allowedWidget = 'datetextbox:Popup,datetextbox_nopopup:Plain';
            allowedFormat = 'short,medium,long';
            defaults = {wdg_tag:'datetextbox',format:'short'};

        }else if(data_type=='H'){
            allowedWidget = 'timetextbox:Calendar Popup,timetextbox_nopopup:Date field';
            allowedFormat = 'short,medium,long';
            defaults = {wdg_tag:'timetextbox',format:'short'};
        }else if(data_type=='B'){
            allowedWidget = 'checkbox:CheckBox,filteringselect:FilteringSelect';
            allowedFormat = 'Yes,No\nTrue,False';
            defaults = {wdg_tag:'checkbox',format:'Yes,No'};

        }else if(data_type='P'){
            allowedWidget = 'img:Image';
            allowedFormat = ''
            defaults = {wdg_tag:'img',format:'auto'};
        }
        sourceNode.setRelativeData('#FORM.allowedWidget',allowedWidget);
        sourceNode.setRelativeData('#FORM.allowedFormat',allowedFormat);
        if(reason!='container' || newrecord){
            for (var k in defaults){
                sourceNode.setRelativeData('#FORM.record.'+k,defaults[k]);
            }
        }
    },
    onSetWdgTag:function(sourceNode,wdg_tag){
        var calculated = sourceNode.getRelativeData('.calculated');
        if(!calculated){
            sourceNode.setRelativeData('#FORM.boxClass','dffb_enterable dffb_'+wdg_tag);
        }else{
            sourceNode.setRelativeData('#FORM.boxClass','dffb_calculated');
        }
    },
    
    onSetCalculated:function(sourceNode,calculated){
        var wdg_tag,boxClass;
        boxClass = 'dffb_enterable';
        if(calculated){
            boxClass = 'dffb_calculated';
            sourceNode.setRelativeData('.wdg_tag',null);
        }else{
                //formclass = 'dffb_'+data_type;
        }
        sourceNode.setRelativeData('#FORM.boxClass',boxClass);
    }
};
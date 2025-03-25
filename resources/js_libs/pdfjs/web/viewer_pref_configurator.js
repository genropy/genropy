
function parseURL(url) {
    var a =  document.createElement('a');
    a.href = url;
    return {
        source: url,
        protocol: a.protocol.replace(':',''),
        host: a.hostname,
        port: a.port,
        query: a.search,
        origin:a.origin,
        pathname:a.pathname,
        params: (function(){
            var ret = {},
                seg = a.search.replace(/^\?/,'').split('&'),
                len = seg.length, i = 0, s;
            for (;i<len;i++) {
                if (!seg[i]) { continue; }
                s = seg[i].split('=');
                ret[s[0]] = s[1];
            }
            return ret;
        })(),
        file: (a.pathname.match(/\/([^\/?#]+)$/i) || [,''])[1],
        hash: a.hash.replace('#',''),
        path: a.pathname.replace(/^([^\/])/,'/$1'),
        relative: (a.href.match(/tps?:\/\/[^\/]+(.+)/) || [,''])[1],
        segments: a.pathname.replace(/^\//,'').split('/')
    };
}

function configureViewer() {
    let parsedUrl = parseURL(document.location.href);
    let _viewer_options = parsedUrl.params._viewer_options;
    let _viewer_tools = parsedUrl.params._viewer_tools;
    let _is_cordova = parsedUrl.params._is_cordova;
    let _external_document_url = parsedUrl.params._external_document_url;

    if(_is_cordova && _external_document_url){
        const app = window.PDFViewerApplication;
        _viewer_options = _viewer_options.split(',').filter(elem=>elem!='print').join(',');
        document.body.classList.add('cordova_external_url');
        app.download = function(){
            window.open(_external_document_url+'/'+this._downloadUrl);
        };
    }

    if(_viewer_options){
        for(let opt of _viewer_options.split(',')){
            document.body.classList.add(opt+'_enabled');
        }
    }
    if(_viewer_tools){
        for(let opt of _viewer_tools.split(',')){
            document.body.classList.add(opt+'_enabled');
        }
    }

};



document.blockUnblockOnload?.(true);

if (document.readyState === "interactive" || document.readyState === "complete") {
  configureViewer();
} else {
  document.addEventListener("DOMContentLoaded", configureViewer, true);
}
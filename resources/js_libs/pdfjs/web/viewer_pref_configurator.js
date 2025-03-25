
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

function patchViewer(){
    console.log('PDFViewerApplication',PDFViewerApplication);
    PDFViewerApplication.download = function() {
        console.log('patch download')
        const url = this._downloadUrl;
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // lasciando vuoto forza il comportamento di download in alcuni browser
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
}

document.blockUnblockOnload?.(true);

if (document.readyState === "interactive" || document.readyState === "complete") {
  configureViewer();
  patchViewer();
} else {
  document.addEventListener("DOMContentLoaded", configureViewer, true);
}
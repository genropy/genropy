<!-- ================  Genropy Headers ================ -->
<script type="text/javascript" src="${dojolib}" djConfig="${djConfig}"> </script>
<script type="text/javascript">dojo.registerModulePath('gnr','${gnrModulePath}');</script>
% if pwa:
    <link rel="manifest" crossorigin="use-credentials" href="/_pwa_manifest.json">
    <script type="text/javascript" src="/_rsrc/common/pwa/app.js"></script>
% endif

% if sentryjs:
    <script type="text/javascript">
    window.sentryOnLoad = function() {
	console.log("GENROPY SENTRY SUPPORT INIT");
	Sentry.init({
	    sampleRate: ${sentry_sample_rate},
	    traceSampleRate: ${sentry_traces_sample_rate},
	    profilesSampleRate: ${sentry_profiles_sample_rate},
	    replaysSessionSampleRate: ${sentry_replays_session_sample_rate},
	    replaysOnErrorSampleRate: ${sentry_replays_on_error_sample_rate},
	    
	});
	// using an event processo to retrieve and
	// add extra data when sending, due to genro client
	// not immediately available when the page is loading
	
	Sentry.addEventProcessor(event => {
	    try {
		event.tags = {
		    gnr_package: genro.getData('gnr.package'),
		    genropy_instance: genro.getData('gnr.siteName'),
		    genro_loaded: true,
		    gnr_table: genro.getData('gnr.table'),
		    gnr_pagename: genro.getData('gnr.pagename'),
		    gnr_page_id: genro.getData('gnr.page_id')
		}
		Sentry.setUser({"username": genro.getData('gnr.avatar.user')});
	    } catch (error) {
		Sentry.setTag("genro_loaded", false);
	    }
	    return event;
	});
    }
    </script>
    <script src="${sentryjs}" crossorigin="anonymous"></script>

% endif

% if favicon:
     <link rel="icon" href="${favicon}" />
     <link rel="apple-touch-icon" href="${favicon}" />
% endif
% if google_fonts:
    <link href='http://fonts.googleapis.com/css?family=${google_fonts}' rel='stylesheet' type='text/css'>
% endif

% if dijitImport:
    % for single in dijitImport:
        <script type="text/javascript" src="${single}"></script>
    % endfor
% endif

% for jsname in genroJsImport:
    <script type="text/javascript" src="${jsname}"></script>
% endfor

% for customHeader in customHeaders:
    ${customHeader}
% endfor

% for jsname in js_requires:
        <script type="text/javascript" src="${jsname}"></script>
% endfor
        % if logo_url:
            <style type="text/css">
                :root {
                    --client-logo: transparent url(${logo_url}) no-repeat center center;;
                }
            </style>
        % endif
        <style type="text/css">
            % for cssname in css_dojo:
            @import url("${cssname}");  
            % endfor
        </style>
            
        % for cssmedia, cssnames  in css_genro.items():
        <style type="text/css" media="${cssmedia}">
                % for cssname in cssnames:
            @import url("${cssname}");
                % endfor
        </style>
        % endfor
        <style type="text/css">    
            % for cssname in css_requires:
            @import url("${cssname}");
            % endfor
        </style>
        
        % for cssmedia, cssnames  in css_media_requires.items():
        <style type="text/css" media="${cssmedia}">
                % for cssname in cssnames:
            @import url("${cssname}");
                % endfor
        </style>
        % endfor
        
        <script type="text/javascript">
            var genro = new gnr.GenroClient({ page_id:'${page_id}',baseUrl:'${filename}', pageMode: '${pageMode or "legacy"}',
                                              pageModule:'${pageModule}',
                                              domRootName:'mainWindow', startArgs: ${startArgs}, baseUrl:'${baseUrl or "/"}'});
        </script>

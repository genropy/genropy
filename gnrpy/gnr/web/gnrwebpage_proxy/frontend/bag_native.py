"""Assets for custom HTML pages consuming the standalone Bag API."""
from gnr.web.gnrjsassets import bag_javascript_files
from gnr.web.gnrwebpage_proxy.frontend.gnrbasefrontend import GnrBaseFrontend


class GnrWebFrontend(GnrBaseFrontend):
    theme = ''

    def init(self, **kwargs):
        if self.page.pagetemplate == 'standard.tpl':
            raise ValueError('bag_native requires a custom HTML template; '
                             'the standard template starts GenroClient')

    def frontend_arg_dict(self, arg_dict):
        pass

    def gnrjs_frontend(self):
        return bag_javascript_files(self.page)

    def css_genro_frontend(self):
        return {}

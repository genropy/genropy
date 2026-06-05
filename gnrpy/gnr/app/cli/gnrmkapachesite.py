#!/usr/bin/env python
# encoding: utf-8
import os
import grp

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrconfig import getGnrConfig
from gnr.app.pathresolver import PathResolver


def build_apache_site(site_name, apache_path='/etc/apache2/sites-available/', 
                    process_name=None, user=None, filename=None,
                      group=None, tmp_path='/tmp', threads=4,
                      admin_mail=None, port=80, domain=None,
                      processes=8, maximum_requests=700, base_url='/', apache24=False):
    gnr_config = getGnrConfig(set_environment=True)
    path_resolver = PathResolver(gnr_config=gnr_config)
    site_path = path_resolver.site_name_to_path(site_name)
    if os.path.exists(os.path.join(site_path,'root.wsgi')):
        script_name = 'root.wsgi'
    else:
        script_name = 'root.py'
    if apache24:
        permissions = """Require all granted"""
    else:
        permissions = """Order allow,deny
                Allow from all"""
    params = dict(process_name=process_name or 'gnr_%s' % site_name,
                  domain=domain,
                  user=user,
                  group=group,
                  tmp_path=tmp_path or '/tmp',
                  threads=str(threads), # Transform threads, maximum_requests and processes to str to accept both int and str as args
                  maximum_requests=str(maximum_requests),
                  processes=str(processes),
                  base_url=base_url,
                  admin_mail=admin_mail or f'genro@{domain}',
                  site_path=site_path,
                  script_name=script_name,
                  port=str(port),
                  permissions = permissions
                  )
    params['process_env'] = 'ENV_{}'.format(params['process_name'].upper())

    apache_file_content = """<VirtualHost *:80>
            ServerName %(domain)s
            ServerAdmin %(admin_mail)s
            DocumentRoot /var/www
            WSGIDaemonProcess %(process_name)s user=%(user)s group=%(group)s python-eggs=%(tmp_path)s threads=%(threads)s processes=%(processes)s maximum-requests=%(maximum_requests)s
            SetEnv %(process_env)s %(process_name)s
            WSGIProcessGroup %%{ENV:%(process_env)s}
            # modify the following line to point your site
            WSGIScriptAlias %(base_url)s %(site_path)s/%(script_name)s
            <Directory %(site_path)s>
                Options Indexes FollowSymLinks
                AllowOverride All
                %(permissions)s
            </Directory>
            ErrorLog %(site_path)s/error.log
    </VirtualHost>
    """ % params
    print(apache_file_content)

description = "generate apache configuration file"
def main():
    epilog = """
    gnr app mkapachesite <site_name> <domain_name> will output an apache site configuration file.
    example usage:
    gnr app mkapachesite genro www.genro.org > genro_site.conf
    will write the correct apache configuration for 'genro' site in genro_site
    then copy genro_site.conf to /etc/apache2/sites-available:
    sudo cp genro_site.conf /etc/apache2/sites-available
    then enable it:
    sudo a2ensite genro_site
    (with apache < 2.4  sudo a2ensite genro_site.conf)
    and finally restart apache:
    sudo apache2ctl restart
    """
    current_user = os.getlogin()
    gid = os.getgid()
    current_group = grp.getgrgid(gid)[0]
    
    parser = GnrCliArgParse(description=description, epilog=epilog)
    parser.add_argument("-u", "--user", dest="user",default=current_user,
                       help="user for wsgi process execution")
    parser.add_argument("-g", "--group", dest="group",default=current_group,
                  help="group for wsgi process execution")
    parser.add_argument("-P", "--port", dest="port", default=80,
                  help="port for virtualserver")
    parser.add_argument("-a", "--apache", dest="apache", default='/etc/apache2/sites-available/',
                  help="port for virtualserver")
    parser.add_argument("-p", "--processes", dest="processes", default=8,
                  help="max processes")
    parser.add_argument("-t", "--threads", dest="threads", default=4,
                        help="max threads")
    parser.add_argument("-r", "--maximum_requests", dest="maximum_requests", default=700,
                        help="max requests per process")
    parser.add_argument("-4", "--apache24", dest="apache24", action='store_true', default=False,
                      help="makes the configuration file compatible with apache 2.4 (remember the .conf at the end of filename!)")
    parser.add_argument("site_name")
    parser.add_argument("domain_name", nargs="?")
    options = parser.parse_args()
    build_apache_site(options.site_name,
                      domain=options.domain_name,
                      user=options.user,
                      group=options.group,
                      threads=options.threads,
                      processes=options.processes,
                      maximum_requests=options.maximum_requests,
                      port=options.port,
                      apache24=options.apache24)
        

if __name__ == '__main__':
    main()

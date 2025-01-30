#!/usr/bin/env python
# encoding: utf-8
import os

from gnr.core.cli import GnrCliArgParse
from gnr.xtnd.sync4Dapp_new import GnrAppSync4D


description = "sync genropy instances with 4d genro xml sync files"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-v', '--verbose',
                      dest='verbose',
                      action='store_true',
                      help="Verbose mode")

    # this is for compatibility with the old script,
    # to collect old positional arguments
    parser.add_argument('args',
                        action='append',
                        nargs="*")

    parser.add_argument('-instance',
                      help="Use command on instance")
    
    parser.add_argument('-D', '--directory',
                      dest='directory',
                      help="Use command on instance identified by supplied directory (overrides -i)")
    
    parser.add_argument('-r', '--rebuild',
                      dest='rebuild',
                      action='store_true',
                      help="Rebuild config_db.xml")
    
    parser.add_argument('-4', '--4dir',
                      dest='sync4d_name',
                      help="specifies a sync4d folder name")
    
    options = parser.parse_args()
    args = options.args[0]
    
    debug = options.debug==True
    app_kwargs=dict(debug=debug)
    if args:
        instance_path=args[0]
    else:
        instance_path=os.getcwd()

    if len(args)>1:
        app_kwargs['sync4d_name']=args[1]
        args=(args[0],)
        
    app_kwargs['sync4d_name'] = options.sync4d_name or app_kwargs.get('sync4d_name','sync4d')
    
    if options.rebuild:
        app_kwargs['rebuild'] = True
    app = GnrAppSync4D(*args, **app_kwargs)
    if options.rebuild:
        app.rebuildRecipe(modelOnly=True)
    else:
        app.loop()
    
if __name__=='__main__':
    main()

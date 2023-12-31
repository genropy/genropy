# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrsys : a connection to the os.
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import sys

def progress(count, total, status='', fd=sys.stdout):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    fd.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    fd.flush() 


def mkdir(path, privileges=0o777):
    """Create a directory named *path* with numeric mode *privileges*.
    
    :param path: the name of the directory
    :param privileges: the current umask value is first masked out.
                       Default value is ``0777`` (octal)"""
    if path and not os.path.isdir(path):
        head, tail = os.path.split(path)

        mkdir(head, privileges)
        # on some systems, privileges are ignored, needs explicit call
        os.chmod(head, privileges)
        
        os.mkdir(path, privileges)
        # on some systems, privileges are ignored, needs explicit call
        os.chmod(path, privileges)
        
def expandpath(path, full=False):
    """Expand user home directory (~) and environment variables. Return the
    expanded path
    
    :param path: the path to expand"""
    path = os.path.expanduser(os.path.expandvars(path))
    if full:
        path = os.path.realpath(os.path.normpath(path))
    return path
    
def listdirs(path, invisible_files=False):
    """Return a list of all the files contained in a path and its descendant
    
    :param path: the path you want to analyze
    :param invisible_files: boolean. If ``True``, add invisible files to the returned list"""
    
    def callb(files, top, names):
        for name in names:
            file_path = os.path.realpath(os.path.join(top, name))
            if (invisible_files or not name.startswith('.')) and os.path.isfile(file_path):
                files.append(file_path)
                
    files = []
    os.walk(path, callb, files)
    return files

def resolvegenropypath(path):
    """added by Jeff.
       
       Relative path may be more appropriate in most cases, but in some cases it may be
       useful to have this construction.
       
       To make it easier to resolve document paths between different installations
       of genropy where sometimes it is installed in the user path and sometimes
       at root (i.e. /genropy/... or ~/genropy/.), so that file path given within
       Genropy will be resolved to be valid if possible and we do not have to edit
       for example our import files. Of course I expect it to be rejected and/or refactored"""
       
    if path.find('~') == 0:
        path = expandpath(path)
        if os.path.exists(path):
            return path
            
    if path.find('/') == 0:
        if os.path.exists(path):
            return path
        else: #try making it into a user directory path
            path = '%s%s' % ('~', path)
            path = expandpath(path)
            if os.path.exists(path):
                return path
    else:
        if os.path.exists(path):
            return path
        else:
            path = '%s%s' % ('~/', path)
            path = expandpath(path)
            if os.path.exists(path):
                return path


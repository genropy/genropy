# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy dev - see LICENSE for details
# module gnr.dev.decorator : support funtions
# Copyright (c) : 2004 - 2024 Softwell sas - Milano
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

import inspect
from time import time
import functools

from gnr.core.gnrlang import thlocal
from gnr.dev import logger

    
def do_cprofile(profile_path=None):
    import cProfile
    profile_path = profile_path or 'stats.prf'
    def decore(func):
        def profiled_func(*args, **kwargs):
            profile = cProfile.Profile()
            try:
                profile.enable()
                result = func(*args, **kwargs)
                profile.disable()
                return result
            finally:
                profile.dump_stats(profile_path)
        return profiled_func
    return decore

def callers(limit=10):
    def decore(func):
        def wrapper(*fn_args, **fn_kwargs):
            stack = inspect.stack()
            logger.debug('%s:', func.__name__)
            for f in stack[1:limit+1]:
                logger.debug('%s:\t(%i) %s', f[3],f[2],f[1])
            return func(*fn_args, **fn_kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__dict__.update(func.__dict__)
        return wrapper
    return decore

def time_measure(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        duration = end_time - start_time
        logger.debug(f"Execution time of {func.__name__}: {duration:.4f} seconds")
        return result
    return wrapper


def timer_call(time_list=None, print_time=True):
    time_list = time_list or []
    def decore(func):
        def wrapper(*arg, **kw):
            t1 = time()
            res = func(*arg, **kw)
            t2 = time()
            if print_time:
                print('-' * 80)
                print('%s took %0.3f ms' % (func.__name__, (t2 - t1) * 1000.0))
                print(10 * ' ' + 28 * '-' + 'args' + 28 * '-' + 10 * ' ')
                print(arg)
                print(10 * ' ' + 27 * '-' + 'kwargs' + 27 * '-' + 10 * ' ')
                print(kw or (hasattr(arg[0], 'kwargs') and arg[0].kwargs))
                print('-' * 80)
            time_list.append((func.__name__, (t2 - t1) * 1000.0))
            return res

        return wrapper

    return decore

def time_cost():
    def decore(func):
        def wrapper(*arg, **kw):
            t1 = time()
            res = func(*arg, **kw)
            t2 = time()
            logger.debug('%s took %0.3f ms' % (func.__name__, (t2 - t1) * 1000.0))
            return res
        return wrapper
    return decore


def debug_call(attribute_list=None, print_time=False):
    """TODO
    :param time_list: TODO. 
    :param print_time: boolean. TODO"""
    import _thread

    attribute_list=attribute_list or []
    def decore(func):
        def wrapper(*arg, **kw):
            thread_ident = _thread.get_ident()
            t1 = time.time()
            tloc = thlocal()
            indent = tloc['debug_call_indent'] = tloc.get('debug_call_indent', -1) + 1
            print('%sSTART: %s in %s (args:%s, kwargs=%s)' % (indent, func.__name__, thread_ident, arg, kw))
            if attribute_list:
                values_dict = dict([(a,getattr(arg[0],a,None)) for a in attribute_list])
                print(values_dict)
            print('%sEND  : %s' % (indent, func.__name__))
            res = func(*arg, **kw)
            t2 = time.time()
            if print_time:
                print('-' * 80)
                print('%s took %0.3f ms' % (func.__name__, (t2 - t1) * 1000.0))
                print(10 * ' ' + 28 * '-' + 'args' + 28 * '-' + 10 * ' ')
                print(arg)
                print(10 * ' ' + 27 * '-' + 'kwargs' + 27 * '-' + 10 * ' ')
                print(kw or (hasattr(arg[0], 'kwargs') and arg[0].kwargs))
                print('-' * 80)
            #time_list.append((func.func_name, (t2 - t1) * 1000.0))
            return res
        return wrapper
    return decore

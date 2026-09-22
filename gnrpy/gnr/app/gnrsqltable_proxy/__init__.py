# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy app - see LICENSE for details
# module gnrsqltable_proxy : app level proxies attached to a database table
# Copyright (c)     : 2004 - 2026 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""App level table proxies.

The proxies under ``gnr.sql.gnrsqltable_proxy`` belong to the SQL layer and are
attached by the table itself.  The ones in this package belong to the
application layer: they are attached through ``gnr.app.gnrdbo.TableBase``, which
is mixed into every table of a ``GnrApp`` database.
"""

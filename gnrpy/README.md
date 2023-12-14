GenroPy
=======

GenroPy is a web framework for line-of-business applications in Python and Javascript.

Installation
============

inside the folder **gnrpy** you can execute 2 different installation:

	sudo pip install .
	
which will install the framework inside your system libraries or virtualenv.

You can install also optional dependencies, 3 different profiles are provided

* pgsql - for PostgreSQL database usage
* mysql - for MySQL database usage
* developer - will install extra tools usefule for genropy's development

Note: sqlite3 driver is installed by default with the base installation, no need
to use a specific profile.

By executing:

	sudo pip install .[profile_name]
   
For example:

	sudo pip install .[pgsql]
	
Multiple profiles are supported too:

	sudo pip install .[pgsql,developer]
	

To avoid system installation, you can run:

	sudo pip install --editable .
	
which will link to the current folder code rather than install the files. Useful for
development work. This replace the '''./setup.py develop''' command which is being
deprecated.
	
To create the enviroment configuration you can now execute:

	gnr app initgenropy

Configuration files are: 

	/.gnr/environment.xml
	/.gnr/instanceconfig/default.xml
	/.gnr/siteconfig/default.xml

Change your development edit **/.gnr/instanceconfig/default.xml**


Visit [www.genropy.org](http://) for more information


sandbox
=======
Sandbox is your first Genropy application.

Inside folder genropy_projects 

	git clone https://bitbucket.org/genropy/sandbox.git

Run a db setup

    gnr app dbsetup sandbox

Genropy webapplications needs a daemon

Run inside another terminal

	gnr app daemon

Now we are ready for running **sandbox** website

	gnr app wsgiserve sandbox
	
If you want to edit tutorial files through the application itself run **gnr app wsgiserve** with **remote_edit** option

	gnr app wsgiserve sandbox --remote_edit
	

License
=======

The code is licensed under the LGPL license::
    
    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.
    
    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU Lesser General Public License for more details.
    
    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

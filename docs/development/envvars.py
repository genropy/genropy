from mako.template import Template


variables = {
    "Testing": {
            "GNR_TEST_PG_PASSWORD": "Database server password for tests",
            "GNR_TEST_PG_HOST": "Database server host for tests",
            "GNR_TEST_PG_PORT": "Database server port for tests",
            "GNR_TEST_PG_USER": "Database server user for tests",
            "GNR_TESTING_INSTANCE_NAME": "Name of the instance when running tests",
    },
    "Deployment": {
        "GNR_RMS_CODE":"TBD",
        "GNR_RMS_CUSTOMER_CODE":"TBD",
        "GNR_RMS_URL":"TBD",
        "GNR_DB_IMPLEMENTATION" : "The database adapter to use (postgres, sqlite, etc)",
        "GNR_DB_NAME": "Name of the database to connect to",
        "GNR_DB_HOST": "Database server host to connect to",
        "GNR_DB_USER": "Database server user for connection",
        "GNR_DB_PORT": "Database server network port", 
        "GNR_DB_PASSWORD": "Database server password",
        "GNR_MAINPACKAGE": "Package to be used for authentication",
        "GNR_ROOTPWD": "Default password for 'admin' user",
        "GNR_EXTERNALHOST": "Public URL of the deployed application",
        "GNR_LOCAL_PROJECTS": "TBD",
        "GNR_CUSTOM_PACKAGE": "TBD",
        "GNR_CUSTOMER_PACKAGE_GIT": "TBD",
        "GNRHOME": "Local folder for genropy projects",
        "GNRINSTANCES": "TBD",
        "GNRPACKAGES": "TBD",
        "GNRSITES": "TBD",
        "GENRO_GNRFOLDER": "TBD",
        "GNR_LOCALE": "The default locale (en_US, it_IT, etc)",
        "GNR_LOGLEVEL": "The default logging level (debug, info, warning, error)",
        "GNR_CURRENT_SITE": "TBD",
        "GNR_WSGI_OPT_": "Prefix for options to be passed to the wsgi server",
        "GNR_GUNICORN_": "Prefix for options to be passed to the gunicorn based application server",
    }
    

}

template_content = """
Genropy Framework Environment Variables Reference Guide	
=======================================================

.. contents::
   :local:
   :depth: 3
	      
Introduction
------------

This document provides a reference guide for all environment variables used in
the Genropy application framework. Each variable includes its name, a
description of its purpose, possible expected value(s), and default
values (if applicable).

Environment Variables
---------------------
% for section, vars in variables.items():

${"=" * len(section) }
${section}
${"=" * len(section) }

.. _env-vars-table-${section}:

.. list-table::
   :header-rows: 1
   :widths: 40 60
	    
   * - Variable
     - Description
% for var, desc in vars.items():
   * - ``${var}``
     - ${desc}
% endfor

Detailed Variable Descriptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

% for var, desc in vars.items():
${var}
${"_" * len(var)}

**Description**: ${desc}

% endfor
% endfor 

Notes
-----

- Environment variables can be used in shell configuration,
  Dockerfiles, docker compose file, or in deployment enviroment.
- Be mindful of type expectations (data type are not always enforced).
																      
"""

template = Template(template_content, strict_undefined=True)
conf_content = template.render(variables=variables)
print(conf_content)

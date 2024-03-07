# Building Genropy Packages

## Prerequisites

Please be sure that you've installed all the developer tools by
issuing the following command:

```sudo pip install .[developer]```


PLEASE NOTE: all of the above command must be issued within the
'gnrpy' folder.

## Version

Please remember to increase the version of the package, by editing the
costant ```VERSION``` located in ```gnrpy/gnr/__init__.py```.

If the version number doesn't change, you won't be able to upload a
new package to the PyPI index.

## Building

To build a new package execute:

```python3 -m build --wheel .```

This will create the ```build``` directory with the installation files
(suitable for debugging the package content) and a ```dist```
directory with the distribution packages in ```wheel``` format
(successor to ```egg`` format).


## Uploading

Uploading a wheel package will copy the package in pythonhosted CDN
and it will add the new release file to the PyPI indexes.

The default upload tool is ```twine```, which relies on pypi
configuration files (like ```~/.pypirc```) for credential caching.

Please be sure to have a personal account to the index you're
uploading to, sufficient permission to upload new packages and
credentials ready. Using the API token and saving it in
```~/.pypirc``` is a convenient way to avoid credentials input,
although they're more easily to get stolen.

NOTE that if you've enable 2FA authentication on the index account,
you won't be able to use username/password, but you'll have to create
an API Token anyway.

### Uploading package to the test index

The test.pypi.org index is a sandbox to test the
packaging/upload/installation process (codename ```testpypi```)

Execute the following to upload a builded wheel package:

```twine upload --repository testpypi dist/genropy-<VERSION>```

with ```<VERSION>``` being the new version you've choosen. If there
are no other builded package in the dist directory, you can rely on
shell globbing, but you better not to.

### Uploading package to the production index

The pypi.org is the official index, the default used by ```pip``` and
related tools.

Execute the following to upload a builded wheel package:

```twine upload dist/genropy-<VERSION>```

with ```<VERSION>``` being the new version you've choosen. If there
are no other builded package in the dist directory, you can rely on
shell globbing, but you better not to.






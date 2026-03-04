# -*- coding: utf-8 -*-
import sys
import shutil
import os, os.path
import json
import gnr
import subprocess
import socket

from gnr.core.gnrbag import Bag
from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp

description = "Create a report of the environment useful for bug reporting"


def send_to_paste_service(message):
    try:
        with socket.create_connection(("termbin.com", 9999), 30) as client_socket:
            client_socket.sendall(message.encode('utf-8'))
            response = client_socket.recv(4096)  # Adjust buffer size as needed
            return response.decode('utf-8')

    except (socket.timeout, ConnectionRefusedError) as e:
        raise


def git_command(path, cmd):
    try:
        result = subprocess.run(["git", "-C", path] + cmd,
                                capture_output=True,
                                text=True,
                                check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None
    
def main():
    p = GnrCliArgParse(
        description=description
    )
    p.add_argument("-j", "--json",
                   help="Output data in json format",
                   action="store_true", default=False)
    p.add_argument("-b", "--bag",
                   help="Output data in Bag xml format",
                   action="store_true", default=False)
    p.add_argument("-p", "--paste",
                   help="Send to paste service",
                   action="store_true", default=False)
    p.add_argument("instance_name", nargs="+")
    options = p.parse_args()
    args = options.instance_name
    instance_name = args[0]

    try:
        app = GnrApp(instance_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # collect data
    cdata = {}
    cdata['instance_name'] = instance_name
    cdata['genropy_version'] = gnr.VERSION

    # test if we have git
    have_git = shutil.which("git")
    
    if have_git:
        framework_path = os.path.dirname(gnr.__file__)
        genropy_branch = git_command(framework_path,
                                     ["rev-parse", "--abbrev-ref", "HEAD"])
        if genropy_branch:
            cdata['genropy_from_git'] = True
            cdata['genropy_git_branch'] = genropy_branch
            cdata['genropy_git_commit'] = git_command(framework_path,
                                                      ['rev-parse', 'HEAD'])
        else:
            cdata['genropy_from_git'] = False

    # analyze packages
    cdata['packages'] = dict()
    for a, p in app.packages.items():
        package_data = dict()
        if have_git:
            package_branch = git_command(p.packageFolder,
                                         ["rev-parse","--abbrev-ref", "HEAD"])
            if package_branch:
                package_data["from_git"] = True
                package_data["repository"] = os.path.basename(git_command(p.packageFolder,
                                                               ["rev-parse", "--show-toplevel"]))
                package_data["git_branch"] = package_branch
                package_data["git_commit"] = git_command(p.packageFolder,
                                                               ['rev-parse', 'HEAD'])

            else:
                package_data["from_git"] = False
        cdata['packages'][a] = package_data
                
    output = cdata
    if options.json:
        output = json.dumps(cdata)
    elif options.bag:
        b = Bag(cdata)
        output = b.toXml()
    else:
        output = "\n".join([f"{k}: {v}" for k, v in cdata.items() if k != "packages"])
        output += "\nPackages:\n"
        for p, data in cdata['packages'].items():
            output += f"{p}\n"
            for attr, val in data.items():
                output += f"  {attr}: {val}\n"
                
    if options.paste:
        url = send_to_paste_service(output)
        print(f"Paste uploaded, please share the URL: {url}")
    else:
        print(output)

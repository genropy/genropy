#!/usr/bin/env python
# encoding: utf-8
"""
Main genropy script launcher. It lookups for CLI commands inside
all packages in the gnr namespace, organize them in section and commands,
and shift argv to let each script handle arguments by itself.
"""

import time
import os, os.path
import sys
import platform
from importlib import import_module
import importlib.util
from pathlib import Path
from collections import defaultdict

import gnr

class CommandManager():
    def __init__(self):
        self.BASE_DIR = os.path.dirname(gnr.__file__)
        self.script_tree = defaultdict(dict)
        self.argv = sys.argv[:]
        self.argv.pop(0)
        self.instance = None
        if self.argv:
            if self.argv[0].startswith("@"):
                from gnr.app.gnrapp import GnrApp
                # try loading the instance, if it
                # doesn't exists, continue with the framework
                # commands
                try:
                    self.instance = GnrApp(self.argv[0][1:])
                    self.load_instance_script_tree()
                except:
                    raise
                    pass
                
        if not self.instance:
            self.load_framework_script_tree()
        
    def load_instance_script_tree(self):
        cli_files = []
        for section, package_obj in self.instance.packages.items():
            PACKAGE_DIR = package_obj.packageFolder
            for root, dirs, files in os.walk(PACKAGE_DIR):
                if 'cli' in dirs:
                    cli_folder = os.path.join(root, 'cli')
                    for fname in os.listdir(cli_folder):
                        if fname.endswith('.py') and not fname.startswith("_"):
                            package_name = fname.replace(".py", "")
                            alter_name  = package_name.startswith("gnr")
                            command_name = package_name.replace("gnr", "")
                            if command_name:
                                self.script_tree[section][command_name] = (
                                    package_name, alter_name,
                                    (section, command_name, alter_name)
                                )
        self.argv.pop(0)
        
    def load_framework_script_tree(self):
        cli_files = []
        for root, dirs, files in os.walk(self.BASE_DIR):
            if 'cli' in dirs:
                section = os.path.basename(root)
                cli_folder = os.path.join(root, 'cli')
                for fname in os.listdir(cli_folder):
                    if fname.endswith('.py') and not fname.startswith("_"):
                        package_name = fname.replace(".py", "")
                        alter_name  = package_name.startswith("gnr")
                        command_name = package_name.replace("gnr", "")
                        if command_name:
                            self.script_tree[section][command_name] = (
                                package_name, alter_name,
                                (section, command_name, alter_name)
                            )
                        
    def load_module(self, section, command, alter_name):
        if self.instance:
            package_path = self.instance.packages[section].packageFolder
            module_path = Path(os.path.join(package_path, "cli", f"{command}.py")).resolve()
            spec = importlib.util.spec_from_file_location(command, module_path)
            if spec is None:
                raise ImportError(f"Cannot load module from {module_path}")
    
            module = importlib.util.module_from_spec(spec)
            sys.modules[command] = module
            spec.loader.exec_module(module)
            return module            
        else:
            if alter_name == True:
                command = f'gnr{command}'
            module_name = f'gnr.{section}.cli.{command}'
            return import_module(module_name)
        
    def print_main_help(self):
        print("Usage: gnr <section> <command> [options]\n")
        print("Or: gnr @instancename <package> <command> [options]\n")
        print("The 'gnr' command is a management command to access all the command line")
        print(f"utilities provided by Genropy framework and projects - Version {gnr.VERSION}\n")

        sections = self.script_tree.keys()
        if sections:
            if self.instance:
                print(f"Available commands from instance {self.instance.instanceName} packages:")
            else:
                print(f"Available sections and commands:")
                
            for section in sorted(sections):
                self.print_section_commands(section)
        else:
            print("No section/commands found.")
            
    def print_section_help(self, section):
        print(f"Usage: gnr {section} <command> [options]")
        print(f"Version: {gnr.VERSION}\n")
        print("Available commands:")
        self.print_section_commands(section)
        
    def print_section_commands(self, section):
        if self.script_tree[section]:
            if platform.system() in ['Linux', 'Darwin']:
                print(f"\n\033[92m[{section}]\033[00m\n")
                missing_doc =  "\033[91mMISSING DESCRIPTION\033[00m"
            else:
                print(f"[{section}]")
                missing_doc = "MISSING DESCRIPTION"
                
            for command, cmd_impl in sorted(self.script_tree[section].items()):
                l_module = self.load_module(*cmd_impl[2])
                description = getattr(l_module, "description", "").capitalize()
                gnr_cli_hide = getattr(l_module, "gnr_cli_hide", False)
                if gnr_cli_hide:
                    continue
                if not description:
                    description = missing_doc
                print(f"  {command :>15} - {description}")
                
    def lookup_new_name(self, old_name):
        """
        Lookup the 'right' command name when a script
        is executed through a old legacy script
        """
        new_name = old_name
        for section, commands in self.script_tree.items():
            for new_cmd_name, cmd_impl in commands.items():
                if cmd_impl[0] == old_name:
                    new_name = f"gnr {section} {new_cmd_name}"
                    break
        return new_name
    
    def run(self):
        if not self.argv:
            if "GNR_AUTOCOMPLETE" in os.environ:
                print(" ".join(self.script_tree.keys()))
                return
            self.print_main_help()
            return

        if len(self.argv) == 1:
            if "GNR_AUTOCOMPLETE" in os.environ:
                print(" ".join(self.script_tree[self.argv[0]].keys()))
                return
            
            if self.argv[0] in ["-h", "--help", "--version"]:
                self.print_main_help()
                return
            
            if self.argv[0] in self.script_tree:
                self.print_section_help(self.argv[0])
            else:
                print("Command section not found! please run with --help")

        if len(self.argv) > 1:
            if self.argv[0] not in self.script_tree:
                print("Command section not found! please run with --help")
                return

            if self.argv[1] in ["--help", "-h", "--version"]:
                self.print_section_help(self.argv[0])
                return
            
            
            if self.argv[1] in self.script_tree[self.argv[0]]:
                cmd_impl = self.script_tree[self.argv[0]][self.argv[1]]
                # trick argparse for command implementation
                if self.instance:
                    command_name = " ".join(sys.argv[:4])
                    sys.argv = sys.argv[4:]
                else:
                    command_name = " ".join(sys.argv[:3])
                    sys.argv = sys.argv[3:]
                sys.argv.insert(0, command_name)
                
                cmd_module = self.load_module(*cmd_impl[2])

                # measure execution time
                start_time = time.time()
                if self.instance:
                    cmd_module.main(self.instance)
                else:
                    cmd_module.main()
                    
                end_time = time.time() - start_time
                
                if "--timeit" in sys.argv:
                    print(f"Total execution time: {end_time:.3f}s", file=sys.stderr)
                
            else:
                print("Command not found! please run with --help")

cmd = CommandManager()        
def main():
    cmd.run()

if __name__ == "__main__":
    main()

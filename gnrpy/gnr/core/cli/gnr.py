#!/usr/bin/env python
# encoding: utf-8
"""
Main genropy script launcher. It lookups for CLI commands inside
all packages in the gnr namespace, organize them in section and commands,
and shift argv to let each script handle arguments by itself.
"""

import os.path
import sys
import argparse
from importlib import import_module
import pkgutil
from collections import defaultdict
import gnr

class CommandManager():
    def __init__(self):
        BASE_DIR = os.path.dirname(gnr.__file__)
        self.script_tree = defaultdict(dict)
        self.argv = sys.argv[:]
        self.argv.pop(0)
        # load all available CLI commands looking
        # inside the 'gnr' namespace
        for section in pkgutil.iter_modules(path=[BASE_DIR]):
            package_cli_cmds = pkgutil.iter_modules(
                path=[os.path.join(section.module_finder.path, section.name, "cli")])
            for command in package_cli_cmds:
                if command.ispkg==False:
                    alter_name = command.name.startswith("gnr")
                    command_name = command.name.replace("gnr", "")
                    if command_name:
                        try:
                            self.script_tree[section.name][command_name] = (
                                command, alter_name,
                                self.load_module(section.name, command_name, alter_name)
                            )
                        except:
                            continue
                        
    def load_module(self, section, command, alter_name):
        if alter_name == True:
            command = f'gnr{command}'
        module_name = f'gnr.{section}.cli.{command}'
        return import_module(module_name)
        
    def print_main_help(self):
        print("Usage: gnr <section> <command> [options]\n")
        print("The 'gnr' command is a management command to access all the command line")
        print("utilities provided by the framework\n")

        print("Available sections and commands:")
        for section in self.script_tree.keys():
            self.print_section_commands(section)

    def print_section_help(self, section):
        print(f"Usage: gnr {section} <command> [options]\n")
        print("Available commands:")
        self.print_section_commands(section)
        
    def print_section_commands(self, section):
        if self.script_tree[section]:
            print(f"\n\033[92m[{section}]\033[00m\n")
            for command, cmd_impl in self.script_tree[section].items():
                missing_doc =  "\033[91mMISSING DESCRIPTION\033[00m"
                description = getattr(cmd_impl[2], "description", "")
                if not description:
                    description = missing_doc
                print(f"  {command :>20} - {description}")
            
    def run(self):
        if not self.argv:
            self.print_main_help()

        if len(self.argv) == 1:
            if self.argv[0] in ["-h", "--help"]:
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

            if self.argv[1] in ["--help", "-h"]:
                self.print_section_commands(self.argv[0])
                return
            
            if self.argv[1] in self.script_tree[self.argv[0]]:
                cmd_impl = self.script_tree[self.argv[0]][self.argv[1]]
                # trick argparse for command implementation
                command_name = " ".join(sys.argv[:3])
                sys.argv = sys.argv[3:]
                sys.argv.insert(0, command_name)
                # sys.argv.pop(0)
                # sys.argv.pop(0)
                # sys.argv.pop(0)
                # sys.argv.insert(0, cmd_impl[0].name)
                cmd_module = cmd_impl[2]
                cmd_module.main()
                
            else:
                print("Command not found! please run with --help")
        
def main():
    cmd = CommandManager()
    cmd.run()


#!/usr/bin/env python3
import argparse
import subprocess
import sys
import signal
import shutil

from gnr.core.cli import GnrCliArgParse

description = """Start a complete application stack"""

AVAILABLE_COMMANDS = {
    "daemon": "gnr web daemon",
    "application": "gnr web serve",
    "taskscheduler": "gnr web taskscheduler",
    "taskworker": "gnr web taskworker",
}

# normalize cli command path
for k, v in AVAILABLE_COMMANDS.items():
    sc = v.split()
    sc[0] = shutil.which(sc[0])
    AVAILABLE_COMMANDS[k] = " ".join(sc)
    
processes = {}

def start_process(cmd_name, command_path, site, args):
    cmd = [sys.executable] + command_path.split() + [site]
    if args:
        cmd.extend(args)
    print(f"Starting {cmd_name}...", end='')
    proc = subprocess.Popen(cmd)
    processes[cmd_name] = proc
    print("OK")


def stop_all_processes():
    print("Stopping all child processes...")
    for cmd_name,proc in processes.items():
        if proc.poll() is None:
            print(f"Terminating {cmd_name}...", end='')
            proc.terminate()
            print("Done")

def signal_handler(sig, frame):
    print("Received termination signal.")
    stop_all_processes()
    sys.exit(0)

def parse_args():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance_name", help="The instance name")

    # Dynamically add argument groups for each app
    for app in AVAILABLE_COMMANDS:
        parser.add_argument(f"--no-{app}", action="store_true",
                            help=f"Do not start  {app}")
                
        parser.add_argument(f"--{app}", nargs=argparse.REMAINDER,
                            help=f"Arguments for {app}")

    return parser.parse_args()

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_args()
    instance_name = args.instance_name
    for app_name, script_path in AVAILABLE_COMMANDS.items():
        # if --no-<app_name> is present, don't start the related process
        if getattr(args, f"no_{app_name}"):
            print(f"Not starting {app_name}")
            continue
        
        app_args = getattr(args, app_name)
        start_process(app_name, script_path, instance_name, app_args)

    try:
        for cmd_name, proc in processes.items():
            proc.wait()
    except KeyboardInterrupt:
        stop_all_processes()

if __name__ == "__main__":
    main()

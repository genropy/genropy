#!/usr/bin/env python3
import subprocess
import sys
import signal
import shutil

from gnr.core.cli import GnrCliArgParse

description = """Start a complete application stack"""

AVAILABLE_COMMANDS = {
    "daemon": "gnr web daemon",
    "application": "gnr web serveprod",
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
    cmd = [sys.executable] + command_path.split()

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
    parser.add_argument("--all", dest="_start_all",
                        action="store_true", help="Start all services")

    # Parse known args, leave the rest
    known_args, unknown_args = parser.parse_known_args()

    # Custom parsing for --{app} options
    app_args = {app: None for app in AVAILABLE_COMMANDS}
    argv = sys.argv[1:]
    # Remove instance_name and eventual --all
    filtered_argv = []
    skip_next = False
    for i, arg in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if arg == known_args.instance_name or arg == known_args._start_all:
            continue
        if any(arg == f"--no-{app}" for app in AVAILABLE_COMMANDS):
            continue
        filtered_argv.append(arg)

    # Now, parse --{app} and their arguments
    i = 0
    while i < len(filtered_argv):
        arg = filtered_argv[i]
        if arg.startswith("--") and arg[2:] in AVAILABLE_COMMANDS:
            app = arg[2:]
            j = i + 1
            app_argv = []
            while j < len(filtered_argv) and not (filtered_argv[j].startswith("--") and filtered_argv[j][2:] in AVAILABLE_COMMANDS):
                app_argv.append(filtered_argv[j])
                j += 1
            app_args[app] = app_argv
            i = j
        else:
            i += 1

    # Attach app_args to known_args
    for app in AVAILABLE_COMMANDS:
        setattr(known_args, app, app_args[app])
    return known_args

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_args()
    instance_name = args.instance_name
    for app_name, script_path in AVAILABLE_COMMANDS.items():
        if getattr(args, f"{app_name}", None) is None and not args._start_all:
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

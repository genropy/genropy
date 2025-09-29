#!/usr/bin/env python
# encoding: utf-8
#
from gnr.core.cli import GnrCliArgParse
from gnr.web import gnrtask

description = "Control the task scheduler"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('--url',
                        dest='url',
                        default=gnrtask.GNR_SCHEDULER_URL,
                        help="The scheduler URL")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reload_parser = subparsers.add_parser("reload", help="Reload the scheduling configuration")
    status_parser = subparsers.add_parser("status", help="Get the current status of scheduler/workers")

    stop_run_parser = subparsers.add_parser("stop_run", help="Stop the current running job")
    stop_run_parser.add_argument("run_id",
                                 help='The run id to stop')
    
    empty_queue_parser = subparsers.add_parser("empty_queue", help="Empty the execution queue(s)")
    empty_queue_parser.add_argument('-q', '--queue-name',
                              nargs="?",
                              required=True,
                              help='The queue to connect to',
                              dest='queue_name')

    fake_parser = subparsers.add_parser("genfake", help="Generate fake tasks")
    fake_parser.add_argument('-n', '--number',
                             default=1,
                             type=int,
                             dest='fake_number',
                             help='The quantity of fake task to generate')


    execute = subparsers.add_parser("execute", help="Insert a task in queue")
    execute.add_argument("table")
    execute.add_argument("action")
    execute.add_argument("--parameters", default=None)
    execute.add_argument("user")
    execute.add_argument("domains")
    execute.add_argument("worker_code")
    execute.add_argument("--attime",
                         default=None)
    
    options = parser.parse_args()

    client = gnrtask.GnrTaskSchedulerClient(url=options.url)
    
    if options.command == 'reload':
        try:
            r = client.reload()
            if r:
                print(f"Reload completed: {r.ok}")
        except Exception as e:
            print(f"Error: {e}")
    elif options.command == 'status':
        try:
            r = client.status()
            print(r)
        except Exception as e:
            print(f"Error: {e}")

    elif options.command == 'genfake':
        try:            
            r = client.gen_fake(options.fake_number)
            print(f"Completed: {r.ok}")
        except Exception as e:
            print(f"Error: {e}")

    elif options.command == 'empty_queue':
        try:
            r = client.empty_queue(options.queue_name)
            print(f"Completed: {r.ok}")
        except Exception as e:
            print(f"Error: {e}")

    elif options.command == 'stop_run':
        try:
            r = client.stop_run(options.run_id)
            print(f"Completed: {r.ok}")
        except Exception as e:
            print(f"Error: {e}")

    elif options.command == 'execute':
        try:
            r = client.execute(options.table,
                               options.action,
                               options.parameters,
                               options.user,
                               options.domains,
                               options.worker_code,
                               options.attime)
            print(f"Completed: {r.ok}")
        except Exception as e:
            print(f"Error: {e}")
        
if __name__=="__main__":
    main()

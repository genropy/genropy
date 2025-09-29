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
    execute.add_argument("--action_parameters", default=None)
    execute.add_argument("user")
    execute.add_argument("domains")
    execute.add_argument("page_id")
    execute.add_argument("worker_code")
    execute.add_argument("--attime",
                         default=None)
    
    options = parser.parse_args()

    client = gnrtask.GnrTaskSchedulerClient(url=options.url)
    
    if options.command == 'reload':
        client.reload()
        if r:
            print(f"Reload completed: {r.ok}")

    elif options.command == 'status':
        r = getattr(client, options.command)()
        print("Status:")
        print(r)

    elif options.command == 'genfake':
        r = client.gen_fake(options.fake_number)
        print(f"Completed: {r.ok}")

    elif options.command == 'empty_queue':
        r = client.empty_queue(options.queue_name)
        print(f"Completed: {r.ok}")

    elif options.command == 'stop_run':
        r = client.stop_run(options.run_id)
        print(f"Completed: {r.ok}")
        
    elif options.command == 'execute':
        r = client.execute(options.table,
                           options.action,
                           options.action_parameters,
                           options.user,
                           options.domains,
                           options.page_id,
                           options.worker_code,
                           options.attime)
        print(f"Completed: {r.ok}")
        
if __name__=="__main__":
    main()

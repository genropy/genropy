#!/usr/bin/env python
import sys

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.app import logger

description = "execute cleanup based on data retention policies"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("--yes-i-am-sure", action="store_true",
                        help="Required to actually delete (safety latch)")
    parser.add_argument("-p", "--policy", action="store_true",
                        help="Show the current policy and exit")
    parser.add_argument("instance_name")
    
    options = parser.parse_args()

    dry_run = not options.yes_i_am_sure
    if dry_run:
        logger.info("Dry-run execution")
        
    app = GnrApp(options.instance_name)

    policy = app.retentionPolicy
    if not policy:
        logger.warning("No policies defined in any table for this app!")
        sys.exit(1)

    if options.policy:
        print("Current policy:")
        for table, conf in policy.items():
            print(f"Table: {table.name} - Retention for {conf[1]} days based on field '{conf[0]}'")
        sys.exit(3)
        
    summary = app.executeRetentionPolicy(dry_run=dry_run)
    for table, report in summary.items():
        logger.info(f"{table.fullname}", report)
    
        
if __name__ == "__main__":
    main()

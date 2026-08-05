#!/usr/bin/env python

# provide insights for a specific app

import sys

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrutils import GnrAppInsights

description = "provide app insights"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("-b", "--bag",
                        dest="bag",
                        action="store_true",
                        help="Output as GnrBag")

    parser.add_argument("-l", "--list",
                        dest="list",
                        action="store_true",
                        help="Show a list of insights")

    parser.add_argument("instance_name",
                        help="Name of the instance to analyze")
    available_insights = list(GnrAppInsights.insights.keys())
    
    parser.add_argument("insight_name", nargs="?",
                        choices=available_insights,
                        default=available_insights[0], metavar="insight_name",
                        help=f"Requested insight: {', '.join(available_insights)}")
    options = parser.parse_args()

    if options.list:
        print("Available insights")
        print("------------------")
        for i_name, i_class in GnrAppInsights.insights.items():
            print(i_name, i_class.__doc__)
        sys.exit(2)
    
    try:
        insights = GnrAppInsights(options.instance_name,
                                  options.insight_name)
    except Exception as e:
        print(f"Error getting insights for {options.instance_name}: {e}")
        sys.exit(1)

    if options.bag:
         b = insights.retrieve(as_bag=True)
         print(b.toXml())
         sys.exit(0)

    title = f"Instance {options.instance_name} insights"
    print(title)
    print("="*len(title))

    insights.pprint()
    

if __name__ == "__main__":
    main()

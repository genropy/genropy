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

    parser.add_argument("instance_name")
    parser.add_argument("insight_name", nargs="?")
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
    
    r = insights.retrieve()

    for section, data in r.items():
        section_title = section.replace("_", " ").capitalize()
        print(section_title)
        print("-"*len(section_title))
        print(" ")
        for project_component, component_data in data.items():
            print(project_component.capitalize())
            print("-"*len(project_component))
            for package, package_stats in component_data.items():
                print(f"{package:<16}: {package_stats['percentage']:=6.2f}% ({package_stats['lines']})")
            print("")

if __name__ == "__main__":
    main()

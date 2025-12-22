#!/usr/bin/env python3

import sys
import os.path
import tempfile
from pathlib import Path
from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbageditor import BagEditor
from gnr.core.gnrconfig import getEnvironmentPath
from gnr.core.gnrbag import Bag

def get_default_file_paths():
    """Get default file paths, returning None if environment is not configured."""
    try:
        env_path = getEnvironmentPath()
        if env_path is None:
            return None, None, None

        environment_file = env_path
        instance_file = os.path.join(os.path.dirname(env_path), "instanceconfig", "default.xml")
        siteconfig_file = os.path.join(os.path.dirname(env_path), "siteconfig", "default.xml")
        return environment_file, instance_file, siteconfig_file
    except Exception:
        return None, None, None


def parse_attributes(attr_strings):
    """Parse attribute strings like 'path="/foobar"' into a dictionary."""
    attributes = {}
    if not attr_strings:
        return attributes

    for attr_string in attr_strings:
        if '=' not in attr_string:
            print(f"Error: Invalid attribute format '{attr_string}'. Expected format: key=value", file=sys.stderr)
            sys.exit(1)

        key, value = attr_string.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        attributes[key] = value

    return attributes

description = "Manipulate Bag entities via command line"

def main():
    parser = GnrCliArgParse(
        description=description,
        epilog='Examples:\n'
               '  %(prog)s file.xml add projects.foobar.goober weight="1" --output result.xml\n'
               '  cat file.xml | %(prog)s - add projects.test path="/foo" --output -\n'
               '  %(prog)s --environment-default get projects.custom1'
    )

    parser.add_argument('file', nargs='?', help='XML file to modify (use "-" to read from stdin, optional if using --*-default flags)')
    parser.add_argument('operation', choices=['add', 'delete', 'update', 'get', 'set'],
                       help='Operation to perform (add creates if missing, update requires existing, get retrieves entity)')
    parser.add_argument('entity_path', help='Dot-separated path to entity (e.g., projects.custom1)')
    parser.add_argument('attributes', nargs='*', help='Attributes to set (format: key=value, not used for get)')
    parser.add_argument('--indent', action='store_true', help='Pretty-print XML output with indentation')
    parser.add_argument('-o', '--output', help='Output file path (use "-" for stdout, defaults to overwriting source file or stdout if reading from stdin)')

    # Default file options
    parser.add_argument('--environment-default', action='store_true',
                       help='Use default environment configuration file')
    parser.add_argument('--instance-default', action='store_true',
                       help='Use default instance configuration file')
    parser.add_argument('--siteconfig-default', action='store_true',
                       help='Use default siteconfig configuration file')

    args = parser.parse_args()

    # Determine which file to use
    default_flags = [args.environment_default, args.instance_default, args.siteconfig_default]
    if sum(default_flags) > 1:
        print("Error: Only one default flag can be specified at a time", file=sys.stderr)
        sys.exit(1)

    using_stdin = False
    temp_file = None

    if args.environment_default or args.instance_default or args.siteconfig_default:
        if args.file is not None:
            print("Error: Cannot specify both a file and a default flag", file=sys.stderr)
            sys.exit(1)
        # Get default file paths
        environment_file, instance_file, siteconfig_file = get_default_file_paths()

        if args.environment_default:
            if environment_file is None:
                print("Error: No Genro environment configured", file=sys.stderr)
                sys.exit(1)
            file_path = environment_file
        elif args.instance_default:
            if instance_file is None:
                print("Error: No Genro environment configured", file=sys.stderr)
                sys.exit(1)
            file_path = instance_file
        elif args.siteconfig_default:
            if siteconfig_file is None:
                print("Error: No Genro environment configured", file=sys.stderr)
                sys.exit(1)
            file_path = siteconfig_file
    elif args.file == '-':
        # Read from stdin
        using_stdin = True
        try:
            stdin_content = sys.stdin.read()
            if not stdin_content.strip():
                print("Error: No input provided on stdin", file=sys.stderr)
                sys.exit(1)

            # Create a temporary file to load the XML
            temp_fd, temp_file = tempfile.mkstemp(suffix='.xml', text=True)
            with os.fdopen(temp_fd, 'w') as f:
                f.write(stdin_content)
            file_path = temp_file
        except Exception as e:
            print(f"Error reading from stdin: {e}", file=sys.stderr)
            if temp_file:
                Path(temp_file).unlink(missing_ok=True)
            sys.exit(1)
    elif args.file is not None:
        # Regular file path provided
        file_path = args.file
    else:
        # No file specified and no default flag
        print("Error: Either specify a file or use one of the --*-default flags", file=sys.stderr)
        sys.exit(1)

    # Determine output destination
    if args.output:
        output_path = args.output
    elif using_stdin:
        # Default to stdout when reading from stdin
        output_path = '-'
    else:
        # Default to overwriting source file
        output_path = file_path

    # Initialize BagEditor
    editor = BagEditor()

    # Load XML file
    try:
        editor.load(file_path)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        if temp_file:
            Path(temp_file).unlink(missing_ok=True)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if temp_file:
            Path(temp_file).unlink(missing_ok=True)
        sys.exit(1)
    finally:
        # Clean up temp file after loading (we don't need it anymore)
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink(missing_ok=True)

    # Perform operation
    try:
        if args.operation == 'get':
            # Handle get operation (read-only, no save needed)
            if args.attributes:
                print("Warning: Attributes are ignored for get operation", file=sys.stderr)

            entity = editor.get_entity(args.entity_path)
            if entity is None:
                print(f"Error: Entity not found: {args.entity_path}", file=sys.stderr)
                sys.exit(1)

            # Display entity information
            print(f"Entity: {args.entity_path}")
            print(f"Value: {entity['value']}")
            if entity['attributes']:
                print("Attributes:")
                for key, value in entity['attributes'].items():
                    print(f"  {key}: {value}")
            else:
                print("Attributes: (none)")
        else:
            # Parse attributes for add/update operations
            attributes = parse_attributes(args.attributes)

            if args.operation == 'add':
                editor.add_entity(args.entity_path, attributes)
            if args.operation == 'set':
                editor.set_entity(args.entity_path, attributes)
            elif args.operation == 'delete':
                if args.attributes:
                    print("Warning: Attributes are ignored for delete operation", file=sys.stderr)
                editor.delete_entity(args.entity_path)
            elif args.operation == 'update':
                editor.update_entity(args.entity_path, attributes)

            # Save the result
            if output_path == '-':
                # Write to stdout
                xml_content = editor.bag.toXml(autocreate=False, encoding='UTF-8')
                sys.stdout.write(xml_content)
                sys.stdout.flush()
            else:
                # Save to file
                editor.save(output_path)
                if output_path != file_path:
                    print(f"Successfully {args.operation}ed entity: {args.entity_path} (saved to {output_path})", file=sys.stderr)
                else:
                    print(f"Successfully {args.operation}ed entity: {args.entity_path}", file=sys.stderr)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

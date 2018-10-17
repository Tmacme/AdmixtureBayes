"""running the premd script..."""

import sys
from call_AdmixtureBayes import main as run_main
import argparse

import colorama
from termcolor import colored

from . import configuration



# Enable colours on Windows
colorama.init()


# should always be set when we run a script!
CONFIGS = configuration.Configurations()


def _report_error(msg):
    output_msg = colored("Error", "red", attrs=["bold"]) + ": " + msg
    print(output_msg, file=sys.stderr)


def _error(msg):
    _report_error(msg)
    sys.exit(1)


def _collect_commands():
    commands = {}
    for name, value in globals().items():
        if callable(value) and name.endswith("_command"):
            command_name = name.rsplit("_command", 1)[0]
            commands[command_name] = value
    return commands


# Commands
# For formatting main argument parseing message
class MixedFormatter(argparse.ArgumentDefaultsHelpFormatter,
                     argparse.RawDescriptionHelpFormatter):
    pass

def run_command(args):
    run_main(args)


# Main app
def main():
    "Main entry point for the script"
    commands = _collect_commands()
    commands_doc = "commands:\n{commands}".format(
        commands="\n".join(
            "  {name:10}:\t{doc}".format(name=name, doc=command.__doc__)
            for name, command in commands.items()
        )
    )

    parser = argparse.ArgumentParser(
        formatter_class=MixedFormatter,
        description="AdmixtureBayes program and auxillary tools",
        epilog=commands_doc
    )
    parser.add_argument(
        'command',
        help="Subcommand to run",
        metavar='command',
        choices=commands.keys()
    )
    parser.add_argument(
        'args', nargs="*",
        help="Arguments to subcommand"
    )

    args = parser.parse_args(sys.argv[1:2])  # only first two
    if args.command not in commands:
        _report_error("Unknown subcommand: {}".format(args.command))
        parser.print_help()
        sys.exit(1)

    commands[args.command](sys.argv[2:])


# Run this in case the module is called as a program...
if __name__ == "__main__":
    main()

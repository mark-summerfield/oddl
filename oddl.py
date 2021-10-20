#!/usr/bin/env python3
# Copyright © 2021 Mark Summerfield. All rights reserved.
# License: GPLv3

__version__ = '0.1.1'


if __name__ == '__main__':
    import pathlib
    import sys

    if len(sys.argv) == 1 or sys.argv[1] in {'h', 'help', '-h', '--help'}:
        raise SystemExit(f'''\
usage: {pathlib.Path(sys.argv[0]).name} \
[lint|minimize|pretty] <file1.oddl> [<file2.oddl> [... <fileN.oddl>]]
 -or-: {pathlib.Path(sys.argv[0]).name} help

h help     : show this usage and quit.
l lint     : check each .oddl file and report any problems (easiest to use
             after pretty); this is the default action.
m minimize : remove all redundant whitespace from each .oddl file.
p pretty   : insert newlines and whitespace to make each .oddl file
             human-readable.

Letter options may be prefixed by - and word options by -- e.g., \
-m or --pretty
''')


    def lint(filename):
        print('TODO lint', filename)


    def minimize(filename):
        print('TODO minimize', filename)


    def pretty(filename):
        print('TODO pretty', filename)


    action = lint
    index = 1
    arg = sys.argv[index]
    if arg in {'m', 'minimize', '-m', '--minimize'}:
        action = minimize
        index += 1
    elif arg in {'p', 'pretty', '-p', '--pretty'}:
        action = pretty
        index += 1
    elif arg in {'l', 'lint', '-l', '--lint'}:
        index += 1
    for filename in sys.argv[index:]:
        action(filename)

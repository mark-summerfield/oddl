#!/usr/bin/env python3
# Copyright © 2021 Mark Summerfield. All rights reserved.
# License: GPLv3

import enum
import re

__all__ = () # TODO
__version__ = '0.1.1'


class Parser:

    def __init__(self, text=None):
        if text:
            self.parse(text)
        else:
            self.clear()


    def clear(self):
        self.state = State.WANT_STRUCTURE
        self.globals = {} # NOTE or set?
        self.structures = []
        self.text = ''
        self.pos = 0
        self.lino = 1


    def parse(self, text):
        # file ::= structure*
        self.clear()
        self.text = text
        while self.pos < len(self.text):
            self.read_structure()


    def read_structure(self):
        # structure ::=
        #   data-type (name? "{" data-list? "}"
        #              | "[" integer-literal "]" "*"? name?
        #                "{" data-array-list? "}")
        #   |
        #   identifier name? ("(" (property ("," property)*)? ")")?
        #                     "{" structure* "}"
        text = self.text[self.pos:]
        match = DATA_TYPE_RX.match(text)
        if match is not None:
            typename = match.group(0)
            self.structures.append(Structure(typename))
            self.pos += len(typename)
            self.read_primitive_structure_data()
            return
        match = RESERVED_STRUCTURE_ID_RX.match(text)
        if match is not None:
            self.error(match.group(0)) # Does not return
        match = ID_RX.match(text)
        if match is not None:
            typename = match.group(0)
            self.structures.append(Structure(typename))
            self.pos += len(typename)
            self.read_derived_structure_data()
            return
        self.error('failed to find a primitive or derived structure')


    def read_primitive_structure_data(self):
        pass # TODO


    def read_derived_structure_data(self):
        pass # TODO


    def error(self, text):
        raise Error(f'error [{self.lino}.{self.pos}]: {text:r}')


class Error(Exception):
    pass


class Structure:

    def __init__(self, typename):
        self.typename = typename


class PrimitiveStructure(Structure):
    pass


class DerivedStructure(Structure):
    pass


@enum.unique
class State(enum.Enum):
    WANT_STRUCTURE = 1


RESERVED_STRUCTURE_ID_RX = re.compile(r'[a-z]\d*')
DATA_TYPE_RX = re.compile(
    r'(?:b|base64|bool|d|double|f|f16|f32|f64|float|float16|float32|'
    r'float64|h|half|i16|i32|i64|i8|int16|int32|int64|int8|r|ref|s|string|'
    r't|type|u16|u32|u64|u8|uint16|uint32|uint64|uint8|z)')
ID_RX = re.compile(r'[A-Za-z_][0-9A-Za-z_]*')


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

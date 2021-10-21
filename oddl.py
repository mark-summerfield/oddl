#!/usr/bin/env python3
# Copyright © 2021 Mark Summerfield. All rights reserved.
# License: GPLv3

import io
import re
import sys

__version__ = '0.1.1'


def check(filename):
    oddl = Oddl(filename)
    oddl.check()


class Oddl:

    def __init__(self, filename=None):
        self.clear()
        if filename is not None:
            self.filename = filename
            self.load()


    def clear(self):
        self.globals = {} # NOTE or set?
        self.structures = []


    def load(self, filename=None):
        filename = filename or self.filename
        with open(filename, 'rt', encoding='utf-8') as file:
            self.loads(file.read())


    def loads(self, text):
        parser = _Parser(self)
        parser.parse(text)


    def save(self, filename=None):
        filename = filename or self.filename
        with open(filename, 'wt', encoding='utf-8') as file:
            self.write(file)


    dump = save


    def dumps(self):
        out = io.StringIO()
        try:
            self.write(out)
            return out.getvalue()
        finally:
            out.close()


    def write(self, out):
        pass # TODO


    def _debug(self):
        # TODO delete
        for i, structure in enumerate(self.structures):
            print(f'#{i}: {structure.__class__.__name__} '
                  f'{vars(structure)}\n')


    def check(self):
        pass  # TODO


    lint = check


class Structure:

    def __init__(self, typename):
        self.typename = typename # built-in or user-defined identifier


class PrimitiveStructure(Structure):
    pass


class DerivedStructure(Structure):
    pass


class _Parser:

    def __init__(self, oddl):
        self.oddl = oddl
        self.clear()


    def clear(self):
        self.oddl.clear()
        self.text = ''
        self.pos = 0
        self.lino = 1


    def parse(self, text):
        # file ::= structure*
        self.clear()
        self.text = text.rstrip()
        while self.pos < len(self.text):
            self.parse_structure()


    def parse_structure(self):
        # structure ::=
        #   data-type (name? "{" data-list? "}"
        #              | "[" integer-literal "]" "*"? name?
        #                "{" data-array-list? "}")
        #   |
        #   identifier name? ("(" (property ("," property)*)? ")")?
        #                     "{" structure* "}"
        self.wsc()
        text = self.text[self.pos:]
        match = _DATA_TYPE_RX.match(text)
        if match is not None:
            typename = match[0]
            self.pos += len(typename)
            self.oddl.structures.append(PrimitiveStructure(typename))
            self.parse_primitive_structure_data()
        else:
            match = _RESERVED_STRUCTURE_ID_RX.match(text)
            if match is not None:
                self.error(f'illegal structure name {match[0]}')
            match = _ID_RX.match(text)
            if match is not None:
                typename = match[0]
                self.pos += len(typename)
                self.oddl.structures.append(DerivedStructure(typename))
                self.parse_derived_structure_data()
            else:
                self.error('primitive or derived structure expected')


    def parse_primitive_structure_data(self):
        # name? "{" data-list? "}"
        # |
        # "[" integer-literal "]" "*"? name? "{" data-array-list? "}"
        self.wsc()
        pass # TODO


    def parse_derived_structure_data(self):
        # name? ("(" (property ("," property)*)? ")")? "{" structure* "}"
        self.wsc()
        pass # TODO


    def wsc(self):
        text = self.text[self.pos:]
        match = _WS_RX.match(text)
        if match is not None:
            ws = match[0]
            self.lino = ws.count('\n')
            self.pos += len(ws)
            text = self.text[self.pos:]
        if text.startswith('//'):
            i = self.text.find('\n', self.pos)
            if i == -1:
                self.pos = len(self.text)
                self.warning('comment but no newline at the end')
                return
            self.lino += 1
            self.pos = i + 1
            self.wsc() # if the next line starts with whitespace or comment
        elif text.startswith('/*'):
            i = self.text.find('*/', self.pos)
            self.lino += self.text.count('\n', self.pos, i)
            self.pos = i + 1
            self.wsc() # if the next line starts with whitespace or comment


    def error(self, message):
        self.oddl._debug() # TODO delete
        raise Error(f'error [{self.lino}.{self.pos}]: {message!r}')


    def warning(self, message):
        print(f'warning [{self.lino}.{self.pos}]: {message!r}',
              file=sys.stderr)


class Error(Exception):
    pass


_RESERVED_STRUCTURE_ID_RX = re.compile(r'[a-z]\d*')
_DATA_TYPE_RX = re.compile(
    r'(?:b|base64|bool|d|double|f|f16|f32|f64|float|float16|float32|'
    r'float64|h|half|i16|i32|i64|i8|int16|int32|int64|int8|r|ref|s|string|'
    r't|type|u16|u32|u64|u8|uint16|uint32|uint64|uint8|z)')
_ID_RX = re.compile(r'[A-Za-z_][0-9A-Za-z_]*')
_WS_RX = re.compile(r'[\s\n]+', re.DOTALL | re.MULTILINE)


if __name__ == '__main__':
    import pathlib

    if len(sys.argv) == 1 or sys.argv[1] in {'h', 'help', '-h', '--help'}:
        raise SystemExit(f'''\
usage: {pathlib.Path(sys.argv[0]).name} \
[check] <file1.oddl> [<file2.oddl> [... <fileN.oddl>]]
 -or-: {pathlib.Path(sys.argv[0]).name} help

h help         : show this usage and quit.
l lint c check : check each .oddl file and report any problems (this is the
                 default action).

Letter options may be prefixed by - and word options by -- e.g., -l or \
--lint
''')
    args = sys.argv[1:]
    if args[0] in {'l', 'lint', '-l', '--lint', 'c', 'check', '-c',
                   '--check'}:
        args = args[1:]
    for filename in args:
        check(filename)

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
        self.global_names = set()
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
        self.name = None


class PrimitiveStructure(Structure):
    pass


class DerivedStructure(Structure):

    def __init__(self, typename):
        super().__init__(typename)
        self.structures = []


class _Parser:

    def __init__(self, oddl):
        self.oddl = oddl
        self.clear()


    def clear(self):
        self.oddl.clear()
        self.text = ''
        self.pos = 0
        self.lino = 1
        self.structures = [self.oddl.structures]


    def parse(self, text):
        # file ::= structure*
        self.clear()
        self.text = text.rstrip()
        while self.pos < len(self.text):
            self.parse_structure(optional=True)


    def parse_structure(self, *, optional=False):
        # structure ::=
        #   data-type (name? "{" data-list? "}"
        #              | "[" integer-literal "]" "*"? name?
        #                "{" data-array-list? "}")
        #   |
        #   identifier name? ("(" (property ("," property)*)? ")")?
        #                     "{" structure* "}"
        text = self.advance(optional, 'structure expected')
        if not text:
            return
        match = _DATA_TYPE_RX.match(text)
        if match is not None:
            typename = match[0]
            self.pos += len(typename)
            # Append to current structure's list of structures
            self.structures[-1].append(PrimitiveStructure(typename))
            self.parse_primitive_structure_content()
        else:
            match = _RESERVED_STRUCTURE_ID_RX.match(text)
            if match is not None:
                self.error(f'illegal structure name {match[0]}')
            match = _ID_RX.match(text)
            if match is not None:
                typename = match[0]
                self.pos += len(typename)
                # Append to current structure's list of structures and make
                # this structure the new current structure when parsing its
                # content since DerivedStructures can nest
                structure = DerivedStructure(typename)
                self.structures[-1].append(structure)
                self.structures.append(structure.structures)
                self.parse_derived_structure_content()
                self.structures.pop()
            else:
                self.error('primitive or derived structure expected')


    def parse_primitive_structure_content(self, *, optional=False):
        # "[" integer-literal "]" "*"? name? "{" data-array-list? "}"
        # |
        # name? "{" data-list? "}"
        text = self.advance(optional,
                            'expected primitive structure content')
        if not text:
            return
        if text[0] == '[':
            text = self.expected('[')
            # TODO parse_int ...
            # if text[0] != ']':
            #   self.error(...)
            # optional star
            # name = self.parse_name(optional=True)
            # if name:
            #   pass # where does this name go?
            # text = self.expected('{')
            # parse optional data-array-list
            # self.expected('}')
        else:
            name = self.parse_name(optional=True)
            if name:
                self.structures[-1].name = name
            # text = self.expected('{')
            # TODO parse_data_list(optional=True)
            # self.expected('}')


    def parse_derived_structure_content(self, *, optional=False):
        # name? ("(" (property ("," property)*)? ")")? "{" structure* "}"
        text = self.advance(optional, 'expected derived structure content')
        if not text:
            return
        name = self.parse_name(optional=True)
        if name:
            self.structures[-1].name = name
        # TODO
        # parse_properties(optional=True)
        # text = self.expected('{')
        # while self.pos < len(self.text):
        #   self.parse_structure(optional=True)
        # self.expected('}')


    def parse_name(self, *, optional=False):
        text = self.advance(optional, 'expected name')
        if not text:
            return
        match = _NAME_RX.match(text)
        if match is None:
            if optional:
                return
            self.error('expected name')
        name = match[0]
        self.pos += len(name)
        return name


    def expected(self, what):
        self.skip_ws_and_comments()
        text = self.text[self.pos:]
        if not text or not text.startswith(what):
            self.error(f'expected {what!r}')
        self.pos += len(what)
        return self.text[self.pos:]


    def advance(self, optional, message):
        self.skip_ws_and_comments()
        text = self.text[self.pos:]
        if not text and not optional:
            self.error(message)
        return text


    def skip_ws_and_comments(self):
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
            self.skip_ws_and_comments() # for the next line...
        elif text.startswith('/*'):
            i = self.text.find('*/', self.pos)
            self.lino += self.text.count('\n', self.pos, i)
            self.pos = i + 1
            self.skip_ws_and_comments() # for the next line...


    def error(self, message):
        self.oddl._debug() # TODO delete
        raise Error(f'error [{self.lino}.{self.pos}]: {message!r}')


    def warning(self, message):
        print(f'warning [{self.lino}.{self.pos}]: {message!r}',
              file=sys.stderr)


class Error(Exception):
    pass


_RESERVED_STRUCTURE_ID_RX = re.compile(r'[a-z]\d*')
_DATA_TYPE_RX = re.compile( # Must be ordered longest to shortest
    r'(:?float16|float32|float64|base64|uint16|uint32|uint64|string|double|'
    r'float|int16|int32|int64|uint8|int8|bool|half|type|f16|u32|u64|f32|'
    r'f64|i16|i32|i64|u16|ref|i8|u8|b|d|f|h|r|s|t|z)')
_ID_RX = re.compile(r'[A-Za-z_][0-9A-Za-z_]*')
_NAME_RX = re.compile(r'[%$][A-Za-z_][0-9A-Za-z_]*')
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

#!/usr/bin/env python3
# Copyright © 2021 Mark Summerfield. All rights reserved.
# License: GPLv3

import base64
import io
import re
import sys

__all__ = ('Oddl',)
__version__ = '0.1.1'


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
        parser = Parser(self)
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


    def __repr__(self): # TODO this is used for debugging right now
        parts = []
        for i, structure in enumerate(self.structures):
            parts.append(f'#{i}: {structure}')
        return '\n'.join(parts)


    def check(self):
        pass  # TODO


    lint = check


class Base64Data(bytes):

    def __new__(Class, value):
        message = ''
        match = BASE64_DATA_RX.fullmatch(value)
        if match is not None:
            try:
                return super().__new__(Class, base64.b64decode(
                                       match[0].encode('utf-8')))
            except base64.Error as err:
                message = f' {err}'
        raise Error(f'invalid base-64-data{message}: {value!r}')


class DataType(str):

    def __new__(Class, value):
        match = DATA_TYPE_RX.fullmatch(value)
        if match is not None:
            return super().__new__(Class, match[0])
        raise Error(f'invalid data-type: {value!r}')


class Name(str):

    def __new__(Class, value):
        match = NAME_RX.fullmatch(value)
        if match is not None:
            return super().__new__(Class, match[0])
        raise Error(f'invalid name: {value!r}')


class Reference(str):

    def __new__(Class, value):
        match = REFERENCE_RX.fullmatch(value)
        if match is not None:
            return super().__new__(Class, match[0])
        raise Error(f'invalid reference: {value!r}')


    @property
    def isnull(self):
        return self == 'null'


class Structure:

    def __init__(self, typename):
        self.typename = typename # built-in or user-defined identifier
        self.name = None


    def __repr__(self): # TODO this is used for debugging right now
        return (f'{self.__class__.__name__}({self.typename}) '
                f'name={self.name}')


class PrimitiveStructure(Structure):
    pass


class DerivedStructure(Structure):

    def __init__(self, typename):
        super().__init__(typename)
        self.structures = []
        self.properties = {}


    def __repr__(self): # TODO this is used for debugging right now
        parts = [super().__repr__(), 'structures=[']
        for structure in self.structures:
            parts.append(repr(structure))
        parts += [']', f'properties={self.properties}']
        return '\n'.join(parts)


class Parser:

    def __init__(self, oddl):
        self.oddl = oddl
        self.clear()


    def clear(self):
        self.oddl.clear()
        self.text = ''
        self.pos = 0
        self.lino = 1
        self.stack = [self.oddl]


    @property
    def current(self):
        return self.stack[-1]


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
        match = DATA_TYPE_RX.match(text)
        if match is not None:
            typename = match[0]
            self.pos += len(typename)
            # Append to current structure's list of structures
            self.current.structures.append(PrimitiveStructure(typename))
            self.parse_primitive_structure_content()
        else:
            match = RESERVED_STRUCTURE_ID_RX.match(text)
            if match is not None:
                self.error(f'illegal structure name {match[0]}')
            match = ID_RX.match(text)
            if match is not None:
                typename = match[0]
                self.pos += len(typename)
                # Append to current structure's list of structures and make
                # this structure the new current structure when parsing its
                # content since DerivedStructures can nest
                structure = DerivedStructure(typename)
                self.current.structures.append(structure)
                self.stack.append(structure)
                self.parse_derived_structure_content()
                self.stack.pop()
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
            text = self.expect('[')
            # TODO parse_int ...
            # if text[0] != ']':
            #   self.error(...)
            # optional star
            # name = self.parse_name(optional=True)
            # if name:
            #   pass # where does this name go?
            # text = self.expect('{')
            # parse optional data-array-list
            # self.expect('}')
        else:
            name = self.parse_name(optional=True)
            if name:
                self.current.name = name
            # text = self.expect('{')
            # TODO parse_data_list(optional=True)
            # self.expect('}')


    def parse_derived_structure_content(self, *, optional=False):
        # name? ("(" (property ("," property)*)? ")")? "{" structure* "}"
        text = self.advance(optional, 'expected derived structure content')
        if not text:
            return
        name = self.parse_name(optional=True)
        if name:
            self.current.name = name
        self.parse_property_list(optional=True)
        text = self.expect('{')
        while self.pos < len(self.text):
            self.parse_structure(optional=True)
        self.expect('}')


    def parse_name(self, *, optional=False):
        text = self.advance(optional, 'expected name')
        if not text:
            return
        match = NAME_RX.match(text)
        if match is None:
            if optional:
                return
            self.error('expected name')
        name = match[0]
        self.pos += len(name)
        return name


    def parse_property_list(self, *, optional=False):
        text = self.advance(optional, 'expected one or more properties')
        if not text:
            if optional:
                return
            self.error('expected one or more properties')
        if text[0] == '(':
            self.pos += 1
            text = text[1:]
            i = text.find(')', 1)
            if i == -1:
                self.error('property list missing closing \')\'')
            for prop in (p.strip() for p in text[:i].split(',')):
                prop = prop.split('=', 1)
                name = prop[0].strip()
                value = (self.parse_property_value(prop[1])
                         if len(prop) == 2 else True)
                self.current.properties[name] = value
            self.pos += i
            self.expect(')')
        elif not optional:
            self.error('expected \'(\' to begin property list')


    def parse_property_value(self, value):
        # (bool-literal | integer-literal | float-literal | string-literal |
        # reference | data-type | base64-data)
        return self.parse_value(value, {bool, int, float, str, Reference,
                                        DataType, Base64Data}, 'property')


    def parse_value(self, value, types, what=''):
        value = value.strip()
        if str in types and value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        if bool in types:
            if value == 'false':
                return False
            if value == 'true':
                return True
        for Class in (int, float, Base64Data, DataType, Name, Reference):
            if Class in types:
                try:
                    return Class(value)
                except (ValueError, Error):
                    pass # may be another type
        what = f' {what}' if what else ''
        self.error(f'invalid{what} value: {value!r}')


    def expect(self, what):
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
        match = WS_RX.match(text)
        if match is not None:
            ws = match[0]
            self.lino += ws.count('\n')
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
        print(self.oddl) # TODO delete
        raise Error(f'error [{self.lino}.{self.column}]: {message!r}')


    def warning(self, message):
        print(f'warning [{self.lino}.{self.column}]: {message!r}',
              file=sys.stderr)


    @property
    def column(self):
        if self.lino == 1:
            j = -1
        else:
            i = j = self.text.find('\n')
            while True:
                i = self.text.find('\n', i + 1)
                if i == -1 or i > self.pos:
                    break
                j = i - 1
        return self.pos - j


class Error(Exception):
    pass


RESERVED_STRUCTURE_ID_RX = re.compile(r'[a-z]\d*')
DATA_TYPE_RX = re.compile( # NOTE Must be ordered longest to shortest
    r'(:?float16|float32|float64|base64|uint16|uint32|uint64|string|double|'
    r'float|int16|int32|int64|uint8|int8|bool|half|type|f16|u32|u64|f32|'
    r'f64|i16|i32|i64|u16|ref|i8|u8|b|d|f|h|r|s|t|z)')
ID_RX = re.compile(r'[A-Za-z_][0-9A-Za-z_]*')
NAME_RX = re.compile(r'[%$][A-Za-z_][0-9A-Za-z_]*')
REFERENCE_RX = re.compile(
    r'null|[%$][A-Za-z_][0-9A-Za-z_]*(?:%[A-Za-z_][0-9A-Za-z_]*)*')
WS_RX = re.compile(r'[\s\n]+', re.DOTALL | re.MULTILINE)
BASE64_DATA_RX = re.compile(
    r'[A-Za-z0-9][A-Za-z0-9][+/\s\nA-Za-z0-9]*={0,2}',
    re.DOTALL | re.MULTILINE)


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
        Oddl(filename).check()

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
        for structure in self.structures:
            structure.write(out, '')


    def check(self):
        pass  # TODO


    lint = check


class Base64Data(bytes):

    __slots__ = ()

    REGEX = re.compile(
        r'[A-Za-z0-9][A-Za-z0-9][+/\s\nA-Za-z0-9]*={0,2}',
        re.DOTALL | re.MULTILINE)

    def __new__(Class, value):
        message = ''
        match = Class.REGEX.fullmatch(value)
        if match is not None:
            try:
                return super().__new__(Class, base64.b64decode(
                                       match[0].encode('utf-8')))
            except base64.Error as err:
                message = f' {err}'
        raise Error(f'invalid base-64-data{message}: {value!r}')


    def write(self, out):
        out.write(base64.b64encode(self).decode('ascii'))


class DataType(str):

    __slots__ = ()

    REGEX = re.compile( # NOTE Must be ordered longest to shortest
        r'(:?float16|float32|float64|base64|uint16|uint32|uint64|string|'
        r'double|float|int16|int32|int64|uint8|int8|bool|half|type|f16|'
        r'u32|u64|f32|f64|i16|i32|i64|u16|ref|i8|u8|b|d|f|h|r|s|t|z)')

    NAME_FOR_NAME = { # prefer shortest, but for float prefer most sensible
        'base64': 'z',
        'bool': 'b',
        'double': 'f64',
        'float': 'f32',
        'float16': 'f16',
        'float32': 'f32',
        'float64': 'f64',
        'half': 'f16',
        'int16': 'i16',
        'int32': 'i32',
        'int64': 'i64',
        'int8': 'i8',
        'ref': 'r',
        'string': 's',
        'type': 't',
        'uint16': 'u16',
        'uint32': 'u32',
        'uint64': 'u64',
        'uint8': 'u8'}

    def __new__(Class, value):
        match = Class.REGEX.fullmatch(value)
        if match is not None:
            return super().__new__(Class, Class.NAME_FOR_NAME[match[0]])
        raise Error(f'invalid data-type: {value!r}')


    def write(self, out):
        out.write(self)


class Reference(str):

    __slots__ = ()

    REGEX = re.compile(
        r'null|[%$][A-Za-z_][0-9A-Za-z_]*(?:%[A-Za-z_][0-9A-Za-z_]*)*')

    def __new__(Class, value):
        match = Class.REGEX.fullmatch(value)
        if match is not None:
            return super().__new__(Class, match[0])
        raise Error(f'invalid reference: {value!r}')


    @property
    def isnull(self):
        return self == 'null'


    def write(self, out):
        out.write(self)


class Int(int):

    __slots__ = ()

    def write(self, out):
        out.write(str(self))


class Real(float):

    __slots__ = ()

    def write(self, out):
        out.write(f'{self:g}')


class String(str):

    __slots__ = ()

    TRANS_TABLE = str.maketrans({'"': '\\"', '\\': '\\\\', '\a': '\\a',
                                 '\b': '\\b', '\f': '\\f', '\n': '\\n',
                                 '\r': '\\r', '\t': '\\t', '\v': '\\v'})

    def write(self, out):
        out.write(f'"{self.translate(self.TRANS_TABLE)}"')


class Structure:

    def __init__(self, datatype):
        self.datatype = datatype # built-in or user-defined identifier
        self.name = None


    def write(self, _out, _indent):
        raise NotImplementedError


class PrimitiveStructure(Structure):

    def write(self, out, indent):
        out.write(f'{indent}{self.datatype}')
        if self.name is not None:
            out.write(f' {self.name}')
        out.write('\n')
        # TODO


class DerivedStructure(Structure):

    def __init__(self, datatype):
        super().__init__(datatype)
        self.structures = []
        self.properties = {}


    def write(self, out, indent):
        out.write(f'{indent}{self.datatype}')
        if self.name is not None:
            out.write(f' {self.name}')
        self.write_properties(out)
        out.write('\n')
        if self.structures:
            out.write(f'{indent}{{\n')
            for structure in self.structures:
                structure.write(out, indent + TAB)
            out.write(f'{indent}}}\n')


    def write_properties(self, out):
        if self.properties:
            out.write(' (')
            sep = ''
            for name, value in self.properties.items():
                out.write(f'{sep}{name} = ')
                if value is True:
                    out.write('true')
                elif value is False:
                    out.write('false')
                else:
                    value.write(out)
                sep = ', '
            out.write(')')


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
        value = self.parse_value(DataType)
        if value is not None:
            # Append to current structure's list of structures
            self.current.structures.append(PrimitiveStructure(value))
            self.parse_primitive_structure_content()
        else:
            match = RESERVED_STRUCTURE_ID_RX.match(text)
            if match is not None:
                self.error(f'illegal structure name {match[0]}')
            match = ID_RX.match(text)
            if match is not None:
                datatype = match[0]
                self.pos += len(datatype)
                # Append to current structure's list of structures and make
                # this structure the new current structure when parsing its
                # content since DerivedStructures can nest
                structure = DerivedStructure(datatype)
                self.current.structures.append(structure)
                self.stack.append(structure)
                self.parse_derived_structure_content()
                self.stack.pop()
            else:
                self.error('primitive or derived structure expected')


    # TODO #######################
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
            count = 0
            while True:
                if not self.parse_property():
                    if count == 0:
                        self.error('at least one property expected')
                    break
                count += 1
        elif not optional:
            self.error('expected \'(\' to begin property list')


    def parse_property(self):
        text = self.advance(False, 'property expected')
        if text.startswith(')'):
            self.pos += 1
            return False # no more
        match = ID_RX.match(text)
        if match is None:
            self.error('property expected')
        name = match[0]
        self.pos += len(name)
        text = text[len(name):]
        self.current.properties[name] = True # assume bool
        while text:
            c = text[0]
            self.pos += 1
            text = text[1:]
            if c.isspace():
                continue
            elif c == ')':
                return False # no more
            elif c == ',':
                break # just had a bool property; another to follow
            elif c == '=':
                text = self.advance(False,
                                    'property value expected')
                self.parse_property_value(name)
                break
            else:
                self.error('property value expected')
        return True # maybe more


    def parse_property_value(self, name):
        # (bool-literal | integer-literal | float-literal | string-literal |
        # reference | data-type | base64-data)
        text = self.text[self.pos:]
        original = text[:20]
        value = None
        if text.startswith('"'):
            value = self.parse_string()
        elif text.startswith(('$', '%')):
            value = self.parse_value(Reference)
            if value is None:
                self.error('invalid reference')
        elif text.startswith('false'):
            value = False
            self.pos += len('false')
        elif text.startswith('true'):
            value = True
            self.pos += len('true')
        else:
            value = self.parse_value(DataType)
            if value is None:
                value = self.parse_value(Base64Data)
                if value is None:
                    value = self.parse_number()
        if value is None:
            self.error(f'invalid property {name} value: {original!r}...')
        self.current.properties[name] = value


    def parse_string(self):
        assert self.text[self.pos] == '"', 'expected \'"\' to start string'
        chars = []
        prev = ''
        self.pos += 1 # skip opening "
        text = self.text[self.pos:]
        while text:
            c = text[0]
            self.pos += 1
            text = text[1:]
            if c == '"':
                if prev == '\\':
                    prev = ''
                else: # end of string
                    return String(''.join(chars))
            elif c == '\\':
                if prev == '\\':
                    prev = ''
                else:
                    prev = c
                    continue
            elif prev == '\\':
                prev = ''
                if c in '\'?abfnrtv':
                    c = CHAR_FOR_LITERAL[c]
                elif c in 'xuU':
                    n = '2' if c == 'x' else ('4' if c == 'u' else '6')
                    match = re.match(HEX_PATTERN + '{' + n + '}')
                    if match is not None:
                        h = match[0]
                        self.pos += len(h)
                        text = text[len(h):]
                        c = chr(int(h, 16))
                    else:
                        self.error(
                            f'expected {n} hex digits not {text[:n]!r}')
                else:
                    self.warning(f'needlessly escaped \'{c}\'')
            chars.append(c)
        self.error('expected \'"\' at end of string')


    def parse_value(self, Class):
        match = Class.REGEX.match(self.text[self.pos:])
        if match is not None:
            value = match[0]
            self.pos += len(value)
            return Class(value)


    def parse_number(self):
        text = self.text[self.pos:]
        if text.startswith("'"): # char-literal
            return self.parse_char_literal_as_number(text)
        match = NUMBER_RX.match(self.text[self.pos:])
        if match is not None:
            value = match[0]
            self.pos += len(value)
            if len(value) > 2 and value[1] in 'bBoOxX':
                kind = value[1]
                radix = 2 if kind in 'bB' else (8 if kind in 'oO' else 16)
                return int(value[2:], radix)
            return Real(value) if '.' in value else Int(value)


    def parse_char_literal_as_number(self, text):
        assert text.startswith("'"), 'expected char-literal'
        j = text.find("'", 1)
        if j == -1:
            self.error('expected closing "\'" for char-literal')
        c = text[1:j] # ignore enclosing 's
        self.pos += j + 1 # skip past closing '
        if len(c) == 4 and c.startswith('\\x'):
            match = re.match(HEX_PATTERN + '{2}', c[2:])
            if match is not None:
                return int(match[0], 16)
            self.error(f'invalid hex char: {c!r}')
        if len(c) == 2 and c[0] == '\\':
            c = CHAR_FOR_LITERAL.get(c[1], c[1])
        if c is not None and len(c) == 1:
            return Int(ord(c))
        self.error('invalid char-literal')


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
        self.oddl.write(sys.stdout) # TODO delete
        file = f' {self.oddl.filename!r}' if self.oddl.filename else ''
        raise Error(
            f'ERROR:{file} [{self.lino}.{self.column}]: {message!r}')


    def warning(self, message):
        file = f' {self.oddl.filename!r}' if self.oddl.filename else ''
        print(f'Warning:{file} [{self.lino}.{self.column}]: {message!r}',
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


RESERVED_STRUCTURE_ID_RX = re.compile(r'[a-z][0-9]*')
ID_RX = re.compile(r'[A-Za-z_][0-9A-Za-z_]*')
NAME_RX = re.compile(r'[%$][A-Za-z_][0-9A-Za-z_]*')
WS_RX = re.compile(r'[\s\n]+', re.DOTALL | re.MULTILINE)
HEX_PATTERN = '[A-Fa-z[0-9]]'
NUMBER_RX = re.compile( # does _not_ handle char-literal's
    r'[-+]?(?:' # order: letters first then longest to shortest
    r'0[bB][01](?:_?[01])*|' # binary-literal
    r'0[oO][0-7](?:_?[0-7])*|' # octal-literal
    r'0[xX][A-Fa-f0-9](?:_?[A-Fa-f0-9])*|' # hex-literal / float-literal
    r'(?:[0-9](?:_?[0-9])*(?:\.[0-9](?:_?[0-9])*)?|\.[0-9](?:_?[0-9])*)'
    r'(?:(?:[eE][-+]?[0-9])?(:?_?[0-9])*)?|' # optional exponent
    r'[0-9](?:_?[0-9])*' # decimal-literal
    r')') # must use [0-9] rather than \d because \d is broader
CHAR_FOR_LITERAL = {"'": "'", '?': '?', 'a': '\a', 'b': '\b', 'f': '\f',
                    'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}
TAB = '    '


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
f format       : resave each .oddl file reformatted with indentation and
                 newlines to produce a regularized human-readable file (with
                 comments stripped and all numbers in base 10).

Letter options may be prefixed by - and word options by -- e.g., -l or \
--format.
''')
    args = sys.argv[1:]
    arg = args[0]
    action = None
    if arg in {'l', 'lint', '-l', '--lint', 'c', 'check', '-c', '--check'}:
        action = 'lint'
    elif arg in {'f', 'format', '-f', '--format'}:
        action = 'format'
    if action is None:
        action = 'lint'
    else:
        args = args[1:]
    for filename in args:
        print('\n' + f' {filename} '.center(72, '@'))
        try:
            oddl = Oddl(filename)
            if action == 'lint':
                oddl.check()
            else:
                oddl.save()
        except Error as err:
            print(err)

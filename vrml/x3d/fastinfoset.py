"""Fast Infoset documents (ITU-T X.891 | ISO/IEC 24824-1) as XML events

`events(data, vocabularies)` reads a Fast Infoset document and yields what
an XML parser would report of it, in document order:

- ``('start', name, attributes)``, attributes a list of ``(name, value)``;
- ``('end', name)``;
- ``('text', text, cdata)``, one character chunk;
- ``('comment', text)`` and ``('pi', target, content)``.

A value or chunk given by an encoding algorithm arrives as that algorithm's
result: a NumPy array for the numeric ones, a list of bools for boolean,
text for the rest, and an `Undecoded` where the vocabulary has no decoder
for the algorithm. A name is ``prefix:local`` where it has a prefix. A name
whose vocabulary entry is not known (`Vocabulary` entries may be None) is
None.

The bit layouts are those of X.891 Annex C, with the clause numbers below;
`specs/x3d/fast-infoset.md` gathers them. A document names its external
vocabulary by URI, and `vocabularies` maps each URI this reader knows to a
function making a fresh `Vocabulary`, since a document's tables grow as it
is read. A document that breaks the encoding raises `FastInfosetError`.
"""

import base64
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

__all__ = [
    'FastInfosetError', 'Undecoded', 'Vocabulary', 'events', 'BUILTIN_ALGORITHMS', 'MAGIC',
]

#: The identification and version every document starts with (12.6, 12.7).
MAGIC = b'\xe0\x00\x00\x01'

#: The XML declarations a document may begin with (12.3).
DECLARATIONS = tuple(
    ("<?xml %sencoding='finf'%s?>" % (version, standalone)).encode('ascii')
    for version in ('', "version='1.0' ", "version='1.1' ")
    for standalone in ('', " standalone='yes'", " standalone='no'")
)

#: The largest index or count any table may reach (7.2.18).
TABLE_LIMIT = 2 ** 20

Event = tuple


class FastInfosetError(ValueError):
    """A document that does not follow the Fast Infoset encoding"""


def _hexadecimal(octets: bytes) -> str:
    return octets.hex().upper()


def _base64(octets: bytes) -> str:
    return base64.b64encode(octets).decode('ascii')


def _numbers(code: str, size: int) -> Callable[[bytes], Any]:
    def decode(octets: bytes) -> Any:
        if len(octets) % size:
            raise FastInfosetError('%d octets are not whole %d-octet values'
                                   % (len(octets), size))
        return np.frombuffer(octets, dtype='>' + code).astype(code)
    return decode


def _booleans(octets: bytes) -> "list[bool]":
    """10.7: the first four bits count the unused bits of the last octet"""
    if not octets:
        raise FastInfosetError('An empty boolean value')
    unused = octets[0] >> 4
    count = 8 * len(octets) - 4 - unused
    if unused > 7 or count < 0:
        raise FastInfosetError('A boolean value with %d unused bits' % unused)
    bits = np.unpackbits(np.frombuffer(octets, dtype=np.uint8))[4:4 + count]
    return [bool(bit) for bit in bits]


def _uuids(octets: bytes) -> str:
    if len(octets) % 16:
        raise FastInfosetError('%d octets are not whole UUIDs' % len(octets))
    words = []
    for start in range(0, len(octets), 16):
        text = octets[start:start + 16].hex()
        words.append('-'.join((text[:8], text[8:12], text[12:16], text[16:20], text[20:])))
    return ' '.join(words)


def _cdata(octets: bytes) -> str:
    return octets.decode('utf-8')


#: The encoding algorithms of X.891 clause 10, by table index.
BUILTIN_ALGORITHMS: "dict[int, Callable[[bytes], Any]]" = {
    1: _hexadecimal,
    2: _base64,
    3: _numbers('i2', 2),
    4: _numbers('i4', 4),
    5: _numbers('i8', 8),
    6: _booleans,
    7: _numbers('f4', 4),
    8: _numbers('f8', 8),
    9: _uuids,
    10: _cdata,
}

#: The algorithm whose strings are CDATA sections (10.11).
CDATA_ALGORITHM = 10

#: The restricted alphabets of X.891 clause 9, by table index.
BUILTIN_ALPHABETS = {1: '0123456789-+.e ', 2: '0123456789-:TZ '}


@dataclass(frozen=True)
class Undecoded:
    """A value in an encoding algorithm the vocabulary has no decoder for"""

    index: int
    name: str
    octets: bytes

    def __str__(self) -> str:
        return 'a value in encoding algorithm %d (%s), which is not read' % (
            self.index, self.name)


@dataclass
class Vocabulary:
    """The tables a document's indexes refer to (8.2-8.5), each from index 1

    Name tables hold the qualified name each surrogate stands for, or None
    where that entry is not known. `algorithms` and `alphabets` are keyed by
    table index, since those two tables number from fixed points (7.2.19,
    7.2.20); an algorithm's index may have no decoder, and `algorithm_names`
    says what such an index is called.
    """

    prefixes: "list[str]" = field(default_factory=lambda: ['xml'])
    namespace_names: "list[str]" = field(
        default_factory=lambda: ['http://www.w3.org/XML/1998/namespace'])
    local_names: "list[str]" = field(default_factory=list)
    other_ncnames: "list[str]" = field(default_factory=list)
    other_uris: "list[str]" = field(default_factory=list)
    attribute_values: "list[Any]" = field(default_factory=list)
    content_chunks: "list[Any]" = field(default_factory=list)
    other_strings: "list[Any]" = field(default_factory=list)
    element_names: "list[Optional[str]]" = field(default_factory=list)
    attribute_names: "list[Optional[str]]" = field(default_factory=list)
    algorithms: "dict[int, Callable[[bytes], Any]]" = field(
        default_factory=lambda: dict(BUILTIN_ALGORITHMS))
    algorithm_names: "dict[int, str]" = field(default_factory=dict)
    alphabets: "dict[int, str]" = field(default_factory=lambda: dict(BUILTIN_ALPHABETS))
    #: The index the document's own algorithms and alphabets start from.
    next_algorithm: int = 32
    next_alphabet: int = 16


def _entry(table: "list[Any]", index: int, what: str) -> Any:
    if not 0 < index <= len(table):
        raise FastInfosetError('%s index %d is past the table (%d entries)'
                               % (what, index, len(table)))
    return table[index - 1]


def _add(table: "list[Any]", value: Any) -> None:
    if len(table) >= TABLE_LIMIT:
        raise FastInfosetError('A vocabulary table is full')
    table.append(value)


def _qualified(prefix: Optional[str], local: str) -> str:
    return '%s:%s' % (prefix, local) if prefix else local


class _Decoder:
    """A cursor over the document's octets, reading each Annex C construct
    from the bit it starts on"""

    def __init__(self, data: bytes, vocabularies: "Mapping[str, Callable[[], Vocabulary]]") -> None:
        self.data = data
        self.position = 0
        self.vocabularies = vocabularies
        self.vocabulary = Vocabulary()
        #: Set when the document element's terminator and the document's
        #: share one octet (C.2.12).
        self.document_ended = False

    # Octets

    def octet(self) -> int:
        try:
            value = self.data[self.position]
        except IndexError:
            raise FastInfosetError('The document ends at octet %d' % self.position) from None
        self.position += 1
        return value

    def peek(self) -> int:
        try:
            return self.data[self.position]
        except IndexError:
            raise FastInfosetError('The document ends at octet %d' % self.position) from None

    def octets(self, count: int) -> bytes:
        end = self.position + count
        if end > len(self.data):
            raise FastInfosetError('%d octets wanted at %d, past the end' % (count, self.position))
        found = self.data[self.position:end]
        self.position = end
        return found

    def integer(self, count: int) -> int:
        return int.from_bytes(self.octets(count), 'big')

    # Integers and lengths (C.21-C.28)

    def sequence_length(self) -> int:
        """C.21, from bit 1"""
        first = self.octet()
        if not first & 0x80:
            return (first & 0x7F) + 1
        return ((first & 0x0F) << 16 | self.integer(2)) + 129

    def octet_string_length(self, first: int) -> int:
        """C.22, from bit 2 of `first`"""
        if not first & 0x40:
            return (first & 0x3F) + 1
        if not first & 0x20:
            return self.octet() + 65
        return self.integer(4) + 321

    def length_from_bit_5(self, first: int) -> int:
        """C.23"""
        if not first & 0x08:
            return (first & 0x07) + 1
        if not first & 0x04:
            return self.octet() + 9
        return self.integer(4) + 265

    def length_from_bit_7(self, first: int) -> int:
        """C.24"""
        if not first & 0x02:
            return (first & 0x01) + 1
        if not first & 0x01:
            return self.octet() + 3
        return self.integer(4) + 259

    def index_from_bit_2(self, first: int) -> int:
        """C.25, 1..2^20"""
        if not first & 0x40:
            return (first & 0x3F) + 1
        if not first & 0x20:
            return ((first & 0x1F) << 8 | self.octet()) + 65
        return ((first & 0x0F) << 16 | self.integer(2)) + 8257

    def index_from_bit_3(self, first: int) -> int:
        """C.27"""
        if not first & 0x20:
            return (first & 0x1F) + 1
        form = first & 0x38
        if form == 0x20:
            return ((first & 0x07) << 8 | self.octet()) + 33
        if form == 0x28:
            return ((first & 0x07) << 16 | self.integer(2)) + 2081
        if form == 0x30:
            return ((self.octet() & 0x0F) << 16 | self.integer(2)) + 526369
        raise FastInfosetError('Octet %#x is not an index' % first)

    def index_from_bit_4(self, first: int) -> int:
        """C.28"""
        if not first & 0x10:
            return (first & 0x0F) + 1
        form = first & 0x1C
        if form == 0x10:
            return ((first & 0x03) << 8 | self.octet()) + 17
        if form == 0x14:
            return ((first & 0x03) << 16 | self.integer(2)) + 1041
        if form == 0x18:
            return ((self.octet() & 0x0F) << 16 | self.integer(2)) + 263185
        raise FastInfosetError('Octet %#x is not an index' % first)

    # Strings (C.13-C.20)

    def utf8(self, octets: bytes) -> str:
        try:
            return octets.decode('utf-8')
        except UnicodeDecodeError as error:
            raise FastInfosetError('A string is not UTF-8: %s' % error) from None

    def literal_from_bit_2(self, first: int) -> str:
        """C.22 octet string, read as UTF-8"""
        return self.utf8(self.octets(self.octet_string_length(first)))

    def identifying(self, table: "list[Any]", what: str) -> str:
        """C.13, from bit 1: a literal, added to `table`, or an index into it"""
        first = self.octet()
        if first & 0x80:
            found: str = _entry(table, self.index_from_bit_2(first), what)
            return found
        text = self.literal_from_bit_2(first)
        _add(table, text)
        return text

    def encoded(self, discriminant: int, first: int, at_bit_5: bool) -> "tuple[Any, bool]":
        """An EncodedCharacterString's content once its format is known, and
        whether it is CDATA (C.19, C.20)"""
        length = self.length_from_bit_5 if at_bit_5 else self.length_from_bit_7
        if discriminant < 2:
            octets = self.octets(length(first))
            if discriminant == 0:
                return self.utf8(octets), False
            try:
                return octets.decode('utf-16-be'), False
            except UnicodeDecodeError as error:
                raise FastInfosetError('A string is not UTF-16: %s' % error) from None
        second = self.octet()
        if at_bit_5:
            index = ((first & 0x0F) << 4 | second >> 4) + 1
        else:
            index = ((first & 0x03) << 6 | second >> 2) + 1
        octets = self.octets(length(second))
        if discriminant == 2:
            return self.restricted(index, octets), False
        return self.algorithm(index, octets), index == CDATA_ALGORITHM

    def restricted(self, index: int, octets: bytes) -> str:
        """Characters of restricted alphabet `index` (7.17.6)"""
        alphabet = self.vocabulary.alphabets.get(index)
        if alphabet is None:
            raise FastInfosetError('Restricted alphabet %d is not in the vocabulary' % index)
        width = len(alphabet).bit_length()
        bits = np.unpackbits(np.frombuffer(octets, dtype=np.uint8))
        whole = len(bits) // width
        values = bits[:whole * width].reshape(whole, width) @ (1 << np.arange(width - 1, -1, -1))
        characters = []
        for value in values:
            if value >= len(alphabet):
                break
            characters.append(alphabet[value])
        return ''.join(characters)

    def algorithm(self, index: int, octets: bytes) -> Any:
        decode = self.vocabulary.algorithms.get(index)
        if decode is None:
            return Undecoded(index, self.vocabulary.algorithm_names.get(index, 'unnamed'), octets)
        return decode(octets)

    def non_identifying(self, table: "list[Any]", what: str) -> "tuple[Any, bool]":
        """C.14, from bit 1: a value and whether it is CDATA"""
        first = self.octet()
        if first & 0x80:
            if first == 0xFF:
                return '', False
            return _entry(table, self.index_from_bit_2(first), what), False
        value, cdata = self.encoded((first >> 4) & 0x03, first, at_bit_5=True)
        if first & 0x40:
            _add(table, value)
        return value, cdata

    def chunk(self, first: int) -> "tuple[Any, bool]":
        """C.15, from bit 3 of `first`"""
        table = self.vocabulary.content_chunks
        if first & 0x20:
            return _entry(table, self.index_from_bit_4(first), 'Character chunk'), False
        value, cdata = self.encoded((first >> 2) & 0x03, first, at_bit_5=False)
        if first & 0x10:
            _add(table, value)
        return value, cdata

    def qualified_name(self, first: int, table: "list[Optional[str]]") -> Optional[str]:
        """The literal name whose presence bits are bits 7-8 of `first`
        (C.17, C.18), added to `table`"""
        vocabulary = self.vocabulary
        prefix = None
        if first & 0x02:
            prefix = self.identifying(vocabulary.prefixes, 'Prefix')
        if first & 0x01:
            self.identifying(vocabulary.namespace_names, 'Namespace name')
        name = _qualified(prefix, self.identifying(vocabulary.local_names, 'Local name'))
        _add(table, name)
        return name

    # Items

    def element_name(self, first: int) -> Optional[str]:
        table = self.vocabulary.element_names
        if first & 0x3C == 0x3C:
            return self.qualified_name(first, table)
        found: Optional[str] = _entry(table, self.index_from_bit_3(first), 'Element name')
        return found

    def attribute(self, first: int) -> "tuple[Optional[str], Any]":
        """C.4: an attribute whose first octet is `first`"""
        table = self.vocabulary.attribute_names
        if first & 0x7C == 0x78:
            name = self.qualified_name(first, table)
        else:
            name = _entry(table, self.index_from_bit_2(first), 'Attribute name')
        value, _cdata = self.non_identifying(self.vocabulary.attribute_values, 'Attribute value')
        return name, value

    def element_start(
            self, first: int) -> "tuple[Optional[str], list[tuple[Optional[str], Any]], bool]":
        """C.3 to the end of the attributes of an element whose first octet
        is `first`: its name, its attributes, and whether its children follow
        (or it has ended with them)"""
        if first & 0x3C == 0x38:
            self.namespace_attributes()
            first = (first & 0x40) | self.octet()
        name = self.element_name(first)
        attributes: "list[tuple[Optional[str], Any]]" = []
        if not first & 0x40:
            return name, attributes, True
        while True:
            octet = self.octet()
            if octet & 0x80:
                break
            attributes.append(self.attribute(octet))
        if octet == 0xFF:
            return name, attributes, False
        if octet != 0xF0:
            raise FastInfosetError('Octet %#x ends no attribute list' % octet)
        return name, attributes, True

    def content(self, first: int) -> Iterator[Event]:
        """The document element whose first octet is `first`, and everything
        in it (C.3.7, C.3.8); sets `document_ended` where its terminator
        shares an octet with the document's

        A terminator ends on bit 4 of its octet; the low four bits are
        padding before the parent's next child (0xF0) or the parent's own
        terminator (0xFF).
        """
        open_elements: "list[Optional[str]]" = []
        while True:
            if not first & 0x80:
                name, attributes, has_children = self.element_start(first)
                yield ('start', name, attributes)
                if has_children:
                    open_elements.append(name)
                else:
                    yield ('end', name)
            elif first & 0xC0 == 0x80:
                value, cdata = self.chunk(first)
                yield ('text', value, cdata)
            elif first & 0xF0 == 0xF0:
                if first not in (0xF0, 0xFF):
                    raise FastInfosetError('Octet %#x is not a terminator' % first)
                yield ('end', open_elements.pop())
                if first == 0xFF:
                    if not open_elements:
                        self.document_ended = True
                        return
                    yield ('end', open_elements.pop())
            else:
                yield from self.other_child(first)
            if not open_elements:
                return
            first = self.octet()

    def namespace_attributes(self) -> None:
        """C.3.4: declared, then not needed by the events"""
        vocabulary = self.vocabulary
        while True:
            octet = self.octet()
            if octet == 0xF0:
                return
            if octet & 0xFC != 0xCC:
                raise FastInfosetError('Octet %#x is not a namespace attribute' % octet)
            if octet & 0x02:
                self.identifying(vocabulary.prefixes, 'Prefix')
            if octet & 0x01:
                self.identifying(vocabulary.namespace_names, 'Namespace name')

    def other_child(self, first: int) -> Iterator[Event]:
        if first == 0xE1:
            target = self.identifying(self.vocabulary.other_ncnames, 'Name')
            content, _cdata = self.non_identifying(self.vocabulary.other_strings, 'String')
            yield ('pi', target, content)
        elif first == 0xE2:
            content, _cdata = self.non_identifying(self.vocabulary.other_strings, 'String')
            yield ('comment', content)
        elif first & 0xFC == 0xC8:
            # An unexpanded entity reference: its name and identifiers only.
            self.identifying(self.vocabulary.other_ncnames, 'Name')
            for bit in (0x02, 0x01):
                if first & bit:
                    self.identifying(self.vocabulary.other_uris, 'URI')
        else:
            raise FastInfosetError('Octet %#x begins no child' % first)

    # The document (C.2)

    def document(self) -> Iterator[Event]:
        for declaration in DECLARATIONS:
            if self.data.startswith(declaration):
                self.position = len(declaration)
                break
        if self.octets(4) != MAGIC:
            raise FastInfosetError('Not a Fast Infoset document of version 1')
        presence = self.octet()
        if presence & 0x80:
            raise FastInfosetError('The padding bit after the version is set')
        if presence & 0x40:
            # C.2.4: each datum an id (a URI) and its data, any octets; ignored (7.2.9)
            for _ in range(self.sequence_length()):
                self.literal_from_bit_2(self.octet())
                self.octets(self.octet_string_length(self.octet()))
        if presence & 0x20:
            self.initial_vocabulary()
        if presence & 0x10:
            self.declarations(0xFC, 0xC0, notation=True)
        if presence & 0x08:
            self.declarations(0xFE, 0xD0, notation=False)
        if presence & 0x04:
            encoding = self.literal_from_bit_2(self.octet())
            if encoding.lower().replace('-', '') != 'utf8':
                raise FastInfosetError('Character encoding scheme %r' % encoding)
        if presence & 0x02:
            self.octet()
        if presence & 0x01:
            self.non_identifying(self.vocabulary.other_strings, 'String')
        yield from self.document_children()

    def declarations(self, mask: int, prefix: int, notation: bool) -> None:
        """Notations (C.11) or unparsed entities (C.10), passed over

        A notation is a name and the identifiers its presence bits name; an
        unparsed entity is a name, a system identifier, a public identifier
        where its bit says so, and a notation name.
        """
        names, uris = self.vocabulary.other_ncnames, self.vocabulary.other_uris
        while True:
            octet = self.octet()
            if octet == 0xF0:
                return
            if octet & mask != prefix:
                raise FastInfosetError('Octet %#x begins no declaration' % octet)
            self.identifying(names, 'Name')
            identifiers = bin(octet & ~mask & 0xFF).count('1') + (0 if notation else 1)
            for _ in range(identifiers):
                self.identifying(uris, 'URI')
            if not notation:
                self.identifying(names, 'Name')

    def document_children(self) -> Iterator[Event]:
        root = False
        while True:
            first = self.octet()
            if not first & 0x80:
                if root:
                    raise FastInfosetError('A second document element')
                root = True
                yield from self.content(first)
                if self.document_ended:
                    break
            elif first & 0xF0 == 0xF0:
                if first not in (0xF0, 0xFF):
                    raise FastInfosetError('Octet %#x is not a terminator' % first)
                break
            elif first & 0xFC == 0xC4:
                # A document type declaration: identifiers and instructions.
                for bit in (0x02, 0x01):
                    if first & bit:
                        self.identifying(self.vocabulary.other_uris, 'URI')
                while self.peek() == 0xE1:
                    self.octet()
                    self.identifying(self.vocabulary.other_ncnames, 'Name')
                    self.non_identifying(self.vocabulary.other_strings, 'String')
                if self.octet() & 0xF0 != 0xF0:
                    raise FastInfosetError('A document type declaration is not terminated')
            else:
                yield from self.other_child(first)
        if not root:
            raise FastInfosetError('No document element')

    def initial_vocabulary(self) -> None:
        """C.2.5"""
        bits = (self.octet() & 0x1F) << 8 | self.octet()
        present = [bool(bits & (1 << (12 - place))) for place in range(13)]
        if present[0]:
            uri = self.literal_from_bit_2(self.octet())
            make = self.vocabularies.get(uri)
            if make is None:
                raise FastInfosetError('External vocabulary %r is not known' % uri)
            self.vocabulary = make()
        vocabulary = self.vocabulary
        if present[1]:
            for _ in range(self.sequence_length()):
                if vocabulary.next_alphabet > 255:
                    raise FastInfosetError('The restricted alphabet table is full')
                vocabulary.alphabets[vocabulary.next_alphabet] = \
                    self.literal_from_bit_2(self.octet())
                vocabulary.next_alphabet += 1
        if present[2]:
            for _ in range(self.sequence_length()):
                uri = self.literal_from_bit_2(self.octet())
                vocabulary.algorithm_names[vocabulary.next_algorithm] = uri
                vocabulary.next_algorithm += 1
        for flag, table in zip(present[3:8], (
                vocabulary.prefixes, vocabulary.namespace_names, vocabulary.local_names,
                vocabulary.other_ncnames, vocabulary.other_uris)):
            if flag:
                for _ in range(self.sequence_length()):
                    _add(table, self.literal_from_bit_2(self.octet()))
        for flag, values in zip(present[8:11], (
                vocabulary.attribute_values, vocabulary.content_chunks,
                vocabulary.other_strings)):
            if flag:
                for _ in range(self.sequence_length()):
                    first = self.octet()
                    _add(values, self.encoded((first >> 4) & 0x03, first, at_bit_5=True)[0])
        for flag, names in zip(present[11:13], (
                vocabulary.element_names, vocabulary.attribute_names)):
            if flag:
                for _ in range(self.sequence_length()):
                    _add(names, self.surrogate())

    def surrogate(self) -> str:
        """C.16, from bit 7: the name its indexes stand for"""
        first = self.octet()
        vocabulary = self.vocabulary
        prefix = None
        if first & 0x02:
            prefix = _entry(vocabulary.prefixes, self.index_from_bit_2(self.octet()), 'Prefix')
        if first & 0x01:
            _entry(vocabulary.namespace_names, self.index_from_bit_2(self.octet()),
                   'Namespace name')
        local = _entry(vocabulary.local_names, self.index_from_bit_2(self.octet()), 'Local name')
        return _qualified(prefix, local)


def events(
    data: bytes,
    vocabularies: "Optional[Mapping[str, Callable[[], Vocabulary]]]" = None,
) -> Iterator[Event]:
    """The XML events of the Fast Infoset document `data`"""
    yield from _Decoder(data, vocabularies or {}).document()

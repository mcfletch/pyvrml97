"""Fast Infoset documents (ITU-T X.891) and the X3D compressed binary encoding.

The documents here are written by `Writer`, which sets down each construct
bit by bit as X.891 Annex C gives it, so the decoder, which reads octets, is
held to the bit layouts rather than to itself. The X3D scenes are the
`.x3db` files of Web3D's example archives in `tests/fixtures/x3d-corpus`.
"""

import glob
import gzip
import os
import struct
import unittest
import zlib
from unittest import mock

import numpy as np

from vrml import protofunctions
from vrml.x3d import fivocabulary, readers
from vrml.x3d.fastinfoset import BUILTIN_ALGORITHMS, FastInfosetError, _Decoder, events

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, 'fixtures', 'x3d-corpus')


class Writer:
    """A Fast Infoset document set down bit by bit"""

    def __init__(self):
        self.bits = []

    def put(self, pattern):
        self.bits.extend(int(bit) for bit in pattern.replace(' ', ''))
        return self

    def number(self, value, width):
        return self.put(format(value, '0%db' % width))

    def octets(self, data):
        assert len(self.bits) % 8 == 0, 'octets begin on bit 1'
        for octet in data:
            self.number(octet, 8)
        return self

    @property
    def bit(self):
        """The bit of the current octet the next construct starts on, from 1"""
        return len(self.bits) % 8 + 1

    def data(self):
        assert len(self.bits) % 8 == 0
        return bytes(int(''.join(map(str, self.bits[start:start + 8])), 2)
                     for start in range(0, len(self.bits), 8))

    # C.21-C.28

    def sequence_length(self, value):
        if value <= 128:
            return self.put('0').number(value - 1, 7)
        return self.put('1000').number(value - 129, 20)

    def octet_string(self, data):
        """C.22, from bit 2"""
        length = len(data)
        if length <= 64:
            self.put('0').number(length - 1, 6)
        elif length <= 320:
            self.put('10 00000').number(length - 65, 8)
        else:
            self.put('11 00000').number(length - 321, 32)
        return self.octets(data)

    def length_at_5(self, length):
        """C.23"""
        if length <= 8:
            return self.put('0').number(length - 1, 3)
        if length <= 264:
            return self.put('10 00').number(length - 9, 8)
        return self.put('11 00').number(length - 265, 32)

    def length_at_7(self, length):
        """C.24"""
        if length <= 2:
            return self.put('0').number(length - 1, 1)
        if length <= 258:
            return self.put('10').number(length - 3, 8)
        return self.put('11').number(length - 259, 32)

    def index_at_2(self, value):
        """C.25"""
        if value <= 64:
            return self.put('0').number(value - 1, 6)
        if value <= 8256:
            return self.put('10').number(value - 65, 13)
        return self.put('11 0').number(value - 8257, 20)

    def index_at_3(self, value):
        """C.27"""
        if value <= 32:
            return self.put('0').number(value - 1, 5)
        if value <= 2080:
            return self.put('100').number(value - 33, 11)
        if value <= 526368:
            return self.put('101').number(value - 2081, 19)
        return self.put('110 0000000').number(value - 526369, 20)

    def index_at_4(self, value):
        """C.28"""
        if value <= 16:
            return self.put('0').number(value - 1, 4)
        if value <= 1040:
            return self.put('100').number(value - 17, 10)
        if value <= 263184:
            return self.put('101').number(value - 1041, 18)
        return self.put('110 000000').number(value - 263185, 20)

    # Strings

    def identifying(self, text=None, index=None):
        """C.13, from bit 1"""
        if index is not None:
            return self.put('1').index_at_2(index)
        return self.put('0').octet_string(text.encode('utf-8'))

    def encoded_at_3(self, kind, data, table=0):
        """C.19: kind 'utf8', 'utf16', 'alphabet' or 'algorithm'"""
        if kind in ('utf8', 'utf16'):
            return self.put('00' if kind == 'utf8' else '01').length_at_5(len(data)).octets(data)
        self.put('10' if kind == 'alphabet' else '11').number(table - 1, 8)
        return self.length_at_5(len(data)).octets(data)

    def encoded_at_5(self, kind, data, table=0):
        """C.20"""
        if kind in ('utf8', 'utf16'):
            return self.put('00' if kind == 'utf8' else '01').length_at_7(len(data)).octets(data)
        self.put('10' if kind == 'alphabet' else '11').number(table - 1, 8)
        return self.length_at_7(len(data)).octets(data)

    def value(self, text=None, index=None, add=True, kind='utf8', data=None, table=0):
        """C.14, from bit 1: a literal, an index, or the empty string (index 0)"""
        if index == 0:
            return self.put('1 1111111')
        if index is not None:
            return self.put('1').index_at_2(index)
        if data is None:
            data = text.encode('utf-8' if kind == 'utf8' else 'utf-16-be')
        return self.put('0' + ('1' if add else '0')).encoded_at_3(kind, data, table)

    # Items

    def child_start(self):
        if self.bit == 5:
            self.put('0000')
        assert self.bit == 1
        return self

    def literal_name(self, local, prefix=None, namespace=None):
        """The presence bits and strings of a literal qualified name"""
        self.put('1' if prefix else '0').put('1' if namespace else '0')
        if prefix:
            self.identifying(prefix)
        if namespace:
            self.identifying(namespace)
        return self.identifying(local)

    def start(self, name=None, index=None, attributes=(), prefix=None, namespace=None):
        """An element's start, attributes and all; `attributes` holds
        (name or index, value keywords) pairs"""
        self.child_start().put('0').put('1' if attributes else '0')
        if index is not None:
            self.index_at_3(index)
        else:
            self.put('1111').literal_name(name, prefix, namespace)
        for attribute, value in attributes:
            self.put('0')
            if isinstance(attribute, int):
                self.index_at_2(attribute)
            else:
                self.put('1111 0').literal_name(attribute)
            self.value(**value)
        if attributes:
            self.put('1111')
        return self

    def end(self):
        """An element's terminator"""
        return self.put('1111')

    def chunk(self, text=None, index=None, add=True, kind='utf8', data=None, table=0):
        self.child_start().put('10')
        if index is not None:
            return self.put('1').index_at_4(index)
        if data is None:
            data = text.encode('utf-8' if kind == 'utf8' else 'utf-16-be')
        return self.put('0' + ('1' if add else '0')).encoded_at_5(kind, data, table)

    def comment(self, text):
        return self.child_start().put('11100010').value(text)

    def instruction(self, target, content):
        return self.child_start().put('11100001').identifying(target).value(content)

    def finish(self):
        """The document's terminator and its padding"""
        self.put('1111')
        if self.bit == 5:
            self.put('0000')
        return self.data()


def header(vocabulary=None, presence='0000000', declaration=b''):
    """A writer past the document's header; `vocabulary` an external URI"""
    writer = Writer().octets(declaration + b'\xe0\x00\x00\x01').put('0')
    if vocabulary is None:
        return writer.put(presence)
    writer.put('0100000').put('000 1000000000000')
    return writer.put('0').octet_string(vocabulary.encode('ascii'))


def deep(depth):
    """A document of `depth` elements, each inside the last"""
    writer = header()
    for _ in range(depth):
        writer.start('a')
    for _ in range(depth):
        writer.end()
    return writer.finish()


def document(body, **options):
    """The events of a document whose element content `body` writes"""
    writer = header(**options)
    body(writer)
    return list(events(writer.finish()))


def element(name, attributes=(), children=()):
    return [('start', name, list(attributes))] + list(children) + [('end', name)]


class TestStructure(unittest.TestCase):
    def test_an_empty_root(self):
        self.assertEqual(document(lambda w: w.start('a').end()), element('a'))

    def test_an_empty_root_with_an_attribute(self):
        found = document(lambda w: w.start('a', attributes=[('x', dict(text='1'))]).end())
        self.assertEqual(found, element('a', [('x', '1')]))

    def test_children_with_and_without_attributes(self):
        def body(w):
            w.start('a', attributes=[('x', dict(text='1'))])
            w.start('b').end()
            w.start('c', attributes=[('y', dict(text='2'))]).end()
            w.start('d').start('e').end().end()
            w.end()
        self.assertEqual(document(body), element('a', [('x', '1')], (
            element('b') + element('c', [('y', '2')]) + element('d', (), element('e')))))

    def test_nested_last_children_end_together(self):
        def body(w):
            w.start('a').start('b').start('c').end().end().end()
        self.assertEqual(document(body), element('a', (), element('b', (), element('c'))))

    def test_text_comments_and_instructions(self):
        def body(w):
            w.start('a').chunk('hello').comment('note').instruction('tool', 'run')
            w.chunk(index=1).end()
        self.assertEqual(document(body), element('a', (), (
            ('text', 'hello', False), ('comment', 'note'), ('pi', 'tool', 'run'),
            ('text', 'hello', False))))

    def test_a_declaration_may_lead(self):
        found = document(lambda w: w.start('a').end(),
                         declaration=b"<?xml version='1.0' encoding='finf'?>")
        self.assertEqual(found, element('a'))

    def test_names_by_index(self):
        def body(w):
            w.instruction('tool', 'one').child_start().put('11100001').identifying(index=1)
            w.value(index=1).start('a').end()
        self.assertEqual(document(body), [('pi', 'tool', 'one'), ('pi', 'tool', 'one')]
                         + element('a'))

    def test_deep_nesting(self):
        found = list(events(deep(5000)))
        self.assertEqual(len(found), 10000)
        self.assertEqual((found[4999], found[5000]), (('start', 'a', []), ('end', 'a')))

    def test_a_declaration_with_instructions(self):
        def body(w):
            w.put('110001 01').identifying('urn:public')
            w.put('11100001').identifying('t').value('c').put('1111 0000')
            w.start('a').end()
        self.assertEqual(document(body), element('a'))

    def test_comments_around_the_root(self):
        def body(w):
            w.comment('before').start('a').end().comment('after')
        self.assertEqual(document(body), [('comment', 'before')] + element('a')
                         + [('comment', 'after')])

    def test_a_prefixed_name(self):
        def body(w):
            w.start('a', prefix='p', namespace='urn:x').end()
        self.assertEqual(document(body), element('p:a'))


class TestTables(unittest.TestCase):
    def test_literal_names_are_added_and_referred_to(self):
        def body(w):
            w.start('a').start('b', attributes=[('x', dict(text='1'))]).end()
            w.start(index=2, attributes=[(1, dict(text='2'))]).end().end()
        self.assertEqual(document(body), element('a', (), (
            element('b', [('x', '1')]) + element('b', [('x', '2')]))))

    def test_values_are_added_only_when_asked(self):
        def body(w):
            w.start('a', attributes=[('x', dict(text='kept')), ('y', dict(text='not', add=False)),
                                     ('z', dict(index=1)), ('w', dict(index=0))]).end()
        self.assertEqual(document(body), element(
            'a', [('x', 'kept'), ('y', 'not'), ('z', 'kept'), ('w', '')]))

    def test_an_index_past_its_table(self):
        with self.assertRaisesRegex(FastInfosetError, 'Attribute value index 2'):
            document(lambda w: w.start('a', attributes=[('x', dict(index=2))]).end())

    def test_an_element_name_past_its_table(self):
        with self.assertRaisesRegex(FastInfosetError, 'Element name index 5'):
            document(lambda w: w.start(index=5).end())

    def test_utf16_strings(self):
        def body(w):
            w.start('a', attributes=[('x', dict(text='é', kind='utf16'))])
            w.chunk('ü', kind='utf16').end()
        self.assertEqual(document(body), element(
            'a', [('x', 'é')], [('text', 'ü', False)]))

    def test_restricted_alphabets(self):
        packed = bytes([0x1C, 0xA2, 0xE3, 0xDF])         # 1 . - 2 SPACE 3 e, then ones
        def body(w):
            w.start('a', attributes=[('x', dict(kind='alphabet', table=1, data=packed))])
            w.chunk(kind='alphabet', table=2, data=bytes([0x0C, 0x1D])).end()
        self.assertEqual(document(body), element(
            'a', [('x', '1.-2 3e')], [('text', '0T1Z', False)]))


def algorithm(index, data):
    return dict(kind='algorithm', table=index, data=data)


class TestAlgorithms(unittest.TestCase):
    """The built-in encoding algorithms of X.891 clause 10"""

    def decoded(self, index, data):
        found = document(lambda w: w.start('a', attributes=[('x', algorithm(index, data))]).end())
        return found[0][2][0][1]

    def test_hexadecimal_and_base64(self):
        self.assertEqual(self.decoded(1, b'\x0f\xa0'), '0FA0')
        self.assertEqual(self.decoded(2, b'hi'), 'aGk=')

    def test_integers(self):
        self.assertEqual(list(self.decoded(3, struct.pack('>hh', -2, 300))), [-2, 300])
        self.assertEqual(list(self.decoded(4, struct.pack('>i', -70000))), [-70000])
        self.assertEqual(list(self.decoded(5, struct.pack('>q', 2 ** 40))), [2 ** 40])

    def test_booleans(self):
        # Four bits counting the unused bits (7), then 1 0 1 1 0.
        self.assertEqual(self.decoded(6, bytes([0b01111011, 0b00000000])),
                         [True, False, True, True, False])

    def test_floats_and_doubles(self):
        floats = self.decoded(7, struct.pack('>ff', 1.5, -2.25))
        self.assertEqual(floats.dtype, np.float32)
        self.assertEqual(list(floats), [1.5, -2.25])
        self.assertEqual(list(self.decoded(8, struct.pack('>d', 0.1))), [0.1])

    def test_uuids(self):
        self.assertEqual(self.decoded(9, bytes(range(16))),
                         '00010203-0405-0607-0809-0a0b0c0d0e0f')

    def test_cdata_is_marked(self):
        found = document(lambda w: w.start('a').chunk(**algorithm(10, b'x < y')).end())
        self.assertEqual(found[1], ('text', 'x < y', True))

    def test_values_that_are_not_whole(self):
        for index, data in ((4, b'\x00\x00\x01'), (9, b'\x00'), (6, b'\xf0')):
            with self.subTest(index=index), self.assertRaises(FastInfosetError):
                self.decoded(index, data)
        with self.assertRaises(FastInfosetError):
            BUILTIN_ALGORITHMS[6](b'')

    def test_an_algorithm_without_a_decoder(self):
        found = self.decoded(40, b'\x00\x01')
        self.assertEqual((found.index, found.name, found.octets), (40, 'unnamed', b'\x00\x01'))


class TestIntegers(unittest.TestCase):
    """Every form of the lengths and indexes of C.21-C.28, at its ends"""

    def read(self, write, read, value, lead=''):
        writer = Writer().put(lead)
        write(writer, value)
        while writer.bit != 1:
            writer.put('0')
        decoder = _Decoder(writer.data(), {})
        if not lead:
            return read(decoder)
        return read(decoder, decoder.octet())

    def test_each_form(self):
        cases = [
            (Writer.index_at_2, _Decoder.index_from_bit_2, '0',
             (1, 64, 65, 8256, 8257, 2 ** 20)),
            (Writer.index_at_3, _Decoder.index_from_bit_3, '00',
             (1, 32, 33, 2080, 2081, 526368, 526369, 2 ** 20)),
            (Writer.index_at_4, _Decoder.index_from_bit_4, '000',
             (1, 16, 17, 1040, 1041, 263184, 263185, 2 ** 20)),
            (Writer.length_at_5, _Decoder.length_from_bit_5, '0000',
             (1, 8, 9, 264, 265, 2 ** 32)),
            (Writer.length_at_7, _Decoder.length_from_bit_7, '000000',
             (1, 2, 3, 258, 259, 2 ** 32)),
        ]
        for write, read, lead, values in cases:
            for value in values:
                with self.subTest(read=read.__name__, value=value):
                    self.assertEqual(self.read(write, read, value, lead), value)
        for value in (1, 128, 129, 2 ** 20):
            with self.subTest(read='sequence_length', value=value):
                self.assertEqual(self.read(Writer.sequence_length,
                                           _Decoder.sequence_length, value), value)

    def test_octet_string_lengths(self):
        for length in (1, 64, 65, 320, 321):
            with self.subTest(length=length):
                text = 'v' * length
                found = document(lambda w, t=text: w.start(
                    'a', attributes=[('x', dict(text=t)), ('y', dict(index=1))]).end())
                self.assertEqual(found[0][2], [('x', text), ('y', text)])
                names = document(lambda w, t=text: w.start(t).end())
                self.assertEqual(names[0][1], text)

    def test_long_chunks(self):
        for length in (1, 2, 3, 258, 259):
            with self.subTest(length=length):
                found = document(lambda w, n=length: w.start('a').chunk('c' * n).end())
                self.assertEqual(found[1], ('text', 'c' * length, False))

    def test_octets_that_are_no_index(self):
        for read, octet in ((_Decoder.index_from_bit_3, 0x38), (_Decoder.index_from_bit_4, 0x1C)):
            with self.subTest(read=read.__name__), self.assertRaises(FastInfosetError):
                read(_Decoder(b'', {}), octet)


def vocabulary_document(writer):
    """A document listing a vocabulary of its own (C.2.5), then using it"""
    writer.put('000 01100 10010111')
    # restricted alphabets: one, at 16
    writer.sequence_length(1).put('0').octet_string(b'ab')
    # encoding algorithms: one URI, at 32
    writer.sequence_length(1).put('0').octet_string(b'urn:example:algorithm')
    # local names
    writer.sequence_length(2).put('0').octet_string(b'root').put('0').octet_string(b'size')
    # attribute values and other strings: one each
    writer.sequence_length(1).put('00').encoded_at_3('utf8', b'big')
    writer.sequence_length(1).put('00').encoded_at_3('utf8', b'1.0')
    # element and attribute name surrogates
    writer.sequence_length(1).put('000000 00').put('0').index_at_2(1)
    writer.sequence_length(1).put('000000 00').put('0').index_at_2(2)
    # version, by index into other strings
    writer.value(index=1)
    writer.start(index=1, attributes=[(1, dict(index=1))])
    writer.chunk(kind='alphabet', table=16, data=bytes([0b01001111])).end()
    return writer.finish()


class TestTheDocument(unittest.TestCase):
    def test_a_vocabulary_of_its_own(self):
        writer = Writer().octets(b'\xe0\x00\x00\x01').put('0 0100001')
        found = list(events(vocabulary_document(writer)))
        self.assertEqual(found, element('root', [('size', 'big')], [('text', 'ba', False)]))

    def test_prefixed_name_surrogates(self):
        writer = Writer().octets(b'\xe0\x00\x00\x01').put('0 0100000')
        writer.put('000 00011 10000010')
        writer.sequence_length(1).put('0').octet_string(b'p')
        writer.sequence_length(1).put('0').octet_string(b'urn:p')
        writer.sequence_length(1).put('0').octet_string(b'a')
        writer.sequence_length(1).put('000000 11').put('0').index_at_2(2)
        writer.put('0').index_at_2(2).put('0').index_at_2(1)
        writer.start(index=1).end()
        self.assertEqual(list(events(writer.finish())), element('p:a'))

    def test_a_full_alphabet_table(self):
        writer = Writer().octets(b'\xe0\x00\x00\x01').put('0 0100000')
        writer.put('000 01000 00000000').sequence_length(241)
        for _ in range(241):
            writer.put('0').octet_string(b'ab')
        with self.assertRaisesRegex(FastInfosetError, 'alphabet table is full'):
            list(events(writer.start('a').end().finish()))

    def test_a_full_table(self):
        from vrml.x3d.fastinfoset import TABLE_LIMIT, _add  # noqa: PLC0415 kept with its use
        with self.assertRaisesRegex(FastInfosetError, 'full'):
            _add([None] * TABLE_LIMIT, 'one more')

    def test_an_external_vocabulary(self):
        def make():
            from vrml.x3d.fastinfoset import Vocabulary  # noqa: PLC0415 kept with its use
            return Vocabulary(element_names=['outer', None], attribute_names=['size'])
        writer = header('urn:example:v')
        writer.start(index=1, attributes=[(1, dict(text='1'))]).start(index=2).end().end()
        found = list(events(writer.finish(), {'urn:example:v': make}))
        self.assertEqual(found, element('outer', [('size', '1')], element(None)))

    def test_an_unknown_vocabulary(self):
        writer = header('urn:example:unknown').start('a').end()
        with self.assertRaisesRegex(FastInfosetError, 'urn:example:unknown'):
            list(events(writer.finish()))

    def test_the_other_header_components(self):
        writer = Writer().octets(b'\xe0\x00\x00\x01').put('0 1011111')
        writer.sequence_length(1).put('0').octet_string(b'id').put('0').octet_string(b'data')
        writer.put('110000 10').identifying('png').identifying('image/png')
        writer.put('1111 0000')
        writer.put('1101000 1').identifying('logo').identifying('logo.png')
        writer.identifying('urn:logo').identifying('png').put('1111 0000')
        writer.put('0').octet_string(b'UTF-8')
        writer.put('0000000 1')
        writer.value('1.0')
        writer.put('110001 10').identifying('scene.dtd')
        writer.put('11100001').identifying('target').value('content').put('1111 0000')
        writer.start('a').end()
        self.assertEqual(list(events(writer.finish())), element('a'))

    def test_namespace_attributes(self):
        writer = header().put('0 1 1110 00')
        writer.put('110011 11').identifying('p').identifying('urn:p')
        writer.put('110011 01').identifying('urn:default')
        writer.put('1111 0000').put('00 1111 00').identifying('a')
        writer.put('0 1111 0 00').identifying('x').value('1').put('1111').end()
        self.assertEqual(list(events(writer.finish())), element('a', [('x', '1')]))

    def test_an_entity_reference(self):
        writer = header().start('a').child_start().put('110010 11')
        writer.identifying('e').identifying('sys').identifying('pub').end()
        self.assertEqual(list(events(writer.finish())), element('a'))

    def test_documents_that_break_the_encoding(self):
        good = header().start('a').end().finish()
        broken = {
            'magic': b'\xe0\x00\x00\x02' + good[4:],
            'padding': good[:4] + b'\x80' + good[5:],
            'truncated': good[:-1],
            'encoding': header(presence='0000100').put('0').octet_string(b'latin-1')
                .start('a').end().finish(),
            'no root': header().finish(),
            'two roots': header().start('a').end().start('b').end().finish(),
            'a bad child': header().start('a').put('11011111').end().finish(),
            'a bad terminator': header().put('0 0 1111 00').identifying('a')
                .put('11110101').finish(),
            'not utf-8': header().put('0 0 1111 00').put('0').octet_string(b'\xff')
                .put('1111').finish(),
            'not utf-16': header().start('a').chunk(kind='utf16', data=b'\x00').end().finish(),
            'a string past the end': header().put('0 0 1111 00 0 0').number(9, 6).data() + b'ab',
            'no such alphabet': header().start('a').chunk(kind='alphabet', table=9, data=b'\x00')
                .end().finish(),
            'a bad attribute list end': header().put('0 1 1111 00').identifying('a')
                .put('0 1111 0 00').identifying('x').value('1').put('11110101').finish(),
            'a bad namespace attribute': header().put('0 1 1110 00').put('10000000').finish(),
            'a bad declaration': Writer().octets(b'\xe0\x00\x00\x01').put('0 0010000')
                .put('10000000').finish(),
            'a bad document terminator': header().start('a').end().put('0000').put('11110101')
                .data(),
            'an unterminated declaration': header().put('110001 00').put('00000000').finish(),
            'a declaration at the end': header().put('110001 00').data(),
        }
        for name, data in broken.items():
            with self.subTest(name), self.assertRaises(FastInfosetError):
                list(events(data))


class TestTheX3DVocabulary(unittest.TestCase):
    def test_attribute_names_as_the_files_number_them(self):
        names = fivocabulary.attribute_names('3.2')
        self.assertEqual(len(names), fivocabulary.ATTRIBUTE_TABLE_SIZE)
        self.assertEqual(names[:3], ['DEF', 'USE', 'containerField'])
        self.assertEqual(names[52], 'bboxSize')
        self.assertEqual(names[53:56], [None, None, None])
        self.assertEqual(names[56], 'accessType')
        self.assertEqual(names[240], 'profile')
        self.assertEqual(names[350], 'mustOutput')
        self.assertEqual(fivocabulary.attribute_names('3.3')[350], 'forceOutput')
        self.assertIsNone(names[517])

    def test_element_names_by_edition(self):
        self.assertEqual(len(fivocabulary.element_names('3.2')), 233)
        self.assertEqual(fivocabulary.element_names('3.2')[223], 'TexCoordDamper')
        names = fivocabulary.element_names('3.3')
        self.assertEqual((len(names), names[0], names[138], names[223]),
                         (252, 'Shape', 'X3D', 'TexCoordDamper2D'))

    def test_attribute_values_are_preloaded(self):
        made = fivocabulary.VOCABULARIES['urn:web3d:x3d:fi-vocabulary-3.2']()
        self.assertEqual(made.attribute_values, ['false', 'true'])
        self.assertEqual(made.next_algorithm, 40)


def delta_zlib(values, span, count=None, stored=None):
    if stored is None:
        stored = [value + 1 - (values[index - span] if span and index >= span else 0)
                  for index, value in enumerate(values)]
    count = len(values) if count is None else count
    return (struct.pack('>I', count) + bytes([span])
            + zlib.compress(struct.pack('>%di' % len(stored), *stored)))


class TestDeltaZlib(unittest.TestCase):
    def test_spans(self):
        values = [0, 1, 2, -1, 3, 4, 5, -1, 6, 9, 8, -1]
        for span in (0, 1, 4, 20):
            with self.subTest(span=span):
                self.assertEqual(
                    list(fivocabulary.delta_zlib_integers(delta_zlib(values, span))), values)

    def test_the_stored_form_is_one_more(self):
        self.assertEqual(list(fivocabulary.delta_zlib_integers(
            delta_zlib([2, 2, 3], 0, stored=[3, 3, 4]))), [2, 2, 3])

    def test_values_that_are_not_whole(self):
        for data in (b'\x00\x00', delta_zlib([1, 2], 0, count=3),
                     struct.pack('>I', 2 ** 30) + b'\x00',
                     struct.pack('>I', 1) + b'\x00not zlib',
                     delta_zlib([1, 2, 3], 0, count=2)):
            with self.subTest(data=data[:8]), self.assertRaises(FastInfosetError):
                fivocabulary.delta_zlib_integers(data)


def scene_of(name):
    path = glob.glob(os.path.join(CORPUS, '**', name), recursive=True)[0]
    with open(path, 'rb') as stream:
        return readers.read(stream.read(), name=path)


def nodes_of(node, type_name):
    """The nodes of type `type_name` in and under `node`"""
    if type(node).__name__ == type_name:
        yield node
    for declared in protofunctions.getFields(node):
        if declared.typeName() == 'SFNode':
            held = [getattr(node, declared.name)]
        elif declared.typeName() == 'MFNode':
            held = getattr(node, declared.name)
        else:
            continue
        for child in held:
            if child is not None:
                yield from nodes_of(child, type_name)


def errors(scene):
    return [problem.message for problem in scene.problems if problem.severity == 'error']


#: The scenes of the committed corpus whose .x3db is the revision of the
#: .x3d beside it.
SAME_AS_XML = (
    'viewpoint', 'Figure04_09TwoTextShapesDifferentJustification',
    'Figure11_1CafeSignSwitchResolutions', 'Figure11_2CafeSignBillboard',
    'Figure13_10PointSetBoxCorners', 'Figure13_11IndexedLineSetBoxWireframe',
    'Figure14_3ElevationGridRibbon', 'Figure15_07ExtrudedCylinder',
    'Figure17_13SimplePixelTexture', 'Figure18_25bTextureTransformBrickBox',
    'Figure22_1BackgroundSkySphere', 'Figure23_4BlackFogVisibility40',
    'Figure23_5BindingFogsAndBackgrounds', 'Figure25_11DungeonDoor',
    'Figure31_1WallColorPrototype',
)


class TestX3DScenes(unittest.TestCase):
    def test_binary_and_xml_build_one_graph(self):
        from vrml.x3d.compare import first_difference  # noqa: PLC0415 kept with its use
        for name in SAME_AS_XML:
            with self.subTest(scene=name):
                path = glob.glob(os.path.join(CORPUS, '**', name + '.x3db'), recursive=True)[0]
                with open(path[:-1], 'rb') as stream:
                    expected = readers.read(stream.read(), name=path[:-1])
                self.assertIsNone(first_difference(expected, scene_of(name + '.x3db'),
                                                   header=False))

    def test_a_scene_and_its_typed_values(self):
        scene = scene_of('Figure10_08BlinkingSphere.x3db')
        self.assertEqual(errors(scene), [])
        self.assertEqual(scene.profile, 'Interchange')
        timer = scene.getDEF('CLOCK')
        self.assertEqual(timer.cycleInterval, 2.0)
        self.assertIs(timer.loop, True)
        colours = scene.getDEF('COLOR_PATH').keyValue
        self.assertEqual(np.asarray(colours).dtype, np.float32)

    def test_integers_by_delta_zlib(self):
        scene = scene_of('Figure13_11IndexedLineSetBoxWireframe.x3db')
        self.assertEqual(errors(scene), [])
        found = list(nodes_of(scene, 'IndexedLineSet'))
        self.assertEqual(list(found[0].coordIndex[:6]), [0, 1, 2, 3, 0, -1])

    def test_gzip_compressed(self):
        path = glob.glob(os.path.join(CORPUS, '**', 'Figure10_08BlinkingSphere.x3db'),
                         recursive=True)[0]
        with open(path, 'rb') as stream:
            data = gzip.compress(stream.read())
        self.assertEqual(errors(readers.read(data, name='scene.x3db.gz')), [])

    def test_a_broken_document_is_reported(self):
        scene = readers.read(b'\xe0\x00\x00\x01\x00', name='broken.x3db')
        self.assertEqual(len(errors(scene)), 1)
        self.assertIn('Fast Infoset', errors(scene)[0])

    def test_a_value_its_field_does_not_take(self):
        writer = header('urn:web3d:x3d:fi-vocabulary-3.2')
        writer.start(index=139, attributes=[(241, dict(text='Immersive')),
                                            (316, dict(text='3.3'))])
        writer.start(index=119).start(index=136, attributes=[
            (138, algorithm(6, bytes([0b01111011, 0]))),
            (450, algorithm(7, struct.pack('>fff', 0, 2, 0))),
        ]).end().end().end()
        scene = readers.read(writer.finish(), encoding='fastinfoset')
        found = errors(scene)
        self.assertEqual(len(found), 2, found)
        self.assertTrue(all('Viewpoint' in message for message in found))

    def test_typed_values_in_statements(self):
        """A prototype field's default arrives as text, which its type reads"""
        writer = header('urn:web3d:x3d:fi-vocabulary-3.2')
        writer.start(index=139, attributes=[(316, dict(text='3.3'))]).start(index=119)
        writer.start('ProtoDeclare', attributes=[('name', dict(text='P'))])
        writer.start('ProtoInterface')
        for name, type_name, value in (
                ('size', 'SFVec3f', algorithm(7, struct.pack('>fff', 1, 2, 3))),
                ('on', 'MFBool', algorithm(6, bytes([0b01111011, 0])))):
            writer.start('field', attributes=[
                ('name', dict(text=name)), ('type', dict(text=type_name)),
                ('accessType', dict(text='inputOutput')), ('value', value)]).end()
        writer.end().start('ProtoBody').start(index=6).end().end().end()
        writer.start('ProtoInstance', attributes=[('name', dict(text='P')),
                                                  ('DEF', dict(text='I'))]).end()
        writer.start(index=6, attributes=[('notAField', algorithm(7, struct.pack('>f', 1)))])
        writer.end().end().end()
        scene = readers.read(writer.finish(), encoding='fastinfoset')
        instance = scene.getDEF('I')
        self.assertEqual(list(instance.size), [1, 2, 3])
        self.assertEqual(list(instance.on), [True, False, True, True, False])
        self.assertEqual([problem.message for problem in scene.problems
                          if 'notAField' not in problem.message], [])
        self.assertTrue(any('notAField' in problem.message for problem in scene.problems))

    def test_a_value_in_an_algorithm_not_read(self):
        writer = header('urn:web3d:x3d:fi-vocabulary-3.2')
        writer.start(index=139, attributes=[(316, dict(text='3.3'))]).start(index=119)
        writer.start(index=6, attributes=[(1, dict(text='T')),
                                          (21, algorithm(35, b'\x78\x01'))])
        writer.chunk(**algorithm(35, b'\x00')).end().end().end()
        scene = readers.read(writer.finish(), encoding='fastinfoset')
        self.assertIsNotNone(scene.getDEF('T'))
        found = errors(scene)
        self.assertEqual(len(found), 2, found)
        self.assertTrue(all('zlibFloatArrayEncoder' in message for message in found), found)

    def test_an_element_no_edition_names(self):
        def make():
            made = fivocabulary.vocabulary('3.2')()
            made.element_names[5] = None                # Transform
            return made
        writer = header('urn:example:x3d')
        writer.start(index=139, attributes=[(316, dict(text='3.3'))]).start(index=119)
        writer.start(index=6).end().end().end()
        with mock.patch.dict(fivocabulary.VOCABULARIES, {'urn:example:x3d': make}):
            scene = readers.read(writer.finish(), encoding='fastinfoset')
        self.assertTrue(any('element name' in message for message in errors(scene)))

    def test_an_attribute_no_edition_names(self):
        writer = header('urn:web3d:x3d:fi-vocabulary-3.2')
        writer.start(index=139, attributes=[(316, dict(text='3.3'))])
        writer.start(index=119).start(index=78, attributes=[(54, dict(text='2 2 2'))])
        writer.end().end().end()
        scene = readers.read(writer.finish(), encoding='fastinfoset')
        warnings = [problem.message for problem in scene.problems if problem.severity == 'warning']
        self.assertTrue(any('Inline attribute' in message for message in warnings), warnings)


if __name__ == '__main__':
    unittest.main()

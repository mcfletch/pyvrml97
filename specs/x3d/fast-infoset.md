# X3D compressed binary encoding (.x3db): decoder notes

Facts for decoding a `.x3db` file, taken from two published specifications and
from the bytes of sample files. Nothing here comes from the source code of any
Fast Infoset or X3D implementation.

## 0. Sources

| Short name | Document | Where it was read |
|---|---|---|
| X.891 | ITU-T Rec. X.891 (05/2005) \| ISO/IEC 24824-1:2007, *Fast infoset* | `https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-X.891-200505-I!!PDF-E&type=items` (808 457 bytes, free download) |
| 19776-3 | ISO/IEC 19776-3:2015 *X3D encodings, Part 3: Compressed binary encoding*, edition 3.3 | `https://www.web3d.org/documents/specifications/19776-3/V3.3/Part03/` (`concepts.html`, `EncodingOfFields.html`, `tables.html`) |
| 19776-3 v3.2 | same part, edition 3.2 | `https://www.web3d.org/documents/specifications/19776-3/V3.2/Part03/tables.html` |
| 19776-3 v3.1 | same part, edition 3.1 | `.../19776-3/V3.1/Part03/tables.html`, `EncodingOfFields.html` |
| 19776-3 v4 CD | committee draft for X3D 4.0 | `https://www.web3d.org/specifications/X3Dv4Draft/ISO-IEC19776-3v4.0-CD/Part03/tables.html` |

Clause numbers below are X.891 unless prefixed "19776-3".

X.891 Annex C is informative but is stated (C.1.1) to describe "informally
(but precisely and fully)" the normative encoding of clause 12 and Annex A;
the bit patterns below are from Annex C and were checked against the sample
bytes in section 11.

Conventions (X.891 5.5): bits in an octet are numbered first (most significant)
to eighth (least significant). "Bits 3-8" means the six low bits. An integer
"in a field of n bits" is unsigned, most significant bit first, and every
multi-octet integer in these encodings is big-endian. Strings in bit patterns
such as `'110'` are written first bit first.

## 1. Document header and framing

### 1.1 Optional XML declaration (12.3-12.5)

The stream may begin with one of exactly nine UTF-8 strings (12.3):

```
<?xml encoding='finf'?>
<?xml encoding='finf' standalone='yes'?>
<?xml encoding='finf' standalone='no'?>
<?xml version='1.0' encoding='finf'?>
<?xml version='1.0' encoding='finf' standalone='yes'?>
<?xml version='1.0' encoding='finf' standalone='no'?>
<?xml version='1.1' encoding='finf'?>
<?xml version='1.1' encoding='finf' standalone='yes'?>
<?xml version='1.1' encoding='finf' standalone='no'?>
```

There is no separator after it; the identification bits follow immediately.
A decoder can test for a leading `<?xml` and then match one of the nine
strings. 19776-3 4.2.4 EXAMPLE 2 shows `<?xml version='1.0' encoding='finf'
standalone='yes'>` without the closing `?`; that is a typo in the example, not
a tenth form (12.3 lists only the nine above). None of the samples carries a
declaration.

### 1.2 Identification, version, padding (12.6-12.9, C.1.3)

| Bits | Value | Meaning |
|---|---|---|
| 16 | `1110000000000000` (0xE0 0x00) | identification (12.6) |
| 16 | `0000000000000001` (0x00 0x01) | version number, 1 for this edition (12.7, 12.9) |
| 1 | `0` | padding (12.8) |

So a file without declaration starts `E0 00 00 01`, and the Document encoding
starts on the second bit of the fifth octet. 19776-3 4.2.4 restates these 33
bits as `'11100000000000000000000000000000000'` (it shows a 35-bit string;
the 33 bits of X.891 are the normative ones). A decoder should reject a
version other than 1.

### 1.3 Document presence bits (C.2.3)

Seven bits follow the padding bit, in this order, `1` = present:

| Bit of octet 5 | Component |
|---|---|
| 2 | additional-data |
| 3 | initial-vocabulary |
| 4 | notations |
| 5 | unparsed-entities |
| 6 | character-encoding-scheme |
| 7 | standalone |
| 8 | version |

The components then appear in that order (C.2.4-C.2.10):

- additional-data (C.2.4): a count by C.21, then for each datum `'0'` padding +
  id by C.22, then `'0'` padding + data by C.22. A processor may ignore every
  datum (7.2.9).
- initial-vocabulary (C.2.5): see section 2.
- notations (C.2.6): each item is `'110000'` + Notation (C.11); then `'1111'`
  termination + `'0000'` padding. Only present when the bit is set.
- unparsed-entities (C.2.7): each item is `'1101000'` + UnparsedEntity (C.10);
  then `'1111'` + `'0000'`.
- character-encoding-scheme (C.2.8): `'0'` padding + C.22 octet string (UTF-8
  name; absence means "UTF-8", 7.2.26).
- standalone (C.2.9): `'0000000'` padding then one bit, `1` = yes.
- version (C.2.10): NonIdentifyingStringOrIndex by C.14, OTHER STRING
  category (7.2.28).

### 1.4 Document children and termination (C.2.11, C.2.12, 12.11)

Each child starts on the first bit of an octet. If the previous item ended on
the fourth bit, `'0000'` padding is appended first (C.2.11.1). The first bits
identify the child:

| Prefix | Child |
|---|---|
| `0` | element (C.3) |
| `11100001` | processing instruction (C.5) |
| `11100010` | comment (C.8) |
| `110001` | document type declaration (C.9) |

After the last child, `'1111'` (C.2.12) is appended, even when there are no
children. If the whole encoding then ends on the fourth bit of an octet,
`'0000'` padding completes it (C.1.3, 12.11). Exactly one child is an element;
at most one is a DTD; the rest are PIs or comments (7.2.29).

## 2. Initial vocabulary and the vocabulary tables

### 2.1 Encoding (C.2.5)

`'000'` padding, then 13 presence bits in this order (C.2.5.1, textual order
of 7.2.1):

1. external-vocabulary
2. restricted-alphabets
3. encoding-algorithms
4. prefixes
5. namespace-names
6. local-names
7. other-ncnames
8. other-uris
9. attribute-values
10. content-character-chunks
11. other-strings
12. element-name-surrogates
13. attribute-name-surrogates

At least one must be present (7.2.1 constraint). The `'000'` and the first
five bits fill the octet after the document presence bits; the other eight
bits fill the next octet. Then, in that order:

- external-vocabulary (C.2.5.2): `'0'` padding + C.22 octet string, a URI.
- restricted-alphabets, encoding-algorithms, prefixes, namespace-names,
  local-names, other-ncnames, other-uris (C.2.5.3): a count by C.21, then each
  item as `'0'` padding + C.22 octet string (UTF-8).
- attribute-values, content-character-chunks, other-strings (C.2.5.4): a count
  by C.21, then each item as `'00'` padding + EncodedCharacterString by C.19.
- element-name-surrogates, attribute-name-surrogates (C.2.5.5): a count by
  C.21, then each item as `'000000'` padding + NameSurrogate by C.16.

### 2.2 The tables (8.2-8.5, Table 1 of 7.2.16)

| Table | Entry | Filled from initial-vocabulary component | Built-in entries |
|---|---|---|---|
| restricted alphabet | ordered set of 2..2^20 distinct characters | restricted-alphabets | 1 numeric, 2 date and time (clause 9) |
| encoding algorithm | algorithm | encoding-algorithms (URIs) | 1..10 (clause 10) |
| PREFIX | string | prefixes | 1 `xml` (7.2.21) |
| NAMESPACE NAME | string | namespace-names | 1 `http://www.w3.org/XML/1998/namespace` (7.2.22) |
| LOCAL NAME | string | local-names | none |
| OTHER NCNAME | string | other-ncnames | none |
| OTHER URI | string | other-uris | none |
| ATTRIBUTE VALUE | string | attribute-values | none |
| CONTENT CHARACTER CHUNK | string | content-character-chunks | none |
| OTHER STRING | string | other-strings | none |
| ELEMENT NAME | name surrogate | element-name-surrogates | none |
| ATTRIBUTE NAME | name surrogate | attribute-name-surrogates | none |

A name surrogate (8.5.2) is (optional PREFIX index, optional NAMESPACE NAME
index, LOCAL NAME index); the prefix index is present only if the namespace
index is. It stands for that qualified name.

### 2.3 Index numbering (6.5, 7.2.12-7.2.23)

- Every table's first entry has index 1 and each addition takes the next
  integer (6.5). Index 0 is never a table entry; where allowed it means the
  empty string (6.5 NOTE, 7.14.6).
- Without an external vocabulary (7.2.12 a, b): restricted alphabets from the
  document start at 16 (3-15 reserved, 7.2.19); encoding algorithms start at
  32 (11-31 reserved, 7.2.20); prefixes and namespace names start at 2
  (7.2.21, 7.2.23); every other table starts at 1.
- With an external vocabulary (7.2.12 c): the initial vocabulary is the final
  vocabulary the URI identifies, and the document's own initial-vocabulary
  entries are appended to it, each table continuing from one plus its highest
  index in the external vocabulary (7.2.19 b, 7.2.20 b, 7.2.21 b, 7.2.23 b). A
  vocabulary defined by text (7.2.14 c, the X3D case) numbers string and name
  tables from 1, PREFIX and NAMESPACE NAME from 2, non-built-in restricted
  alphabets from 16 and non-built-in encoding algorithms from 32 (7.2.15).
- Limits: restricted alphabet and encoding algorithm tables at most 256
  entries; all others at most 2^20 (7.2.18). A processor that cannot make a
  required addition stops with an error (7.13.9, 7.14.9, 7.16.9); a
  string-index beyond the current table size is an error (7.14.8 NOTE 1).

### 2.4 How tables grow while reading (7.13.8, 7.14.8, 7.16.8, 8.1, 8.4.2)

Additions happen in the order the components appear in the stream (8.1.1,
8.1.2 NOTE: the conceptual order is the encoding order).

| What is read | Category / table | Added when |
|---|---|---|
| element or attribute prefix (literal) | PREFIX | always, if literal (7.13.8 b) |
| namespace name of element/attribute (literal) | NAMESPACE NAME | always, if literal |
| local name (literal) | LOCAL NAME | always, if literal |
| namespace attribute prefix / namespace name (literal) | PREFIX / NAMESPACE NAME | always, if literal |
| PI target; entity, unparsed entity, notation name; notation-name | OTHER NCNAME | always, if literal |
| system / public identifier (entity ref, DTD, unparsed entity, notation) | OTHER URI | always, if literal |
| attribute value | ATTRIBUTE VALUE | literal with add-to-table bit `1` (7.14.8 b) |
| character chunk | CONTENT CHARACTER CHUNK | literal with add-to-table bit `1` |
| document version, PI content, comment content | OTHER STRING | literal with add-to-table bit `1` |
| literal qualified name of an element | ELEMENT NAME | always: after its prefix, namespace and local name are resolved (and added if literal), the surrogate of their indexes is appended (7.16.8.2 b) |
| literal qualified name of an attribute | ATTRIBUTE NAME | as above |

A string given by index is never added again. A non-identifying string with
add-to-table `0`, and the empty string (index 0), are never added. Duplicate
entries are legal and harmless to a processor (6.10 NOTE).

An entry added from an EncodedCharacterString stands for the character string
(7.14.8 a returns "the character string"). A decoder can store either the
decoded text or the (format, octets) pair and decode on use; a later index
reference denotes the same character string either way.

## 3. Primitive encodings (Annex C, C.21-C.29)

Each rule starts at a fixed bit of an octet. The "value" field holds
value minus the lower bound of its range.

### 3.1 C.21 Length of a sequence-of (starts on bit 1)

| Range | Bits |
|---|---|
| 1..128 | `0` + 7-bit field |
| 129..2^20 | `1` + `000` padding + 20-bit field |

Used for the item counts of additional-data and of each initial-vocabulary
table.

### 3.2 NonEmptyOctetString lengths (followed by the octets)

C.22, starting on bit 2 (UTF-8 octet strings in the vocabulary header,
literal identifying strings):

| Length | Bits |
|---|---|
| 1..64 | `0` + 6-bit field |
| 65..320 | `10` + `00000` padding + 8-bit field |
| 321..2^32 | `11` + `00000` padding + 32-bit field |

C.23, starting on bit 5 (octets of an EncodedCharacterString started on bit 3):

| Length | Bits |
|---|---|
| 1..8 | `0` + 3-bit field |
| 9..264 | `10` + `00` padding + 8-bit field |
| 265..2^32 | `11` + `00` padding + 32-bit field |

C.24, starting on bit 7 (octets of an EncodedCharacterString started on bit 5):

| Length | Bits |
|---|---|
| 1..2 | `0` + 1-bit field |
| 3..258 | `10` + 8-bit field |
| 259..2^32 | `11` + 32-bit field |

In every case the octets themselves follow and end on bit 8 (C.22.4, C.23.4,
C.24.4).

### 3.3 Integers 1..2^20 or 0..2^20

C.25, range 1..2^20, starting on bit 2:

| Range | Bits |
|---|---|
| 1..64 | `0` + 6-bit field |
| 65..8256 | `10` + 13-bit field |
| 8257..2^20 | `11` + `0` padding + 20-bit field |

C.26, range 0..2^20, starting on bit 2: zero is `1111111`; otherwise C.25.
(`1111111` cannot be a C.25 encoding because C.25's `11` form is followed by
a `0`.)

C.27, range 1..2^20, starting on bit 3:

| Range | Bits |
|---|---|
| 1..32 | `0` + 5-bit field |
| 33..2080 | `100` + 11-bit field |
| 2081..526368 | `101` + 19-bit field |
| 526369..2^20 | `110` + `0000000` padding + 20-bit field |

C.28, range 1..2^20, starting on bit 4:

| Range | Bits |
|---|---|
| 1..16 | `0` + 4-bit field |
| 17..1040 | `100` + 10-bit field |
| 1041..263184 | `101` + 18-bit field |
| 263185..2^20 | `110` + `000000` padding + 20-bit field |

C.29, range 1..256, starting on bit 5 or bit 7: an 8-bit field holding
value-1. Used only for the restricted-alphabet and encoding-algorithm indexes
of an EncodedCharacterString, so it ends on bit 4 or bit 6 of the next octet.

Byte-level reading of these, with `b` the current octet:

- C.25: `b & 0x40 == 0` gives `(b & 0x3F) + 1`; `b & 0x60 == 0x40` gives
  `((b & 0x1F) << 8 | next) + 65`; otherwise `((b & 0x0F) << 16 | next2) + 8257`.
- C.27: `b & 0x20 == 0` gives `(b & 0x1F) + 1`; `b & 0x38 == 0x20` gives
  `((b & 0x07) << 8 | next) + 33`; `== 0x28` gives `((b & 0x07) << 16 |
  next2) + 2081`; `== 0x30` gives `((n1 & 0x0F) << 16 | next2) + 526369`
  where `n1` is the next octet. `b & 0x38 == 0x38` is not an integer here
  (in C.18 it is the literal-name prefix `1111`).
- C.28: `b & 0x10 == 0` gives `(b & 0x0F) + 1`; `b & 0x1C == 0x10` gives
  `((b & 0x03) << 8 | next) + 17`; `== 0x14` gives `((b & 0x03) << 16 |
  next2) + 1041`; `== 0x18` gives `((n1 & 0x0F) << 16 | next2) + 263185`.

## 4. Strings, names and their "literal or index" choices

### 4.1 IdentifyingStringOrIndex (7.13, C.13), starts on bit 1

| First bit | Then |
|---|---|
| `0` | literal: C.22 octet string, UTF-8 (7.13.5); added to the applicable table |
| `1` | string-index by C.25 (1..2^20) |

### 4.2 NonIdentifyingStringOrIndex on bit 1 (7.14, C.14)

| Bits | Then |
|---|---|
| `0` + add-to-table bit | EncodedCharacterString by C.19 (starting on bit 3) |
| `1` | string-index by C.26 (0..2^20); `1` + `1111111` = 0xFF is the empty string |

Used for attribute values (C.4.4), comment content (C.8.3), PI content
(C.5.4) and the document version (C.2.10).

### 4.3 NonIdentifyingStringOrIndex on bit 3 (C.15)

| Bits 3-4 | Then |
|---|---|
| `0` + add-to-table bit | EncodedCharacterString by C.20 (starting on bit 5) |
| `1` | string-index by C.28 (1..2^20), starting on bit 4 |

Used only for character chunks; there is no zero (empty) form, as a chunk is
never empty (7.7.4).

### 4.4 EncodedCharacterString (7.17, C.19, C.20)

Two discriminant bits select the format (C.19.3, C.20.3):

| Bits | Format | Then |
|---|---|---|
| `00` | UTF-8 (7.17.4) | octets |
| `01` | UTF-16BE (7.17.5) | octets |
| `10` | restricted alphabet (7.17.6) | 8-bit index-1 (C.29), then octets |
| `11` | encoding algorithm (7.17.7) | 8-bit index-1 (C.29), then octets |

C.19 starts on bit 3: discriminant in bits 3-4; for `00`/`01` the length is C.23
from bit 5 of the same octet; for `10`/`11` the index occupies bits 5-8 and
bits 1-4 of the next octet and the length is C.23 from bit 5 of that next
octet.

C.20 starts on bit 5: discriminant in bits 5-6; for `00`/`01` the length is C.24
from bit 7; for `10`/`11` the index occupies bits 7-8 and bits 1-6 of the next
octet, and the length is C.24 from bit 7 of that next octet.

The length is of the octet string, not of the character string.

### 4.5 NameSurrogate (7.15, C.16), starts on bit 7

Two presence bits (prefix index, namespace-name index), then for each present
index `'0'` padding + C.25, then `'0'` padding + local-name index by C.25.
Occurs only in the initial vocabulary (7.15.3 NOTE).

### 4.6 QualifiedNameOrIndex on bit 2 (attributes, C.17)

| Bits 2-6 | Then |
|---|---|
| `11110` (`'1111'` + `'0'` padding) | literal: bit 7 prefix present, bit 8 namespace present, then prefix (C.13), namespace name (C.13), local name (C.13) as present |
| otherwise | name-surrogate-index by C.25 from bit 2 |

Byte test: `b & 0x7C == 0x78` is literal. A C.25 integer cannot start `1111`
(its `11` form is followed by `0` padding), so the two are distinct.

### 4.7 QualifiedNameOrIndex on bit 3 (elements, C.18)

| Bits 3-6 | Then |
|---|---|
| `1111` | literal: bit 7 prefix present, bit 8 namespace present, then prefix, namespace name, local name, each C.13 |
| otherwise | name-surrogate-index by C.27 from bit 3 |

Byte test: `b & 0x3C == 0x3C` is literal. If the namespace name is absent the
prefix is absent too (7.16.6).

## 5. Information items

### 5.1 Element (7.3, C.3), starts on bit 2 after the `0` identification bit

1. Bit 2: attributes present (C.3.3).
2. If bits 3-6 are `1110`: namespace attributes (C.3.4). `'1110'` + `'00'`
   padding completes the octet; then each namespace attribute is `'110011'` +
   NamespaceAttribute (section 5.7); then `'1111'` termination + `'000000'`
   padding. That is the octet 0xF0 followed by two padding bits, so the
   element's qualified name starts on bit 3 of the octet after 0xF0.
3. Qualified name by C.18 (bit 3).
4. If attributes are present: each attribute is `'0'` + Attribute (section
   5.2), then `'1111'` termination (C.3.6). No count is written.
5. Children (C.3.7), each starting on bit 1 (pad `'0000'` if the previous bit
   was the fourth):

   | Prefix | Child |
   |---|---|
   | `0` | element |
   | `10` | character chunk (C.7) |
   | `110010` | unexpanded entity reference (C.6) |
   | `11100001` | processing instruction (C.5) |
   | `11100010` | comment (C.8) |

6. `'1111'` termination (C.3.8), always.

Because every attribute and every non-element child ends on bit 8, and every
terminator `'1111'` starts on bit 1 or bit 5, the octet-level picture is:

- In an attribute list, an octet whose first four bits are `1111` ends the list
  (an attribute starts with `0`). Its low nibble is either `0000` (padding:
  children follow) or `1111` (the element's own terminator: no children). So
  0xF0 = "attributes done, children follow" and 0xFF = "attributes done, element
  done".
- In a children list, an octet whose first four bits are `1111` is this
  element's terminator, ending on bit 4. The low nibble then belongs to the
  parent: `0000` padding before the parent's next child, or `1111` the parent's
  terminator. 0xF0 = "element done, parent continues"; 0xFF = "element done and
  parent done". After a 0xFF the grandparent continues at the next octet with no
  padding, since the parent ended on bit 8.
- An element with no attributes and no children ends with its terminator in the
  octet after its name: 0xF0 or 0xFF by the same rule.
- At document level the same applies: the root element's terminator and the
  document's `'1111'` (C.2.12) share 0xFF when the root's last item ended on
  bit 8; if the root ends on bit 4, the document terminator is 0xF0 (`1111` +
  the final `0000` padding).

All six samples end `... F0 A0 FF`: Scene terminator + padding, a chunk by
index 1 (`"\n"`), then X3D terminator + document terminator.

### 5.2 Attribute (7.4, C.4), starts on bit 2

Qualified name by C.17, then normalized value by C.14 (ATTRIBUTE VALUE
category). Ends on bit 8.

### 5.3 Character chunk (7.7, C.7), starts on bit 3

NonIdentifyingStringOrIndex by C.15, CONTENT CHARACTER CHUNK category. Ends on
bit 8. Adjacent chunks are permitted: the content is their concatenation
(7.3.7 NOTE). The samples split each run of whitespace into a `"\n"` chunk and
an indentation chunk.

### 5.4 Comment (7.8, C.8)

`11100010`, then content by C.14, OTHER STRING category.

### 5.5 Processing instruction (7.5, C.5)

`11100001`, then target by C.13 (OTHER NCNAME) and content by C.14 (OTHER
STRING).

### 5.6 Unexpanded entity reference (7.6, C.6)

`110010` + two presence bits (system-identifier, public-identifier); then name
by C.13 (OTHER NCNAME), system identifier by C.13 (OTHER URI), public
identifier by C.13 (OTHER URI) as present.

### 5.7 Namespace attribute (7.12, C.12)

After `110011`: two presence bits (prefix, namespace-name) in bits 7-8, then
prefix by C.13 (PREFIX) and namespace name by C.13 (NAMESPACE NAME) as present.
Absent prefix means a default declaration `xmlns="..."`; absent namespace name
means the empty string (7.12.5, 7.12.6). The C.12.2 NOTE says the type "starts
on the eighth bit"; with six identification bits the presence bits are bits 7
and 8, so it starts on bit 7 and the NOTE is in error.

### 5.8 Document type declaration (7.9, C.9)

At document level only: `110001` + two presence bits (system-identifier,
public-identifier); identifiers by C.13 (OTHER URI); then each child PI as
`11100001` + C.5; then `'1111'` termination. It ends on bit 4, so the next
document child is preceded by `'0000'` padding. Only the identifiers and PIs are
carried; no internal subset. The C.9.2 NOTE says it starts on bit 7, which
agrees.

### 5.9 Notation (C.11) and unparsed entity (C.10)

Notation: after `110000`, two presence bits (system, public), name by C.13,
then the identifiers by C.13. Unparsed entity: after `1101000`, one presence
bit (public), name, system identifier, public identifier if present,
notation-name, each by C.13. C.10.7 says "The value of name is encoded" a second
time where notation-name is meant (7.10.1 lists notation-name last); read the
fourth string as notation-name.

## 6. Restricted alphabets (7.17.6, clause 9)

Built-in entries:

| Index | Name | Characters in order (values 0..14) |
|---|---|---|
| 1 | numeric (9.1) | `0123456789-+.e` and SPACE |
| 2 | date and time (9.2) | `0123456789-:TZ` and SPACE |

Decoding an octet string in restricted alphabet A with |A| characters:

1. Field width = the number of bits needed to write |A| as an unsigned integer
   (7.17.6.3: last value + 1). For the 15-character built-ins it is 4 bits;
   for a 24-character alphabet 5; for 32 characters 6.
2. Read fields most significant bit first; each value v < |A| is character
   A[v].
3. A field of all ones cannot be a character (7.17.6.3 NOTE 1); the encoder pads
   the last octet with `1` bits (7.17.6.5), so stop at an all-ones field or when
   fewer bits than one field remain.

## 7. Built-in encoding algorithms (clause 10)

"Word" (10.1.2) is a maximal run of non-SPACE characters; lists are joined by
single SPACE characters.

| Index | Name | Octets | Character string rebuilt |
|---|---|---|---|
| 1 | hexadecimal (10.2) | any octets | two uppercase hex digits per octet, high nibble first; even length; no whitespace |
| 2 | base64 (10.3) | any octets | RFC 2045 base64 of the octets, no whitespace |
| 3 | short (10.4) | 2 octets per word, big-endian two's complement | decimal integers, `-` sign, no leading zeros, SPACE-separated |
| 4 | int (10.5) | 4 octets per word, as above | as above |
| 5 | long (10.6) | 8 octets per word, as above | as above |
| 6 | boolean (10.7) | bits 1-4 of octet 1 = number of unused bits in the last octet; values from bit 5 of octet 1 on, then bits 1-8 of following octets; `0` false, `1` true | `true`/`false` words |
| 7 | float (10.8) | 4 octets per word, IEEE 754 single, big-endian | float words |
| 8 | double (10.9) | 8 octets per word, IEEE 754 double, big-endian | double words |
| 9 | uuid (10.10) | 16 octets per word | `8-4-4-4-12` lowercase hex groups (X.667 6.4) |
| 10 | cdata (10.11) | UTF-8 of the string | the string; its use marks the string as a whole CDATA section |

Details:

- boolean: count = 8 × octets − 4 − unused. The first octet may also be the
  last, holding up to three unused bits (10.7.3 NOTE).
- float and double: the original string matched the canonical lexical form of
  XML Schema Part 2, 3.2.4 / 3.2.5, with uppercase `E` (10.8.1 a, d; 10.9.1). A
  decoder that must reproduce the character string exactly writes that canonical
  form. For X3D, 19776-3 4.2.3 says decompressed values "shall be numerically
  equal to, but need not necessarily match the form of, the original values".
- short/int/long: the word lexical rules (10.4.1 a-g) exclude `+`, leading
  zeros and `-0`.
- cdata: if used at all in a document, every character string that was a CDATA
  section uses it (10.11.3).

Algorithms from the document or an external vocabulary take indexes 32 and up
(7.2.20); X3D's are in section 9.3.

## 8. Restrictions worth knowing (clause 11)

There are no `[base URI]` properties (7.2.31, 7.3.9), `[all declarations
processed]` is true (11.3 a), and attribute values, comments and PI contents
are at most 2^32 characters (11.3 j).

## 9. X3D-specific rules (ISO/IEC 19776-3)

### 9.1 File form

- Header: optional XML declaration then the Fast Infoset header bits
  (19776-3 4.2.4, citing X.891 12.3).
- The `X3D` element carries two added SFString attributes, `binaryVersion`
  (e.g. `"3.3"`) and `serializerVersion` (`"Fast infoset 2004"`)
  (19776-3 4.2.4). Neither name is in Table A.3, so they would arrive as literal
  attribute names. None of the samples carries them.
- The whole file may be gzip-compressed (RFC 1952), extension `.x3db.gz`
  (19776-3 4.5.1, 4.5.2). Test for 0x1F 0x8B before the `E0 00` check.
- File extension `.x3db`; MIME type `model/x3d+binary` (19776-3 4.5.2).
- The decoded XML is in "X3D canonical form" (19776-3 4.2.3): attributes with
  default values are omitted; DEF, USE and containerField come first, then the
  rest alphabetically; MFString values are `"..."` strings; comments are
  preserved; CDATA sections stay CDATA. The samples do not follow the
  alphabetical rule (HelloWorld's Viewpoint is DEF, fieldOfView, position,
  description, centerOfRotation), and they separate MFString items with commas
  (`"EXAMINE","WALK","FLY","ANY"`) where 4.2.3 calls for single spaces. Commas
  are whitespace in X3D field syntax, so either form parses.
- Prototype instances appear only as `ProtoInstance`/`fieldValue`, never as
  native tags (19776-3 4.2.5).
- Node compressors (19776-3 4.3.1, 4.4.3) are signalled in-band by a
  `MetadataSet name=".x3db"` with `MetadataInteger name="encoding"` and
  `name="payload"`. The registry of compressor numbers is Annex B
  (`nodecompressors.html`), which defines none. A decoder can leave such
  MetadataSets in place.

### 9.2 Field value encodings (19776-3 5.1-5.6)

All field values end on an octet boundary (5.1.2). The permitted algorithms per
X3D field type:

| X3D field type | Lossless | Lossy |
|---|---|---|
| SF/MFBool | boolean (6) | none |
| SF/MFFloat, SF/MFVec2f, SF/MFVec3f, SF/MFVec4f, SF/MFRotation, SF/MFColor, SF/MFColorRGBA, SF/MFMatrix3f, SF/MFMatrix4f | float (7), zlibFloatArrayEncoder | QuantizedFloatArrayEncoder, QuantizedzlibFloatArrayEncoder |
| SF/MFDouble, SF/MFVec2d, SF/MFVec3d, SF/MFVec4d, SF/MFMatrix3d, SF/MFMatrix4d | double (8), zlibDoubleArrayEncoder | QuantizedDoubleArrayEncoder, QuantizedzlibDoubleArrayEncoder |
| SF/MFTime | double (8) only (5.6.15) | none allowed |
| SFInt32 | int (4) only (5.6.7) | none |
| MFInt32 | int (4), RangeIntArrayEncoder, DeltazlibIntArrayEncoder | none |
| SF/MFImage | RangeIntArrayEncoder, DeltazlibIntArrayEncoder (5.6.6) | none |
| SF/MFString | plain string, no algorithm (5.6.14) | none |
| SF/MFNode | elements (5.6.12) | none |
| CDATA (script/shader source) | cdata (10) (5.2.3) | none |

Any value may also be a plain UTF-8 string (5.2.1: "By default all field values
are written in String form"). Algorithms other than X.891's and these are
invalid (5.1.2).

### 9.3 X3D encoding algorithm table (19776-3 A.2.5, Table A.5)

| Index (per Table A.5) | URI |
|---|---|
| 32 | `encoder://web3d.org/QuantizedFloatArrayEncoder` |
| 33 | `encoder://web3d.org/DeltazlibIntArrayEncoder` |
| 34 | `encoder://web3d.org/QuantizedzlibFloatArrayEncoder` |
| 35 | `encoder://web3d.org/zlibFloatArrayEncoder` |
| 36 | `encoder://web3d.org/QuantizedDoubleArrayEncoder` |
| 37 | `encoder://web3d.org/zlibDoubleArrayEncoder` |
| 38 | `encoder://web3d.org/QuantizedzlibDoubleArrayEncoder` |
| 39 | `encoder://web3d.org/RangeIntArrayEncoder` |

The 3.2 and 3.3 editions and the v4 CD have identical Table A.5s. Table A.5 says
the table is "preloaded", so these indexes apply without the document listing
the URIs. 19776-3 5.2.1 also says that if an encoder is used "this URI shall be
added to the Encoding Algorithm Table described in 8.3 of ISO/IEC 24824-1". A
document that does list them in its initial vocabulary, on top of the
preloaded table, would number its own copies from 40 (7.2.20 b). None of the
samples lists any.

The samples write their delta-zlib integer arrays with the C.29 field 0x21,
which is index 34, not 33. See section 10.3.

### 9.4 X3D encoder byte layouts (19776-3 5.3-5.5)

None of the quantized, zlib-float, double or range encoders occurs in any file
examined, so these layouts are from the text alone. The text leaves several
points open; they are listed as questions under each encoder.

zlib (5.3): RFC 1950 zlib format (two-octet header, deflate data, Adler-32).
The text names only "the zlib library"; the samples' streams begin `78 01`.

QuantizedFloatArrayEncoder (5.4.1), `encoder://web3d.org/QuantizedFloatArrayEncoder`:

- Header 9 bits: exponent bit count in 3 bits, mantissa bit count in 5 bits,
  sign bit count in 1 bit (0 means all values positive). Then each value in
  exponent + mantissa + sign bits, packed continuously from bit 2 of the second
  octet ("using the extra seven bits of the second byte"), with `0` bits padding
  the last octet.
- Count = floor((octets × 8 − 9) / (exponent + mantissa + sign)).
- "A custom value is selected for the exponent, mantissa and sign bits … The
  bias of 127 is still used."
- Ambiguous: "The exponent is encoded using three bits, giving a range of 1-8.
  Zero exponent bits cannot be used." Three bits hold 0-7, so either the field
  holds count−1, or 0 means 8. The worked example writes exponent count 4 as
  `100` and mantissa count 4 as `00100`, so the field holds the count directly,
  and 8 would have to be `000`.
- Ambiguous: the order of sign, exponent and mantissa within a value, how a
  reduced-width exponent relates to the bias of 127, and how the mantissa is
  truncated or rounded. The worked example (values 0.42, −1, 0.1972 with 4/4/1
  bits; octets `100 00100`, `1 0110101`, `10 100000`, `000 01011`,
  `0010 0000`) gives per-value bit strings `011010110`, `100000000`,
  `010110010`. −1 has a leading `1` and zeros elsewhere, consistent with sign
  first and an exponent field of 0 for 2^0. No combination tried (sign, exponent
  and mantissa in any order; exponent as low bits of the biased exponent, as
  two's complement of the unbiased exponent, or rebiased by 7 or 8; mantissa
  truncated, rounded, or low bits) reproduces all three values. The example
  labels the bit `1` in octet 2 "Sign(0)" while the stated sign count is 1. The
  example cannot be used to settle the reconstruction rule.

QuantizedzlibFloatArrayEncoder (5.4.3):

- Header 9 bits as above, then `0000000` padding (2 octets total), then the
  number of values in 4 octets (byte order not stated), then a zlib stream of
  "the float values".
- Ambiguous: whether the zlib stream holds the packed quantized bits or IEEE
  floats; the per-value layout carries the same open questions as 5.4.1.

zlibFloatArrayEncoder (5.4.2): "The array of floats is sent to the zlib library
unmodified." No count or byte order is stated; big-endian IEEE single, as in
X.891 float (10.8.3), is the likely reading. Length = inflated size / 4.

QuantizedDoubleArrayEncoder (5.4.4):

- Header 11 bits: exponent count 4 bits ("range of 0-15"), mantissa count 6
  bits, sign 1 bit; bias 1023. Count = floor((octets × 8 − 11) / (e + m + s)).
- Ambiguous: the text repeats "using the extra seven bits of the second byte",
  copied from 5.4.1, which disagrees with an 11-bit header (only five bits of
  the second octet remain). An exponent count of 0 is permitted here, unlike the
  float case.

zlibDoubleArrayEncoder (5.4.5): zlib of the doubles; the same open questions as
5.4.2.

QuantizedzlibDoubleArrayEncoder (5.4.6): the 5.4.4 header and data, "then encoded
using the zlib library". Whether the header is inside or outside the zlib stream,
and whether a count is present, are not stated.

RangeIntArrayEncoder (5.5.1), `encoder://web3d.org/RangeIntArrayEncoder`:

- numBits as one octet, then shift as a 32-bit integer (byte order and
  signedness not stated), then each value in numBits bits, padded with `0` bits
  to an octet boundary. Value = stored − shift, with shift = −minValue.
- numBits = ceiling(log2(maxValue − minValue)) is one bit short when the range
  is an exact power of two (range 0..4 needs 3 bits, formula gives 2) and is
  undefined when all values are equal. A decoder should trust the numBits octet.
- Count = "length / numBits": the length meant is presumably the data octets × 8
  after the 5-octet header. With numBits < 8, padding can be mistaken for extra
  values (numBits 1 and 3 values leave 5 padding bits, read as 5 extra zeros).
  The text gives no count field.

DeltazlibIntArrayEncoder (5.5.2), `encoder://web3d.org/DeltazlibIntArrayEncoder`:

- Text: span (0-255) in 8 bits, then the value count in 4 octets, then a zlib
  stream of the deltas. "The first Span values are the original values, the rest
  are deltas", d[i] = v[i] − v[i−span]. Example: `0,1,2,-1,3,4,5,-1,6,9,8,-1`
  with span 4 → `0,1,2,-1,3,3,3,0,3,5,3,0`.
- The samples do this differently; see 10.3, which every delta-zlib value in 33
  sample files decodes by.

### 9.5 X3D external vocabulary (19776-3 Annex A)

URI: `urn:web3d:x3d:fi-vocabulary-3.3` (3.3 edition, A.2.1);
`urn:web3d:x3d:fi-vocabulary-3.2` (3.2 edition). The v4 CD names both
`urn:web3d:x3d:fi-vocabulary-3.3` and `urn:web3d:x3d:fi-vocabulary-4.0`
with the same tables as 3.3. The 3.1 edition names no URI and numbers its
tables from 0.

Contents:

- Element names (A.2.2, Table A.2): name surrogates with no prefix or namespace
  ("The optional value prefix and namespace attributes are blank"). 3.3: 252
  entries, IDs 1-252. 3.2: 233 entries; identical to the first 233 of 3.3 except
  entry 224, `TexCoordDamper` in 3.2 and `TexCoordDamper2D` in 3.3.
- Attribute names (A.2.3, Table A.3): as above. 3.3: 546 entries, IDs 1-546.
  3.2: 516 entries; identical to the first 516 of 3.3 except entry 350,
  `mustOutput` in 3.2 and `forceOutput` in 3.3.
- Attribute values (A.2.4, Table A.4): 1 `false`, 2 `true`.
- Encoding algorithms (A.2.5): section 9.3.
- Restricted alphabets, prefixes, namespace names, OTHER NCNAME, OTHER URI,
  content chunks, other strings: none listed.

The full 3.3 lists are in Appendix A and Appendix B. Section 10.2 gives the
attribute numbering the sample files use, which differs from Table A.3 above
index 53.

Not specified by Annex A:

- The LOCAL NAME table. A name surrogate is a triple of string-table indexes
  (8.5.2), so the vocabulary implies a LOCAL NAME table holding these names, but
  its order is not given (element names first or attribute names first, or
  interleaved). No spelling appears in both Table A.2 and Table A.3, so the
  table would hold 252 + 546 = 798 local names under 3.3. A decoder needs the LOCAL NAME table only when a literal
  qualified name gives its local name by string-index (C.13 `1` + index), or to
  number the local names a document adds (they continue from the table's
  highest index, 7.2.15/7.2.21). None of the samples does either. Neither
  question has an answer in the published text.
- Whether "IDs" are FI vocabulary table indexes. They are, for the 3.3/3.2
  numbering from 1: the element IDs match the samples exactly (section 10.1).
- The next free name-surrogate index for literal names a document adds: by
  7.2.15 it is one plus the vocabulary's highest, so 234 (elements) under 3.2
  and 253 under 3.3; the attribute value depends on 10.2.

## 10. Observed in the sample files

Checked first with a structure dumper written from Annex C, over the six
samples in section 11 and 27 more ConformanceNist files (33 in all; every
file parses to its last octet), and then with `vrml.x3d.fastinfoset` over
the 1071 non-empty `.x3db` files of the ConformanceNist and Vrml2Sourcebook
archives (section 10.5). Each decoded tree was compared with the `.x3d` published beside it.

The `.x3d` beside each `.x3db` is not the document the `.x3db` was made from.
The `.x3db` files were generated from an earlier revision: different `meta`
lists, `version='3.1'` in the binary against later versions in the XML,
attributes since removed (Viewpoint `fieldOfView='0.7854'`), a ROUTE `toField`
of `translation` where the XML now says `set_translation`, and child order
differences (Coordinate/Color, Appearance/geometry). Comparisons have to allow
for this.

### 10.1 Header and element names

- No XML declaration; header `E0 00 00 01`; document presence octet `0x20`
  (initial vocabulary only); initial-vocabulary presence bits
  `1000000000000` (external vocabulary only).
- External vocabulary URI in every file: `urn:web3d:x3d:fi-vocabulary-3.2`.
- No DTD, no comments, no PIs, no namespace attributes, no literal qualified
  names. The `xmlns:xsd` and `xsd:noNamespaceSchemaLocation` attributes in the
  XML are absent from the binary.
- Every element name is a name-surrogate index, and the indexes equal Table
  A.2's IDs: across the 33 files the Scene element sequences equal the XML's
  except for the reordering listed above. Seen: 1-7, 9, 11, 13, 14, 16, 19, 29,
  30, 31, 36, 37, 43, 44, 50, 55, 58, 61, 78, 91, 105, 110, 112-115, 119, 125,
  128, 130, 136, 138, 139, 142, 143, 145.
- Attribute value index 1 resolves to `false` and 2 to `true` (IndexedFaceSet
  `solid`, TimeSensor `loop`), and the first literal added to the ATTRIBUTE
  VALUE table is referenced later as index 3: Table A.4 is preloaded as stated.

### 10.2 Attribute names: one extra entry after index 53

Attribute name indexes match Table A.3 (3.2 or 3.3, identical in this range)
up to 53. From 57 up they are Table A.3's ID plus one. Evidence (index in file
→ attribute in the XML, identified by equal values; Table A.3 ID in brackets):

| File index | Attribute | Table A.3 ID |
|---|---|---|
| 1, 2, 4-8 | DEF, USE, fromNode, fromField, toNode, toField, name | same |
| 10, 15, 17, 18, 21, 22, 25 | color, colorPerVertex, rotation, scale, translation, url, point | same |
| 29, 30, 31, 41-47 | diffuseColor, emissiveColor, shininess, radius, size, height, solid, ccw, key, keyValue | same |
| 50, 51, 53 | position, orientation, bboxSize | same |
| 57 | accessType | 56 |
| 75, 76 | axisOfRotation, backUrl | 74, 75 |
| 84, 92 | centerOfRotation, content | 83, 91 |
| 98, 99, 103 | creaseAngle, crossSection, cycleInterval | 97, 98, 102 |
| 112, 115 | description, directOutput | 111, 114 |
| 138, 155, 156, 164, 166 | fieldOfView, groundAngle, groundColor, image, info | 137, 154, 155, 163, 165 |
| 175, 197 | justify, loop | 174, 196 |
| 241 | profile | 240 |
| 270, 275, 280, 282, 290 | skyColor, spine, string, style, title | 269, 274, 279, 281, 289 |
| 306, 316 | type, version | 305, 315 |
| 325, 326, 328, 329 | xDimension, xSpacing, zDimension, zSpacing | 324, 325, 327, 328 |

So the vocabulary these files were written with has one attribute name more
than Table A.3, at index 54, 55 or 56 (Table A.3's 54-56 are `AS`, `InlineDEF`,
`accessType`). Which name it is, and whether the shift holds above 329, cannot
be read from these files or any published edition. Neither the 3.1 table (0-based,
with duplicate `center` and `coordIndex` entries) nor the 3.2/3.3/v4 tables
give this numbering.

Further oddities, recorded as found:

- Every `meta` element carries attribute 46 (`key` in Table A.3, confirmed as
  `key` by PositionInterpolator) and attribute 92 (`content`) with the same
  value, after `name` (8). A decoder following the table yields
  `<meta name="..." key="..." content="..."/>`.
- In ConformanceNist `SpecialGroups/Inline/test_bboxsizesame.x3db`, Inline
  carries attributes 53, 54 and 330, all `2 2 2`; the XML has only
  `bboxSize='2 2 2'`.

For a reader of these files: map 1-53 by Table A.3, 57 and up by Table A.3
ID − 1, and treat 54-56 as unresolved.

### 10.3 Encoding algorithms in use

Only two occur in the 33 files:

- Built-in float, field octet 0x06 (index 7): every float-typed field (SFVec3f,
  SFRotation, SFColor, MFFloat keys, ElevationGrid height, Extrusion spine and
  scale, Background colours and angles). Big-endian IEEE single, as in 10.8.
- Field octet 0x21 (index 34 by C.29): every MFInt32 and SFImage
  (IndexedFaceSet coordIndex/texCoordIndex, PixelTexture image); 42 values.
  Table A.5 gives index 33 for DeltazlibIntArrayEncoder and 34 for
  QuantizedzlibFloatArrayEncoder. The octets are integers, so these files write
  the delta-zlib encoder as 34; read 34 as either an off-by-one in the
  encoder's index or a different table order. With no float use of 34 in any
  sample, the two readings cannot be told apart.

Layout of the delta-zlib values in the samples:

| Octets | Content |
|---|---|
| 0-3 | value count, 32-bit big-endian unsigned |
| 4 | span, 0-255 |
| 5- | zlib stream (RFC 1950, header `78 01`) inflating to count × 4 octets of 32-bit big-endian signed integers |

This places the count before the span; 19776-3 5.5.2's text gives span first.
Reconstruction that reproduces all 42 values exactly:

```
v[i] = s[i] - 1                     for i < span (or every i if span == 0)
v[i] = s[i] - 1 + v[i - span]       for i >= span
```

Every stored value carries +1 relative to 5.5.2's description (span 0, used for
SFImage, stores v + 1 with no differencing; image `2 2 3 0xFF0000 …` is stored
`3, 3, 4, 16711681, …`). Span 5 was used for coordIndex of quads with `-1`
separators.

### 10.4 Strings and tables

- Literal attribute values in the 33 files: 1089 UTF-8 with add-to-table `1`,
  448 UTF-8 with add-to-table `0`, and 344 algorithm-encoded, all with
  add-to-table `0`. Repeats come back as indexes into ATTRIBUTE VALUE and
  CONTENT CHARACTER CHUNK, and every such index resolves to the right string
  when the tables number from 1 (ATTRIBUTE VALUE after the preloaded `false` and
  `true`) and only add-to-table `1` literals are added.
- MFString values are plain UTF-8, `"a","b"` with commas.
- Some numeric values are plain UTF-8 strings rather than encoded (Viewpoint
  `fieldOfView='0.7854'`, TimeSensor `cycleInterval='5.0'`, ElevationGrid
  `xDimension='6'`); a decoder has to accept both forms for any field.

### 10.5 The whole of two archives

Read with `vrml.x3d.fastinfoset` and the vocabulary of section 10.2: all
1071 non-empty `.x3db` files of the ConformanceNist and Vrml2Sourcebook
archives (106 more are published empty), every one naming
`urn:web3d:x3d:fi-vocabulary-3.2`.

- Literal attribute names a document adds are numbered from 1026, in all
  75 files that add one (`global`, `axisRotation`, `autoRefresh`,
  `autoRefreshTimeLimit`, `forceTransitions`, `collide`). The ATTRIBUTE NAME
  table these files were written against has 1025 entries. No file refers
  to an entry between 518 and 1025. No file adds an element name.
- Of 54-56, only 54 occurs: on `Inline`, 31 times, holding the same value
  as `bboxSize` (53).
- Values written a second time under a name the node does not take, each
  holding the value of a field the node does have: an Anchor's `url` also
  as `autoRefresh`, `autoRefreshTimeLimit` (literal names), `load` (193) and
  `visible` (330); an Inline's `bboxSize` also as 54 and `visible` (330); a
  LOD's `range` also as `forceTransitions` (literal); a Viewpoint's
  `centerOfRotation` also as `retainUserOffsets` (450).
- With those set aside, each decoded attribute name is one the `.x3d`
  beside the file gives that element, or one the later `.x3d` revision
  dropped. 623 of the 1071 build the `.x3d`'s scene graph exactly; the rest
  differ where the revisions differ (routes to `translation` rather than
  `set_translation`, absolute `file:///c:/x3d-code/` URLs, explicit
  defaults, older field values).

## 11. Sample files

Downloaded on 2026-10-07 and read as data only. The `.x3db` files of the
committed corpus subset (`tests/fixtures/x3d-corpus`) are from the same
archives.

Licence for all: the "Web3D Consortium Open-Source License for Models and
Software" at `https://www.web3d.org/x3d/content/examples/license.html`
(BSD-style: redistribution in source and binary form with the copyright notice,
conditions and disclaimer retained; no use of the Web3D Consortium name for
endorsement). Each `.x3d` names that licence in a `meta name='license'`
(`../../license.html` relative for ConformanceNist). The ConformanceNist files
also carry a NIST disclaimer `meta` and credit Michael Kass (NIST) as creator
and Don Brutzman as translator; HelloWorld credits Don Brutzman.

| File | URL | Bytes | SHA-256 |
|---|---|---|---|
| HelloWorld.x3db | https://www.web3d.org/x3d/content/examples/HelloWorld.x3db | 1551 | b1dea7d97417e33fc51b37946702924f1bafd8207c17aa4b2b9f12beb5b76cbb |
| HelloWorld.x3d | https://www.web3d.org/x3d/content/examples/HelloWorld.x3d | 3563 | eb3a44140eebce91aa8b9433fc05f90baea6110cc1df281b7b80be13c445c174 |
| default_box.x3db | https://www.web3d.org/x3d/content/examples/ConformanceNist/Geometry/Box/default_box.x3db | 3177 | 7b00790951b6cfa3c714c70a2b1391ad7022ff005e541332a1b44e2c3c513c7f |
| default_box.x3d | https://www.web3d.org/x3d/content/examples/ConformanceNist/Geometry/Box/default_box.x3d | 3204 | a79fb609afded369bf1b68f013ba4cb262204e46ca92a4fc561b9ce6709a4bda |
| coordIndex_color.x3db | https://www.web3d.org/x3d/content/examples/ConformanceNist/Geometry/IndexedFaceSet/coordIndex_color.x3db | 4343 | 172b0cc99368ff99d6d3d06486766497be5e21ef32746822b89edf5f9efc2510 |
| coordIndex_color.x3d | https://www.web3d.org/x3d/content/examples/ConformanceNist/Geometry/IndexedFaceSet/coordIndex_color.x3d | 3990 | 29fb04ee7bc5ec18a8537662136bbeb5da711ab678335a8f0688e21a8b4acce5 |
| simple.x3db | https://www.web3d.org/x3d/content/examples/ConformanceNist/Interpolators/PositionInterpolator/simple.x3db | 4319 | 444e36c9f33b15be8e519fd404009dcd414d9f43c79787b11e95322f4bde3d21 |
| simple.x3d | https://www.web3d.org/x3d/content/examples/ConformanceNist/Interpolators/PositionInterpolator/simple.x3d | 3890 | 2be1211d223679840e87ebc0b98a3a4ab5daa9a10c56e7ac4725f5f06d898b98 |
| default_grid.x3db | https://www.web3d.org/x3d/content/examples/ConformanceNist/Geometry/ElevationGrid/default_grid.x3db | 3545 | 7333125b2c22f35ce867e6940816866c57ee07b0c64edb5f210b26bdcec6adec |
| default_grid.x3d | https://www.web3d.org/x3d/content/examples/ConformanceNist/Geometry/ElevationGrid/default_grid.x3d | 3481 | 8cca9e6bdaac119d1142b02779f1e1df21835db4bc60ba4df0aec98bdf7fbb10 |
| IndexedFaceCoord.x3db | https://www.web3d.org/x3d/content/examples/ConformanceNist/GeometricProperties/Coordinate/IndexedFaceCoord.x3db | 10491 | 1a2b0d4c568261ab93aa05deebb747711073d4369658456c512b09a7a1b27e49 |
| IndexedFaceCoord.x3d | https://www.web3d.org/x3d/content/examples/ConformanceNist/GeometricProperties/Coordinate/IndexedFaceCoord.x3d | 23080 | 99219df26758603f3aecf6cb53d39d932bd034c83292170545ef605a69cd991a |

What each exercises:

- HelloWorld: chunks by index, `meta`, DEF/USE, float arrays (built-in 7),
  MFString, `false` from the preloaded attribute value table, elements with and
  without attributes and children.
- default_box: smallest scene; empty elements (`Material`, `Box`).
- coordIndex_color: delta-zlib coordIndex (span 5), Coordinate and Color
  float arrays.
- simple: TimeSensor `loop` = `true` by index 2, PositionInterpolator key and
  keyValue floats, ROUTEs with string-index node names.
- default_grid: ElevationGrid height floats, attributes above 300.
- IndexedFaceCoord: a 2420-value delta-zlib coordIndex; larger C.22/C.23 lengths.

The Web3D archive pages list a `.x3db` beside every ConformanceNist example
(e.g. `ConformanceNist/Geometry/Box/default_boxIndex.html` links
`default_box.x3db`).

## 12. HelloWorld.x3db, first 64 octets

```
000000 e0 00 00 01 20 10 00 1e 75 72 6e 3a 77 65 62 33
000010 64 3a 78 33 64 3a 66 69 2d 76 6f 63 61 62 75 6c
000020 61 72 79 2d 33 2e 32 60 6a 40 b0 48 00 49 6d 6d
000030 65 72 73 69 76 65 40 fb 42 33 2e 33 f0 90 0a 20
```

| Offset | Octets | Bits | Meaning |
|---|---|---|---|
| 00-01 | `e0 00` | `1110000000000000` | identification (12.6) |
| 02-03 | `00 01` | | version 1 (12.7) |
| 04 | `20` | `0` `0100000` | padding (12.8); presence: initial-vocabulary only (C.2.3) |
| 05-06 | `10 00` | `000` `1000000000000` | padding; initial-vocabulary presence: external-vocabulary only (C.2.5.1) |
| 07 | `1e` | `0` `0` `011110` | padding (C.2.5.2); C.22 short length, 30 + 1 = 31 |
| 08-26 | | | `urn:web3d:x3d:fi-vocabulary-3.2` (31 octets) |
| 27 | `60` | `0` `1` `100` `000` | element (C.2.11.2); attributes present (C.3.3); C.27 `100` form, high 3 bits of 11-bit field |
| 28 | `6a` | | low 8 bits: 0b00001101010 = 106; 106 + 33 = 139 = `X3D` (Table A.2) |
| 29 | `40` | `0` `10` `00000` | attribute (C.3.6.1); C.25 `10` form, high 5 bits of 13 |
| 2a | `b0` | | 176 + 65 = 241 = `profile` (Table A.3 says 240; section 10.2) |
| 2b | `48` | `0` `1` `00` `10` `00` | literal (C.14.3), add-to-table, UTF-8 (C.19.3.1), C.23 `10` form + `00` padding |
| 2c | `00` | | length 0 + 9 = 9 |
| 2d-35 | | | `Immersive`; becomes ATTRIBUTE VALUE 3 |
| 36-37 | `40 fb` | `0` `10` `00000` + `fb` | attribute, C.25: 251 + 65 = 316 = `version` (Table A.3: 315) |
| 38 | `42` | `0` `1` `00` `0` `010` | literal, add-to-table, UTF-8, C.23 short length 2 + 1 = 3 |
| 39-3b | | | `3.3`; ATTRIBUTE VALUE 4 |
| 3c | `f0` | `1111` `0000` | end of attributes (C.3.6.2); padding before the first child (C.3.7.1) |
| 3d | `90` | `10` `0` `1` `00` `0` `0` | character chunk (C.3.7.5); literal (C.15.3), add-to-table; UTF-8 (C.20.3.1); C.24 short length 0 + 1 = 1 |
| 3e | `0a` | | `"\n"`; CONTENT CHARACTER CHUNK 1 |
| 3f | `20` | `0` `0` `100` `000` | element, no attributes, C.27 `100` form; the next octet `6e` completes 110 + 33 = 143 = `head` |

The X3D element of this file has no `binaryVersion` or `serializerVersion`
attribute (19776-3 4.2.4).

## 13. Ambiguities and conflicts, in one list

1. Attribute name numbering: the published Table A.3 (3.2, 3.3, v4 CD) does not
   match Web3D's own `.x3db` files above index 53; they use one extra entry at
   54-56 whose name is unknown (10.2).
2. Delta-zlib algorithm index: Table A.5 says 33; the files use 34 (10.3).
3. Delta-zlib layout: text says span then count; files have count then span
   (10.3).
4. Delta-zlib values: the files store every value +1 relative to the text's
   description and example (10.3).
5. Quantized float: exponent-count field range ("1-8" in 3 bits), value bit
   order, exponent rebiasing and mantissa rounding are unstated, and the worked
   example matches no tried reading (9.4).
6. Quantized double: header length (11 bits) disagrees with "the extra seven
   bits of the second byte" (9.4).
7. zlib float/double: byte order and any count prefix unstated (9.4).
8. Quantized zlib float/double: what goes into the zlib stream unstated; count
   byte order unstated; double variant gives no count (9.4).
9. Range int: numBits formula off by one at powers of two; no value count;
   shift signedness and byte order unstated (9.4).
10. LOCAL NAME, PREFIX and NAMESPACE NAME table contents of the X3D external
    vocabulary are not given, so a literal name referencing a preloaded local
    name by index, or the numbering of newly added local names, cannot be
    determined (9.5).
11. Which vocabulary a `...-3.2` URI denotes when the published 3.2 table and
    the files disagree (9.5, 10.2).
12. X.891 notes: C.12.2 NOTE "eighth bit" should be seventh (5.7); C.10.7
    repeats "name" for notation-name (5.9). Both are notes or obvious slips; the
    ASN.1 in 7.10.1 and the bit counts settle them.
13. 19776-3 4.2.3 calls for space-separated MFString values and alphabetical
    attributes after DEF/USE/containerField; the files use commas and do not
    sort (9.1).
14. 19776-3 4.2.4 EXAMPLE 2 shows an XML declaration missing its `?`, and a
    35-bit header string where X.891 has 33 bits (1.1, 1.2).

## 14. Not obtained

- X.891 Annex A (the ASN.1 and ECN modules, the normative form of Annex C) and
  Annex D (worked examples) were in the downloaded PDF but not transcribed here;
  Annex C was used instead. Any corrigendum or amendment to X.891 | ISO/IEC
  24824-1 after 05/2005 was not looked for.
- ISO/IEC 19776-3 Annex B (node compressor registry) lists no compressors; no
  registry entries were found.
- No sample uses the quantized, zlib-float, double or range-int encoders,
  restricted alphabets, UTF-16, comments, PIs, DTDs, namespaces or literal
  names. Those parts of these notes are from the text only.
- No published list of the vocabulary actually behind
  `urn:web3d:x3d:fi-vocabulary-3.2` as Web3D's files use it (10.2).

## Appendix A. Table A.2, element name table (19776-3 3.3), ID = name-surrogate index

| ID | Name | ID | Name | ID | Name | ID | Name |
|---|---|---|---|---|---|---|---|
| 1 | `Shape` | 64 | `GeoLOD` | 127 | `TextureCoordinateGenerator` | 190 | `GeoProximitySensor` |
| 2 | `Appearance` | 65 | `GeoLocation` | 128 | `TimeSensor` | 191 | `GeoTransform` |
| 3 | `Material` | 66 | `GeoMetadata` | 129 | `TimeTrigger` | 192 | `Layer` |
| 4 | `IndexedFaceSet` | 67 | `GeoOrigin` | 130 | `TouchSensor` | 193 | `LayerSet` |
| 5 | `ProtoInstance` | 68 | `GeoPositionInterpolator` | 131 | `TransmitterPdu` | 194 | `Layout` |
| 6 | `Transform` | 69 | `GeoTouchSensor` | 132 | `TriangleFanSet` | 195 | `LayoutGroup` |
| 7 | `ImageTexture` | 70 | `GeoViewpoint` | 133 | `TriangleSet` | 196 | `LayoutLayer` |
| 8 | `TextureTransform` | 71 | `HAnimDisplacer` | 134 | `TriangleSet2D` | 197 | `LinePickSensor` |
| 9 | `Coordinate` | 72 | `HAnimHumanoid` | 135 | `TriangleStripSet` | 198 | `MotorJoint` |
| 10 | `Normal` | 73 | `HAnimJoint` | 136 | `Viewpoint` | 199 | `OrientationChaser` |
| 11 | `Color` | 74 | `HAnimSegment` | 137 | `VisibilitySensor` | 200 | `OrientationDamper` |
| 12 | `ColorRGBA` | 75 | `HAnimSite` | 138 | `WorldInfo` | 201 | `OrthoViewpoint` |
| 13 | `TextureCoordinate` | 76 | `IMPORT` | 139 | `X3D` | 202 | `ParticleSystem` |
| 14 | `ROUTE` | 77 | `IS` | 140 | `component` | 203 | `PickableGroup` |
| 15 | `fieldValue` | 78 | `Inline` | 141 | `connect` | 204 | `PointEmitter` |
| 16 | `Group` | 79 | `IntegerSequencer` | 142 | `field` | 205 | `PointPickSensor` |
| 17 | `LOD` | 80 | `IntegerTrigger` | 143 | `head` | 206 | `PolylineEmitter` |
| 18 | `Switch` | 81 | `KeySensor` | 144 | `humanoidBodyType` | 207 | `PositionChaser` |
| 19 | `Script` | 82 | `LineProperties` | 145 | `meta` | 208 | `PositionChaser2D` |
| 20 | `IndexedTriangleFanSet` | 83 | `LineSet` | 146 | `CADAssembly` | 209 | `PositionDamper` |
| 21 | `IndexedTriangleSet` | 84 | `LoadSensor` | 147 | `CADFace` | 210 | `PositionDamper2D` |
| 22 | `IndexedTriangleStripSet` | 85 | `MetadataDouble` | 148 | `CADLayer` | 211 | `PrimitivePickSensor` |
| 23 | `MultiTexture` | 86 | `MetadataFloat` | 149 | `CADPart` | 212 | `RigidBody` |
| 24 | `MultiTextureCoordinate` | 87 | `MetadataInteger` | 150 | `ComposedCubeMapTexture` | 213 | `RigidBodyCollection` |
| 25 | `MultiTextureTransform` | 88 | `MetadataSet` | 151 | `ComposedShader` | 214 | `ScalarChaser` |
| 26 | `IndexedLineSet` | 89 | `MetadataString` | 152 | `ComposedTexture3D` | 215 | `ScreenFontStyle` |
| 27 | `PointSet` | 90 | `MovieTexture` | 153 | `FloatVertexAttribute` | 216 | `ScreenGroup` |
| 28 | `StaticGroup` | 91 | `NavigationInfo` | 154 | `FogCoordinate` | 217 | `SingleAxisHingeJoint` |
| 29 | `Sphere` | 92 | `NormalInterpolator` | 155 | `GeneratedCubeMapTexture` | 218 | `SliderJoint` |
| 30 | `Box` | 93 | `NurbsCurve` | 156 | `ImageCubeMapTexture` | 219 | `SplinePositionInterpolator` |
| 31 | `Cone` | 94 | `NurbsCurve2D` | 157 | `ImageTexture3D` | 220 | `SplinePositionInterpolator2D` |
| 32 | `Anchor` | 95 | `NurbsOrientationInterpolator` | 158 | `IndexedQuadSet` | 221 | `SplineScalarInterpolator` |
| 33 | `Arc2D` | 96 | `NurbsPatchSurface` | 159 | `LocalFog` | 222 | `SquadOrientationInterpolator` |
| 34 | `ArcClose2D` | 97 | `NurbsPositionInterpolator` | 160 | `Matrix3VertexAttribute` | 223 | `SurfaceEmitter` |
| 35 | `AudioClip` | 98 | `NurbsSet` | 161 | `Matrix4VertexAttribute` | 224 | `TexCoordDamper2D` |
| 36 | `Background` | 99 | `NurbsSurfaceInterpolator` | 162 | `PackagedShader` | 225 | `TextureProperties` |
| 37 | `Billboard` | 100 | `NurbsSweptSurface` | 163 | `PixelTexture3D` | 226 | `TransformSensor` |
| 38 | `BooleanFilter` | 101 | `NurbsSwungSurface` | 164 | `ProgramShader` | 227 | `TwoSidedMaterial` |
| 39 | `BooleanSequencer` | 102 | `NurbsTextureCoordinate` | 165 | `QuadSet` | 228 | `UniversalJoint` |
| 40 | `BooleanToggle` | 103 | `NurbsTrimmedSurface` | 166 | `ShaderPart` | 229 | `ViewpointGroup` |
| 41 | `BooleanTrigger` | 104 | `OrientationInterpolator` | 167 | `ShaderProgram` | 230 | `Viewport` |
| 42 | `Circle2D` | 105 | `PixelTexture` | 168 | `TextureCoordinate3D` | 231 | `VolumeEmitter` |
| 43 | `Collision` | 106 | `PlaneSensor` | 169 | `TextureCoordinate4D` | 232 | `VolumePickSensor` |
| 44 | `ColorInterpolator` | 107 | `PointLight` | 170 | `TextureTransform3D` | 233 | `WindPhysicsModel` |
| 45 | `Contour2D` | 108 | `Polyline2D` | 171 | `TextureTransformMatrix3D` | 234 | `BlendedVolumeStyle` |
| 46 | `ContourPolyline2D` | 109 | `Polypoint2D` | 172 | `BallJoint` | 235 | `BoundaryEnhancementVolumeStyle` |
| 47 | `CoordinateDouble` | 110 | `PositionInterpolator` | 173 | `BoundedPhysicsModel` | 236 | `CartoonVolumeStyle` |
| 48 | `CoordinateInterpolator` | 111 | `PositionInterpolator2D` | 174 | `ClipPlane` | 237 | `ComposedVolumeStyle` |
| 49 | `CoordinateInterpolator2D` | 112 | `ProtoBody` | 175 | `CollidableOffset` | 238 | `EdgeEnhancementVolumeStyle` |
| 50 | `Cylinder` | 113 | `ProtoDeclare` | 176 | `CollidableShape` | 239 | `IsoSurfaceVolumeData` |
| 51 | `CylinderSensor` | 114 | `ProtoInterface` | 177 | `CollisionCollection` | 240 | `MetadataBoolean` |
| 52 | `DirectionalLight` | 115 | `ProximitySensor` | 178 | `CollisionSensor` | 241 | `OpacityMapVolumeStyle` |
| 53 | `Disk2D` | 116 | `ReceiverPdu` | 179 | `CollisionSpace` | 242 | `ProjectionVolumeStyle` |
| 54 | `EXPORT` | 117 | `Rectangle2D` | 180 | `ColorDamper` | 243 | `SegmentedVolumeData` |
| 55 | `ElevationGrid` | 118 | `ScalarInterpolator` | 181 | `ConeEmitter` | 244 | `ShadedVolumeStyle` |
| 56 | `EspduTransform` | 119 | `Scene` | 182 | `Contact` | 245 | `SilhouetteEnhancementVolumeStyle` |
| 57 | `ExternProtoDeclare` | 120 | `SignalPdu` | 183 | `CoordinateDamper` | 246 | `ToneMappedVolumeStyle` |
| 58 | `Extrusion` | 121 | `Sound` | 184 | `DISEntityManager` | 247 | `VolumeData` |
| 59 | `FillProperties` | 122 | `SphereSensor` | 185 | `DISEntityTypeMapping` | 248 | `ColorChaser` |
| 60 | `Fog` | 123 | `SpotLight` | 186 | `DoubleAxisHingeJoint` | 249 | `CoordinateChaser` |
| 61 | `FontStyle` | 124 | `StringSensor` | 187 | `EaseInEaseOut` | 250 | `ScalarDamper` |
| 62 | `GeoCoordinate` | 125 | `Text` | 188 | `ExplosionEmitter` | 251 | `TexCoordChaser2D` |
| 63 | `GeoElevationGrid` | 126 | `TextureBackground` | 189 | `ForcePhysicsModel` | 252 | `unit` |

The 3.2 edition's table is entries 1-233 of this list with entry 224 reading
`TexCoordDamper`.

## Appendix B. Table A.3, attribute name table (19776-3 3.3), ID as published

Section 10.2: in Web3D's sample files IDs above 53 are written as ID + 1.

| ID | Name | ID | Name | ID | Name | ID | Name |
|---|---|---|---|---|---|---|---|
| 1 | `DEF` | 138 | `filled` | 275 | `startAngle` | 412 | `viewport` |
| 2 | `USE` | 139 | `finalText` | 276 | `startTime` | 413 | `activeLayer` |
| 3 | `containerField` | 140 | `fireMissionIndex` | 277 | `stiffness` | 414 | `align` |
| 4 | `fromNode` | 141 | `fired1` | 278 | `stopTime` | 415 | `offsetUnits` |
| 5 | `fromField` | 142 | `fired2` | 279 | `string` | 416 | `scaleMode` |
| 6 | `toNode` | 143 | `firedTime` | 280 | `stripCount` | 417 | `sizeUnits` |
| 7 | `toField` | 144 | `firingRange` | 281 | `style` | 418 | `layout` |
| 8 | `name` | 145 | `firingRate` | 282 | `summary` | 419 | `objectType` |
| 9 | `value` | 146 | `fogType` | 283 | `tdlType` | 420 | `pickedNormal` |
| 10 | `color` | 147 | `forceID` | 284 | `tessellation` | 421 | `pickedPoint` |
| 11 | `colorIndex` | 148 | `frequency` | 285 | `tessellationScale` | 422 | `pickedTextureCoordinate` |
| 12 | `coordIndex` | 149 | `frontUrl` | 286 | `time` | 423 | `intersectionType` |
| 13 | `texCoordIndex` | 150 | `fuse` | 287 | `timeOut` | 424 | `sortOrder` |
| 14 | `normalIndex` | 151 | `geoCoords` | 288 | `timestamp` | 425 | `axis1Angle` |
| 15 | `colorPerVertex` | 152 | `geoGridOrigin` | 289 | `title` | 426 | `axis1Torque` |
| 16 | `normalPerVertex` | 153 | `geoSystem` | 290 | `toggle` | 427 | `axis2Angle` |
| 17 | `rotation` | 154 | `groundAngle` | 291 | `top` | 428 | `axis2Torque` |
| 18 | `scale` | 155 | `groundColor` | 292 | `topToBottom` | 429 | `axis3Angle` |
| 19 | `center` | 156 | `hatchColor` | 293 | `topUrl` | 430 | `axis3Torque` |
| 20 | `scaleOrientation` | 157 | `hatchStyle` | 294 | `touchTime` | 431 | `enabledAxies` |
| 21 | `translation` | 158 | `hatched` | 295 | `transmitFrequencyBandwidth` | 432 | `motor1Axis` |
| 22 | `url` | 159 | `headlight` | 296 | `transmitState` | 433 | `motor2Axis` |
| 23 | `repeatS` | 160 | `horizontal` | 297 | `transmitterApplicationID` | 434 | `motor3Axis` |
| 24 | `repeatT` | 161 | `horizontalDatum` | 298 | `transmitterEntityID` | 435 | `stop1Bounce` |
| 25 | `point` | 162 | `http-equiv` | 299 | `transmitterRadioID` | 436 | `stop1ErrorCorrection` |
| 26 | `vector` | 163 | `image` | 300 | `transmitterSiteID` | 437 | `stop2Bounce` |
| 27 | `range` | 164 | `importedDEF` | 301 | `transparent` | 438 | `stop2ErrorCorrection` |
| 28 | `ambientIntensity` | 165 | `info` | 302 | `triggerTime` | 439 | `stop3Bounce` |
| 29 | `diffuseColor` | 166 | `innerRadius` | 303 | `triggerTrue` | 440 | `stop3ErrorCorrection` |
| 30 | `emissiveColor` | 167 | `inputFalse` | 304 | `triggerValue` | 441 | `motor1Angle` |
| 31 | `shininess` | 168 | `inputNegate` | 305 | `type` | 442 | `motor1AngleRate` |
| 32 | `specularColor` | 169 | `inputSource` | 306 | `uDimension` | 443 | `motor2Angle` |
| 33 | `transparency` | 170 | `inputTrue` | 307 | `uKnot` | 444 | `motor2AngleRate` |
| 34 | `whichChoice` | 171 | `integerKey` | 308 | `uOrder` | 445 | `motor3Angle` |
| 35 | `index` | 172 | `intensity` | 309 | `uTessellation` | 446 | `motor3AngleRate` |
| 36 | `mode` | 173 | `jump` | 310 | `ulimit` | 447 | `autoCalc` |
| 37 | `source` | 174 | `justify` | 311 | `vDimension` | 448 | `duration` |
| 38 | `function` | 175 | `keyPress` | 312 | `vKnot` | 449 | `retainUserOffsets` |
| 39 | `alpha` | 176 | `keyRelease` | 313 | `vOrder` | 450 | `isBound` |
| 40 | `vertexCount` | 177 | `knot` | 314 | `vTessellation` | 451 | `appearance` |
| 41 | `radius` | 178 | `lang` | 315 | `version` | 452 | `createParticles` |
| 42 | `size` | 179 | `language` | 316 | `verticalDatum` | 453 | `lifetimeVariation` |
| 43 | `height` | 180 | `leftToRight` | 317 | `vertices` | 454 | `maxParticles` |
| 44 | `solid` | 181 | `leftUrl` | 318 | `visibilityLimit` | 455 | `particleLifetime` |
| 45 | `ccw` | 182 | `length` | 319 | `visibilityRange` | 456 | `particleSize` |
| 46 | `key` | 183 | `lengthOfModulationParameters` | 320 | `warhead` | 457 | `colorKey` |
| 47 | `keyValue` | 184 | `level` | 321 | `weight` | 458 | `geometryType` |
| 48 | `enabled` | 185 | `limitOrientation` | 322 | `whichGeometry` | 459 | `texCoordKey` |
| 49 | `direction` | 186 | `lineSegments` | 323 | `writeInterval` | 460 | `pickable` |
| 50 | `position` | 187 | `linearAcceleration` | 324 | `xDimension` | 461 | `angularDampingFactor` |
| 51 | `orientation` | 188 | `linearVelocity` | 325 | `xSpacing` | 462 | `angularVelocity` |
| 52 | `bboxCenter` | 189 | `linetype` | 326 | `yScale` | 463 | `autoDamp` |
| 53 | `bboxSize` | 190 | `linewidthScaleFactor` | 327 | `zDimension` | 464 | `autoDisable` |
| 54 | `AS` | 191 | `llimit` | 328 | `zSpacing` | 465 | `disableAngularSpeed` |
| 55 | `InlineDEF` | 192 | `load` | 329 | `visible` | 466 | `disableLinearSpeed` |
| 56 | `accessType` | 193 | `loadTime` | 330 | `repeatR` | 467 | `disableTime` |
| 57 | `actionKeyPress` | 194 | `localDEF` | 331 | `texture` | 468 | `finiteRotationAxis` |
| 58 | `actionKeyRelease` | 195 | `location` | 332 | `back` | 469 | `fixed` |
| 59 | `address` | 196 | `loop` | 333 | `front` | 470 | `forces` |
| 60 | `altKey` | 197 | `marking` | 334 | `left` | 471 | `inertia` |
| 61 | `antennaLocation` | 198 | `mass` | 335 | `right` | 472 | `linearDampingFactor` |
| 62 | `antennaPatternLength` | 199 | `maxAngle` | 336 | `parts` | 473 | `torques` |
| 63 | `antennaPatternType` | 200 | `maxBack` | 337 | `isSelected` | 474 | `useFiniteRotation` |
| 64 | `applicationID` | 201 | `maxExtent` | 338 | `isValid` | 475 | `useGlobalForce` |
| 65 | `articulationParameterArray` | 202 | `maxFront` | 339 | `numComponents` | 476 | `constantForceMix` |
| 66 | `articulationParameterChangeIndicatorArray` | 203 | `maxPosition` | 340 | `depth` | 477 | `constantSurfaceThickness` |
| 67 | `articulationParameterCount` | 204 | `metadataFormat` | 341 | `update` | 478 | `errorCorrection` |
| 68 | `articulationParameterDesignatorArray` | 205 | `minAngle` | 342 | `fogCoord` | 479 | `iterations` |
| 69 | `articulationParameterIdPartAttachedArray` | 206 | `minBack` | 343 | `texCoord` | 480 | `maxCorrectionSpeed` |
| 70 | `articulationParameterTypeArray` | 207 | `minFront` | 344 | `activate` | 481 | `preferAccuracy` |
| 71 | `attenuation` | 208 | `minPosition` | 345 | `programs` | 482 | `pointSize` |
| 72 | `autoOffset` | 209 | `modulationTypeDetail` | 346 | `matrix` | 483 | `stopBounce` |
| 73 | `avatarSize` | 210 | `modulationTypeMajor` | 347 | `anchorPoint` | 484 | `stopErrorCorrection` |
| 74 | `axisOfRotation` | 211 | `modulationTypeSpreadSpectrum` | 348 | `body1` | 485 | `angleRate` |
| 75 | `backUrl` | 212 | `modulationTypeSystem` | 349 | `body2` | 486 | `maxSeparation` |
| 76 | `beamWidth` | 213 | `momentsOfInertia` | 350 | `forceOutput` | 487 | `minSeparation` |
| 77 | `beginCap` | 214 | `multicastRelayHost` | 351 | `body1AnchorPoint` | 488 | `separation` |
| 78 | `bindTime` | 215 | `multicastRelayPort` | 352 | `body2AnchorPoint` | 489 | `separationRate` |
| 79 | `bottom` | 216 | `munitionApplicationID` | 353 | `plane` | 490 | `closed` |
| 80 | `bottomRadius` | 217 | `munitionEndPoint` | 354 | `appliedParameters` | 491 | `keyVelocity` |
| 81 | `bottomUrl` | 218 | `munitionEntityID` | 355 | `bounce` | 492 | `normalizeVelocity` |
| 82 | `centerOfMass` | 219 | `munitionQuantity` | 356 | `frictionCoefficients` | 493 | `surface` |
| 83 | `centerOfRotation` | 220 | `munitionSiteID` | 357 | `minBounceSpeed` | 494 | `anisotropicDegree` |
| 84 | `child1Url` | 221 | `munitionStartPoint` | 358 | `slipFactors` | 495 | `borderColor` |
| 85 | `child2Url` | 222 | `mustEvaluate` | 359 | `softnessConstantForceMix` | 496 | `borderWidth` |
| 86 | `child3Url` | 223 | `navType` | 360 | `softnessErrorCorrection` | 497 | `boundaryModeS` |
| 87 | `child4Url` | 224 | `networkMode` | 361 | `surfaceSpeed` | 498 | `boundaryModeT` |
| 88 | `class` | 225 | `next` | 362 | `isActive` | 499 | `boundaryModeR` |
| 89 | `closureType` | 226 | `nodeField` | 363 | `useGeometry` | 500 | `magnificationFilter` |
| 90 | `collideTime` | 227 | `offset` | 364 | `set_destination` | 501 | `minificationFilter` |
| 91 | `content` | 228 | `on` | 365 | `set_value` | 502 | `textureCompression` |
| 92 | `controlKey` | 229 | `order` | 366 | `tau` | 503 | `texturePriority` |
| 93 | `controlPoint` | 230 | `originator` | 367 | `tolerance` | 504 | `generateMipMaps` |
| 94 | `convex` | 231 | `outerRadius` | 368 | `value_changed` | 505 | `targetObject` |
| 95 | `coordinateSystem` | 232 | `parameter` | 369 | `initialDestination` | 506 | `backAmbientIntensity` |
| 96 | `copyright` | 233 | `pauseTime` | 370 | `initialValue` | 507 | `backDiffuseColor` |
| 97 | `creaseAngle` | 234 | `pitch` | 371 | `angle` | 508 | `backEmissiveColor` |
| 98 | `crossSection` | 235 | `points` | 372 | `variation` | 509 | `backShininess` |
| 99 | `cryptoKeyID` | 236 | `port` | 373 | `surfaceArea` | 510 | `backSpecularColor` |
| 100 | `cryptoSystem` | 237 | `power` | 374 | `frictionDirection` | 511 | `separateBackColor` |
| 101 | `cutOffAngle` | 238 | `previous` | 375 | `slipCoefficients` | 512 | `displayed` |
| 102 | `cycleInterval` | 239 | `priority` | 376 | `category` | 513 | `clipBoundary` |
| 103 | `cycleTime` | 240 | `profile` | 377 | `country` | 514 | `internal` |
| 104 | `data` | 241 | `progress` | 378 | `domain` | 515 | `gustiness` |
| 105 | `dataFormat` | 242 | `protoField` | 379 | `extra` | 516 | `turbulence` |
| 106 | `dataLength` | 243 | `radioEntityTypeCategory` | 380 | `kind` | 517 | `unitCategory` |
| 107 | `dataUrl` | 244 | `radioEntityTypeCountry` | 381 | `specific` | 518 | `unitName` |
| 108 | `date` | 245 | `radioEntityTypeDomain` | 382 | `subcategory` | 519 | `unitConversionFactor` |
| 109 | `deadReckoning` | 246 | `radioEntityTypeKind` | 383 | `axis1` | 520 | `weightConstant1` |
| 110 | `deletionAllowed` | 247 | `radioEntityTypeNomenclature` | 384 | `axis2` | 521 | `weightConstant2` |
| 111 | `description` | 248 | `radioEntityTypeNomenclatureVersion` | 385 | `desiredAngularVelocity1` | 522 | `weightFunction1` |
| 112 | `detonateTime` | 249 | `radioID` | 386 | `desiredAngularVelocity2` | 523 | `weightFunction2` |
| 113 | `dir` | 250 | `readInterval` | 387 | `maxAngle1` | 524 | `boundaryOpacity` |
| 114 | `directOutput` | 251 | `receivedPower` | 388 | `maxTorque1` | 525 | `opacityFactor` |
| 115 | `diskAngle` | 252 | `receiverState` | 389 | `maxTorque2` | 526 | `retainedOpacity` |
| 116 | `displacements` | 253 | `reference` | 390 | `minAngle1` | 527 | `colorSteps` |
| 117 | `documentation` | 254 | `relativeAntennaLocation` | 391 | `stopBounce1` | 528 | `orthogonalColor` |
| 118 | `elapsedTime` | 255 | `resolution` | 392 | `stopConstantForceMix1` | 529 | `parallelColor` |
| 119 | `ellipsoid` | 256 | `resumeTime` | 393 | `stopErrorCorrection1` | 530 | `ordered` |
| 120 | `encodingScheme` | 257 | `rightUrl` | 394 | `suspensionErrorCorrection` | 531 | `edgeColor` |
| 121 | `endAngle` | 258 | `rootUrl` | 395 | `suspensionForce` | 532 | `gradientThreshold` |
| 122 | `endCap` | 259 | `rotateYUp` | 396 | `body1Axis` | 533 | `contourStepSize` |
| 123 | `enterTime` | 260 | `rtpHeaderExpected` | 397 | `body2Axis` | 534 | `dimensions` |
| 124 | `enteredText` | 261 | `sampleRate` | 398 | `hinge1Angle` | 535 | `surfaceTolerance` |
| 125 | `entityCategory` | 262 | `samples` | 399 | `hinge1AngleRate` | 536 | `surfaceValues` |
| 126 | `entityCountry` | 263 | `shiftKey` | 400 | `hinge2Angle` | 537 | `intensityThreshold` |
| 127 | `entityDomain` | 264 | `side` | 401 | `hinge2AngleRate` | 538 | `segmentEnabled` |
| 128 | `entityExtra` | 265 | `siteID` | 402 | `set_fraction` | 539 | `lighting` |
| 129 | `entityID` | 266 | `skinCoordIndex` | 403 | `easeInEaseOut` | 540 | `shadows` |
| 130 | `entityKind` | 267 | `skinCoordWeight` | 404 | `modifiedFraction_changed` | 541 | `phaseFunction` |
| 131 | `entitySpecific` | 268 | `skyAngle` | 405 | `force` | 542 | `silhouetteBoundaryOpacity` |
| 132 | `entitySubCategory` | 269 | `skyColor` | 406 | `geoCenter` | 543 | `silhouetteRetainedOpacity` |
| 133 | `exitTime` | 270 | `spacing` | 407 | `centerOfRotation_changed` | 544 | `silhouetteSharpness` |
| 134 | `extent` | 271 | `spatialize` | 408 | `geoCoord_changed` | 545 | `coolColor` |
| 135 | `family` | 272 | `speed` | 409 | `orientation_changed` | 546 | `warmColor` |
| 136 | `fanCount` | 273 | `speedFactor` | 410 | `position_changed` |  |  |
| 137 | `fieldOfView` | 274 | `spine` | 411 | `isPickable` |  |  |

The 3.2 edition's table is entries 1-516 of this list with entry 350 reading
`mustOutput`.

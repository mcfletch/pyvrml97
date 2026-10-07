"""The X3D compressed binary encoding (ISO/IEC 19776-3), read as Fast Infoset

A `.x3db` document is the XML encoding written as Fast Infoset (ITU-T
X.891) with the X3D vocabulary (`vrml.x3d.fivocabulary`). Its elements go
through the XML encoding's handlers (`ElementReader`); a node's value given
by an encoding algorithm arrives as numbers or booleans, and is given to the
builder as a value of its field's type rather than as text. A value in an
algorithm the vocabulary does not decode is reported and left unset.
"""

from typing import Any

from vrml.x3d import codecs
from vrml.x3d.builder import SceneBuilder
from vrml.x3d.fastinfoset import FastInfosetError, Undecoded, events
from vrml.x3d.fivocabulary import VOCABULARIES
from vrml.x3d.readers.xml import CONTAINERS, ElementReader
from vrml.x3d.scene import X3DScene


def text_of(value: Any) -> str:
    """A decoded value as XML attribute text"""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ' '.join('true' if item else 'false' for item in value)
    return ' '.join(codecs.number_text(number) for number in value)


class FastInfosetReader(ElementReader):
    """Turns a Fast Infoset document's events into builder calls"""

    def read(self, data: bytes) -> X3DScene:
        try:
            for event in events(data, VOCABULARIES):
                kind = event[0]
                if kind == 'start':
                    self._element(event[1], event[2])
                elif kind == 'end':
                    self._end(event[1])
                elif kind == 'text':
                    if isinstance(event[1], Undecoded):
                        self.builder.problem('error', 'Fast Infoset: %s' % event[1])
                        continue
                    self.in_cdata = event[2]
                    self._characters(text_of(event[1]))
                    self.in_cdata = False
        except FastInfosetError as error:
            self.builder.problem('error', 'Fast Infoset: %s' % error)
            return self.builder.end_document(complete=False)
        return self.builder.end_document()

    def _element(self, name: "str | None", attributes: "list[tuple[str | None, Any]]") -> None:
        if name is None:
            self.builder.problem('error', 'Fast Infoset: an element name the vocabulary '
                                 'does not know')
            name = ''
        known = {}
        for key, value in attributes:
            if key is None:
                self.builder.problem('warning', 'Fast Infoset: a %s attribute whose name no '
                                     'edition of the vocabulary gives' % name)
            elif isinstance(value, Undecoded):
                self.builder.problem('error', 'Fast Infoset: %s.%s is %s' % (name, key, value))
            else:
                known[key] = value
        if name in self.statements or name in CONTAINERS:
            known = {key: text_of(value) for key, value in known.items()}
        self._start(name, known)

    def _value(self, name: str, value: Any) -> None:
        if isinstance(value, str):
            self.builder.field_text(name, value)
            return
        type_name = self.builder.field_type(name)
        if type_name is None:
            self.builder.field_text(name, text_of(value))
            return
        try:
            typed = codecs.from_values(type_name, value)
        except ValueError as error:
            node = self.builder.current_node()
            self.builder.problem('error', '%s.%s: %s' % (self.builder.current_type(), name, error),
                                 node)
            return
        self.builder.field(name, typed)


def read(
    data: bytes,
    builder: SceneBuilder,
    charset: "str | None" = None,  # noqa: ARG001 every reader takes it; each string here names its own encoding
) -> X3DScene:
    """The scene an X3D compressed binary document builds; each of its
    strings names its own encoding, so `charset` is not read"""
    return FastInfosetReader(builder).read(data)

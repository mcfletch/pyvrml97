"""X3D's bind stacks: which viewpoint, background, fog and navigation are in force

Each scene keeps a stack of bindable nodes per kind (ISO/IEC 19775-1, 7.2.2):
viewpoints of every sort share one, as do backgrounds. The node on top is the
bound one.

- `set_bind TRUE` on a node not on top moves it there: it sends `isBound TRUE`
  and `bindTime`, and the node it covers sends `isBound FALSE`. On the top
  node it does nothing.
- `set_bind FALSE` on the top node takes it off: it sends `isBound FALSE` and
  `bindTime`, and the node it uncovers sends `isBound TRUE` and `bindTime`. On
  a node beneath the top it takes the node off and sends nothing.

The stacks are kept on the scene the node is rooted in; a node in no scene is
a stack of its own. `bindTime` is the node's :meth:`~vrml.x3d.timing.Timed.now`.
Layers do not yet have stacks of their own: every node of a scene is on the
scene's stacks.
"""

from __future__ import annotations

import weakref
from collections.abc import Iterable
from typing import Any, Optional

from vrml import field, protofunctions
from vrml.vrml97 import nodetypes
from vrml.x3d import timing

__all__ = ['KINDS', 'Bindable', 'bound', 'current', 'kind_of']

#: The kinds of bindable node, each with a stack of its own.
KINDS: "tuple[type, ...]" = (nodetypes.Viewpoint, nodetypes.Background, nodetypes.Fog,
                             nodetypes.NavigationInfo)


def kind_of(node: Any) -> type:
    """The kind of bindable `node` is, which names its stack"""
    for kind in KINDS:
        if isinstance(node, kind):
            return kind
    return type(node)


def _stack(owner: Any, kind: type) -> "list[weakref.ref[Any]]":
    """The bind stack of `kind` on `owner`, the top last"""
    stacks: "dict[type, list[weakref.ref[Any]]]" = owner.__dict__.setdefault('_bindStacks', {})
    found = stacks.setdefault(kind, [])
    found[:] = [reference for reference in found if reference() is not None]
    return found


def _owner(node: Any) -> Any:
    return protofunctions.root(node) or node


def bound(node: Any, kind: Optional[type] = None) -> Any:
    """The node on top of a bind stack, or None

    `node` is a bindable, naming its own scene and kind, or a scene with
    `kind` naming the stack.
    """
    if kind is None:
        owner, kind = _owner(node), kind_of(node)
    else:
        owner = node
    stack = _stack(owner, kind)
    return stack[-1]() if stack else None


def current(candidates: Iterable[Any]) -> Any:
    """The bound node of `candidates`, binding the first where none is

    `candidates` are bindables of one kind in one scene, in the order the
    scene has them: the first is the one bound when a scene is entered.
    """
    found = list(candidates)
    if not found:
        return None
    top = bound(found[0])
    if top is not None:
        return top
    found[0].set_bind = True
    return found[0]


class Bindable(timing.Timed):
    """A node on its scene's bind stack of its kind"""

    bindTime = field.newEvent('bindTime', 'SFTime', 1)
    isBound = field.newEvent('isBound', 'SFBool', 1)
    set_bind = field.newEvent('set_bind', 'SFBool', 0)

    def sendBound(self, value: bool) -> None:
        """Send `isBound` and `bindTime`: the node has been bound or unbound"""
        self.isBound = value
        self.bindTime = self.now()

    def on_set_bind(self, value: Any) -> None:
        stack = _stack(_owner(self), kind_of(self))
        top = stack[-1]() if stack else None
        if value:
            if top is self:
                return
            stack[:] = [reference for reference in stack if reference() is not self]
            stack.append(weakref.ref(self))
            if top is not None:
                top.sendBound(False)
            self.sendBound(True)
            return
        if top is self:
            stack.pop()
            self.sendBound(False)
            uncovered = stack[-1]() if stack else None
            if uncovered is not None:
                uncovered.sendBound(True)
            return
        stack[:] = [reference for reference in stack if reference() is not self]

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
- A bound node that has been collected is taken off as if it were sent
  `set_bind FALSE`, at the next look at its stack: the node it uncovers sends
  `isBound TRUE` and `bindTime` then.

The stacks are kept on the scene the node is rooted in; a node in no scene is
a stack of its own. `bindTime` is the node's :meth:`~vrml.x3d.timing.Timed.now`.
Every node of a scene, inside a `Layer` or not, is on the scene's stacks;
the separate stacks X3D gives each layer (7.2.2) are not kept.
"""

from __future__ import annotations

import weakref
from collections.abc import Iterable, Sequence
from typing import Any, Optional

from vrml import field, protofunctions
from vrml.vrml97 import nodetypes
from vrml.x3d import timing

__all__ = ['KINDS', 'Bindable', 'bound', 'current', 'current_path', 'kind_of']

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
    """The bind stack of `kind` on `owner`, the top last; a collected top uncovers
    the node beneath it"""
    stacks: "dict[type, list[weakref.ref[Any]]]" = owner.__dict__.setdefault('_bindStacks', {})
    found = stacks.setdefault(kind, [])
    top_collected = bool(found) and found[-1]() is None
    found[:] = [reference for reference in found if reference() is not None]
    uncovered = found[-1]() if top_collected and found else None
    if uncovered is not None:
        uncovered.sendBound(True)
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


def current_path(paths: Sequence[Any]) -> Any:
    """The path of `paths` to the bound node, binding one where it is not reached

    Each path is a sequence from the scene drawn to a bindable node, all of
    one kind: the paths a scene draws, which a `Switch` choosing another child
    changes. The topmost node a path reaches is bound (moved to the top where
    it is beneath), looking at the drawn scene's stack and then at those of the
    scenes its Inlines read. Where none is reached, the first path to a node
    of the drawn scene itself is bound: the nodes of a file an Inline reads
    are not candidates for the first bound (19775-1, 7.2.2). None where no
    path leads to one.
    """
    if not paths:
        return None
    kind = kind_of(paths[0][-1])
    main = _owner(paths[0][0])
    owners = [main]
    for path in paths:
        owner = _owner(path[-1])
        if not any(owner is known for known in owners):
            owners.append(owner)
    for owner in owners:
        for reference in reversed(_stack(owner, kind)):
            node = reference()
            for path in paths:
                if path[-1] is node:
                    node.set_bind = True
                    return path
    for path in paths:
        if not _inlined(path[-1], main):
            path[-1].set_bind = True
            return path
    return None


def _inlined(node: Any, main: Any) -> bool:
    """Whether `node` is of another scene than `main`: one an Inline read"""
    owner = protofunctions.root(node)
    return bool(owner) and owner is not main


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

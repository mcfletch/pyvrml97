"""Validating a scene against the X3D model

`validate(scene)` walks every node the scene reaches and reports, as
`LoadProblem` records: values outside the range the X3DUOM gives a field,
values outside a closed enumeration, and nodes of components or levels the
scene's profile and COMPONENT statements do not include. It is a pass of its
own, so building a scene does none of this work.
"""

from collections.abc import Iterator
from typing import Any

import numpy as np

from vrml import field, node, protofunctions
from vrml.x3d import profiles
from vrml.x3d.scene import LoadProblem


def _nodes(roots: Any) -> Iterator[Any]:
    """Every node reachable from `roots`, once each"""
    seen: "set[Any]" = set()
    stack = list(roots)
    while stack:
        current = stack.pop()
        if not current or current in seen or not isinstance(current, node.Node):
            continue
        seen.add(current)
        yield current
        for declared in protofunctions.getFields(current):
            if declared.name.startswith(' '):
                continue
            if isinstance(declared, node.MFNode):
                stack.extend(reversed(list(declared.__get__(current))))
            elif isinstance(declared, node.SFNode):
                stack.append(declared.__get__(current))


def _out_of_range(declared: Any, value: Any) -> "str | None":
    if declared.minimum is None and declared.maximum is None:
        return None
    try:
        numbers = np.asarray(value, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    if declared.typeName() in ('SFRotation', 'MFRotation'):
        return None
    if declared.minimum is not None:
        low = numbers <= declared.minimum if declared.minimumExclusive else (
            numbers < declared.minimum)
        if low.any():
            return '%s is below %s%s' % (numbers[low][0], declared.minimum,
                                         ' (exclusive)' if declared.minimumExclusive else '')
    if declared.maximum is not None:
        high = numbers >= declared.maximum if declared.maximumExclusive else (
            numbers > declared.maximum)
        if high.any():
            return '%s is above %s%s' % (numbers[high][0], declared.maximum,
                                         ' (exclusive)' if declared.maximumExclusive else '')
    return None


def _outside_choices(declared: Any, value: Any) -> "str | None":
    if not declared.choices or declared.choicesOpen:
        return None
    values = value if isinstance(value, list) else [value]
    for item in values:
        if item not in declared.choices:
            return '%r is not one of %s' % (item, ', '.join(declared.choices))
    return None


def _allowed(scene: Any, profile: "str | None") -> "tuple[dict[str, int], str | None]":
    """Each component's highest allowed level, and a problem with the profile"""
    name = profile if profile is not None else scene.profile
    chosen = profiles.PROFILES.get(name)
    if chosen is None:
        return dict(profiles.COMPONENTS), 'Unknown profile %r; components not checked' % name
    allowed = chosen.levels()
    for statement in scene.components:
        component = profiles.COMPONENT_ALIASES.get(statement.name, statement.name)
        allowed[component] = max(allowed.get(component, 0), statement.level)
    return allowed, None


def validate(scene: Any, profile: "str | None" = None) -> "list[LoadProblem]":
    """The problems a scene has against the X3D model

    profile -- the profile to check components against; the scene's own
        where not given. The scene's COMPONENT statements add to it.
    """
    problems = []
    allowed, unknown = _allowed(scene, profile)
    if unknown:
        problems.append(LoadProblem(severity='warning', message=unknown))
    for current in _nodes(scene.children):
        type_name = protofunctions.protoName(current)
        component = getattr(type(current), 'COMPONENT', None)
        if component is not None and unknown is None:
            name, level = component
            if allowed.get(name, 0) < level:
                problems.append(LoadProblem(
                    severity='error', node=current,
                    message='%s needs %s level %d, which profile %s and the COMPONENT '
                            'statements do not give'
                            % (type_name, name, level, profile or scene.profile),
                ))
        for declared in protofunctions.getFields(current):
            if declared.name.startswith(' ') or isinstance(declared, (node.SFNode, node.MFNode)):
                continue
            if not isinstance(declared, field.Field) or not declared.fhas(current):
                continue
            value = declared.__get__(current)
            found = _out_of_range(declared, value) or _outside_choices(declared, value)
            if found:
                problems.append(LoadProblem(
                    severity='error', node=current,
                    message='%s.%s: %s' % (type_name, declared.name, found),
                ))
    return problems

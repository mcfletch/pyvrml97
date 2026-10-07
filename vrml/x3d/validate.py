"""Validating a scene against the X3D model

`validate(scene)` walks every node the scene and its prototypes' bodies
reach and reports, as `LoadProblem` records: values outside the range the
X3DUOM gives a field, numbers that are not finite, values outside a closed
enumeration, nodes and fields the scene's version does not have, nodes of
components or levels the scene's profile and COMPONENT statements do not
include, and COMPONENT statements past a component's highest level. It is a
pass of its own, so building a scene does none of this work.
"""

from collections.abc import Iterator
from typing import Any

import numpy as np

from vrml import field, node, protofunctions
from vrml.x3d import dialects, extension, profiles
from vrml.x3d import nodes as x3d
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


def _roots(scene: Any) -> "list[Any]":
    """The scene's root nodes, and those of each prototype body it declares"""
    found = list(scene.children)
    for proto in getattr(scene, 'protoTypes', {}).values():
        body = protofunctions.getSceneGraph(proto)
        if body:
            found.extend(body.children)
    return found


def _not_finite(declared: Any, value: Any) -> "str | None":
    if declared.typeName() not in _FLOAT_TYPES:
        return None
    try:
        numbers = np.asarray(value, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    bad = ~np.isfinite(numbers)
    return '%s is not a finite number' % numbers[bad][0] if bad.any() else None


_FLOAT_TYPES = frozenset((
    'SFFloat', 'MFFloat', 'SFDouble', 'MFDouble', 'SFTime', 'MFTime',
    'SFVec2f', 'MFVec2f', 'SFVec3f', 'MFVec3f', 'SFVec4f', 'MFVec4f',
    'SFVec2d', 'MFVec2d', 'SFVec3d', 'MFVec3d', 'SFVec4d', 'MFVec4d',
    'SFColor', 'MFColor', 'SFColorRGBA', 'MFColorRGBA', 'SFRotation', 'MFRotation',
    'SFMatrix3f', 'MFMatrix3f', 'SFMatrix4f', 'MFMatrix4f',
    'SFMatrix3d', 'MFMatrix3d', 'SFMatrix4d', 'MFMatrix4d',
))


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
    for statement in scene.components:
        name = profiles.COMPONENT_ALIASES.get(statement.name, statement.name)
        highest = profiles.COMPONENTS.get(name)
        if highest is not None and statement.level > highest:
            problems.append(LoadProblem(
                severity='error',
                message='COMPONENT %s:%d is past its highest level, %d'
                        % (statement.name, statement.level, highest)))
    version = str(scene.version or x3d.X3D_VERSION)
    chosen = dialects.DIALECTS.get(version)
    if chosen is None:
        problems.append(LoadProblem(
            severity='warning',
            message='Unknown version %r; checked against %s' % (version, x3d.X3D_VERSION)))
        chosen = dialects.DIALECTS[x3d.X3D_VERSION]
    tables = chosen.tables()
    for current in _nodes(_roots(scene)):
        type_name = protofunctions.protoName(current)
        declared_type = x3d.CONCRETE_NODES.get(type_name)
        in_vocabulary = declared_type is not None and isinstance(current, declared_type)
        if in_vocabulary and not tables.has_node(type_name):
            problems.append(LoadProblem(
                severity='error', node=current,
                message='%s has no node %s' % (chosen.name, type_name)))
            in_vocabulary = False
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
            if (in_vocabulary and declared.name in extension.vocabulary_fields(type_name)
                    and not tables.has_field(type_name, declared.name)):
                problems.append(LoadProblem(
                    severity='error', node=current,
                    message='%s has no field %s.%s' % (chosen.name, type_name, declared.name)))
                continue
            value = declared.__get__(current)
            found = (_not_finite(declared, value) or _out_of_range(declared, value)
                     or _outside_choices(declared, value))
            if found:
                problems.append(LoadProblem(
                    severity='error', node=current,
                    message='%s.%s: %s' % (type_name, declared.name, found),
                ))
    return problems

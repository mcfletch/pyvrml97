"""An X3D scene, and the records a document's statements make

The `X3DScene` is a `SceneGraph` that also holds what an X3D document says
about itself: its profile and version, the components and units it declares,
its `meta` statements, its `IMPORT`/`EXPORT` statements, and the problems
reading it met. Each of those is a node, so a scene's records copy, write
out and can be inspected like the rest of the graph.
"""

from vrml import field, node
from vrml import fieldtypes  # noqa: F401 registers the field types used below
from vrml.vrml97.scenegraph import SceneGraph


class ComponentInfo(node.Node):
    """A `component` statement: a component and the level a scene uses"""

    PROTO = 'ComponentInfo'
    name = field.newField('name', 'SFString', 1, '')
    level = field.newField('level', 'SFInt32', 1, 1)


class UnitInfo(node.Node):
    """A `unit` statement: one unit category's name and conversion factor

    `category` is `angle`, `force`, `length` or `mass`; a value read from
    the document in that category is multiplied by `conversionFactor`.
    """

    PROTO = 'UnitInfo'
    category = field.newField('category', 'SFString', 1, '')
    name = field.newField('name', 'SFString', 1, '')
    conversionFactor = field.newField('conversionFactor', 'SFDouble', 1, 1.0)


class MetaInfo(node.Node):
    """A `meta` statement: a name and its content"""

    PROTO = 'MetaInfo'
    name = field.newField('name', 'SFString', 1, '')
    content = field.newField('content', 'SFString', 1, '')
    dir = field.newField('dir', 'SFString', 1, '')
    httpEquiv = field.newField('httpEquiv', 'SFString', 1, '')
    lang = field.newField('lang', 'SFString', 1, '')
    scheme = field.newField('scheme', 'SFString', 1, '')


class ImportInfo(node.Node):
    """An `IMPORT` statement: a node an Inline's scene exports, named here

    `localDEF` names the node in this scene once the Inline has loaded and
    its scene exports `importedDEF`.
    """

    PROTO = 'ImportInfo'
    inlineDEF = field.newField('inlineDEF', 'SFString', 1, '')
    importedDEF = field.newField('importedDEF', 'SFString', 1, '')
    localDEF = field.newField('localDEF', 'SFString', 1, '')


class ExportInfo(node.Node):
    """An `EXPORT` statement: a node this scene offers to an `IMPORT`"""

    PROTO = 'ExportInfo'
    localDEF = field.newField('localDEF', 'SFString', 1, '')
    AS = field.newField('AS', 'SFString', 1, '')


class RouteInfo(node.Node):
    """A `ROUTE` statement whose ends are not all available yet

    A route naming an imported node waits here until the Inline that
    exports it has loaded; `vrml.x3d.builder.bind_imports` then makes the
    route and removes this record.
    """

    PROTO = 'RouteInfo'
    fromNode = field.newField('fromNode', 'SFString', 1, '')
    fromField = field.newField('fromField', 'SFString', 1, '')
    toNode = field.newField('toNode', 'SFString', 1, '')
    toField = field.newField('toField', 'SFString', 1, '')


class LoadProblem(node.Node):
    """Something reading a document met: an error, a warning or a note

    `line` and `column` are 1-based positions in the document, or 0 where
    the encoding does not give one; `path` is the way to the problem through
    a document that has no lines to give (JSON's members and indexes). `node`
    is the node concerned, if any.
    """

    PROTO = 'LoadProblem'
    severity = field.newField(
        'severity', 'SFString', 1, 'error',
        choices=('error', 'warning', 'info'), choicesOpen=False,
    )
    line = field.newField('line', 'SFInt32', 1, 0)
    column = field.newField('column', 'SFInt32', 1, 0)
    message = field.newField('message', 'SFString', 1, '')
    path = field.newField('path', 'SFString', 1, '')
    node = node.SFNodeReference('node', 1, node.NULL)

    def __str__(self) -> str:
        where = ' line %d' % self.line if self.line else ''
        if self.line and self.column:
            where += ' column %d' % self.column
        if not self.line and self.path:
            where = ' at %s' % self.path
        return '%s%s: %s' % (self.severity, where, self.message)


class X3DScene(SceneGraph):
    """An X3D document's scene, with what the document says about itself"""

    PROTO = 'X3DScene'
    profile = field.newField('profile', 'SFString', 1, 'Full')
    version = field.newField('version', 'SFString', 1, '4.1')
    components = field.newField('components', 'MFNode', 1, list,
                                requiredTypes=ComponentInfo)
    units = field.newField('units', 'MFNode', 1, list, requiredTypes=UnitInfo)
    meta = field.newField('meta', 'MFNode', 1, list, requiredTypes=MetaInfo)
    imports = field.newField('imports', 'MFNode', 1, list, requiredTypes=ImportInfo)
    exports = field.newField('exports', 'MFNode', 1, list, requiredTypes=ExportInfo)
    pendingRoutes = field.newField('pendingRoutes', 'MFNode', 1, list,
                                   requiredTypes=RouteInfo)
    problems = field.newField('problems', 'MFNode', 1, list, requiredTypes=LoadProblem)

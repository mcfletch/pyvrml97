"""Assigning to a field has to do what the field says it does.

Fields are descriptors, and several of them do real work in ``fset``: an MFNode
keeps its observable list in place so the scenegraph's change notifications keep
flowing, an SFNode propagates the scene root into what is attached to it, a weak
field stores a reference rather than the object.

The C accelerator supplies ``__set__`` for every field, and a ``cdef`` method it
calls cannot be overridden from Python -- so an accelerated build ran none of
that, and ``node.children = [...]`` quietly detached the list from the
scenegraph. What is asserted here is that assignment and ``fset`` do the same
thing, accelerated or not.
"""
import gc

import pytest
from pydispatch.dispatcher import connect

from vrml import field, node, olist


class Watcher:
    """A live receiver: pydispatch drops a weakly-referenced lambda at once."""

    def __init__(self):
        self.added = []
        self.removed = []
        connect(self.on_add, signal=olist.OList.NEW_CHILD_EVT)
        connect(self.on_remove, signal=olist.OList.DEL_CHILD_EVT)

    def on_add(self, sender, value, **named):
        self.added.append((sender, value))

    def on_remove(self, sender, value, **named):
        self.removed.append((sender, value))


class Child(node.Node):
    PROTO = 'Child'
    name = field.newField('name', 'SFString', 1, '')


class Holder(node.Node):
    PROTO = 'Holder'
    children = node.MFNode('children')
    one = node.SFNode('one')


@pytest.fixture
def watcher():
    gc.collect()
    return Watcher()


class TestAssigningAChildList:
    def test_a_new_child_is_announced(self, watcher) -> None:
        holder = Holder(children=[Child(name='first')])
        arriving = Child(name='second')
        holder.children = list(holder.children) + [arriving]
        assert any(value is arriving for _, value in watcher.added)

    def test_a_departing_child_is_announced(self, watcher) -> None:
        going = Child(name='going')
        holder = Holder(children=[Child(name='staying'), going])
        holder.children = [holder.children[0]]
        assert any(value is going for _, value in watcher.removed)

    def test_the_announcement_comes_from_the_node(self, watcher) -> None:
        """A listener asks the sender what its children are, so the sender has
        to be the node and not the bare list."""
        holder = Holder(children=[])
        holder.children = [Child(name='new')]
        assert watcher.added
        assert all(sender is holder for sender, _ in watcher.added)

    def test_the_list_object_is_kept(self, watcher) -> None:
        """Whatever is holding a reference to the list keeps a live one."""
        holder = Holder(children=[Child()])
        before = holder.children
        holder.children = [Child(), Child()]
        assert holder.children is before
        assert len(before) == 2

    def test_assignment_and_fset_agree(self, watcher) -> None:
        by_assignment = Holder(children=[])
        by_call = Holder(children=[])
        child_a, child_b = Child(name='a'), Child(name='b')
        by_assignment.children = [child_a]
        type(Holder.children).fset(Holder.children, by_call, [child_b])
        assert len(by_assignment.children) == len(by_call.children)
        assert len([1 for _, value in watcher.added
                    if value in (child_a, child_b)]) == 2


class TestAssigningASingleNode:
    def test_the_scene_root_reaches_what_is_attached(self) -> None:
        """SFNode.fset passes the root down; a bypassed setter would not."""
        root = Holder()
        node.Node.rootSceneGraph.fset(root, root, notify=0)
        attached = Child()
        root.one = attached
        assert node.Node.rootSceneGraph.fget(attached) is root

    def test_the_value_is_what_was_assigned(self) -> None:
        holder = Holder()
        attached = Child(name='x')
        holder.one = attached
        assert holder.one is attached


class TestOrdinaryFieldsStillWork:
    def test_a_scalar_field_round_trips(self) -> None:
        child = Child()
        child.name = 'renamed'
        assert child.name == 'renamed'

    def test_a_scalar_field_announces_the_change(self) -> None:
        seen = []

        class Listener:
            def note(self, sender, value=None, **named):
                seen.append(value)

        listener = Listener()
        connect(listener.note, signal=('set', Child.name))
        child = Child()
        child.name = 'renamed'
        assert 'renamed' in seen

    def test_deleting_a_field_restores_its_default(self) -> None:
        child = Child(name='given')
        del child.name
        assert child.name == ''



class TestDeletingAFieldFromAPrototype:
    """A prototype holds its field values on the class itself.

    `setSceneGraph`, `setExternalURL` and their `del` counterparts all work on
    a prototype rather than an instance, and a class's `__dict__` is a
    read-only mapping proxy -- so setting and deleting there go through
    `setattr` and `delattr`, not through the dictionary.

    Both the pure-Python field and the compiled one have to do this: which is
    in use is decided by whether `PyVRML97-accelerate` is installed, and a
    user does not expect the answer to change with it.
    """

    def built(self):
        from vrml import node as node_module
        return node_module.prototype('Wheel')

    def test_a_scene_graph_is_set_and_read_back(self) -> None:
        from vrml import protofunctions
        from vrml.vrml97.scenegraph import SceneGraph
        built, graph = self.built(), SceneGraph()
        protofunctions.setSceneGraph(built, graph)
        assert protofunctions.getSceneGraph(built) is graph

    def test_a_scene_graph_is_deleted(self) -> None:
        from vrml import protofunctions
        from vrml.vrml97.scenegraph import SceneGraph
        built, graph = self.built(), SceneGraph()
        protofunctions.setSceneGraph(built, graph)
        protofunctions.delSceneGraph(built)
        assert protofunctions.getSceneGraph(built) is not graph

    def test_an_external_url_is_set_and_read_back(self) -> None:
        from vrml import protofunctions
        built = self.built()
        protofunctions.setExternalURL(built, ['http://example.com/w.wrl'])
        assert list(protofunctions.getExternalURL(built)) == [
            'http://example.com/w.wrl']

    def test_an_external_url_is_deleted(self) -> None:
        from vrml import protofunctions
        built = self.built()
        protofunctions.setExternalURL(built, ['http://example.com/w.wrl'])
        protofunctions.delExternalURL(built)
        assert list(protofunctions.getExternalURL(built)) == []

    def test_deleting_one_that_was_never_set_raises(self) -> None:
        from vrml import protofunctions
        with pytest.raises(AttributeError):
            protofunctions.delSceneGraph(self.built())

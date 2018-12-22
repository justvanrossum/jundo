from collections.abc import Mapping, Sequence, Set
import pytest
from jundo.undoManager import *


class _AttributeObject:

    def someMethod(self, x):
        return x + 2

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
               ", ".join("%s=%r" % (k, v) for k, v in self.__dict__.items()))


def test_module_docsting_example():
    model = [1, 2, 3, {"a": 123}]
    um = UndoManager()
    proxy = um.setModel(model)
    # Modifications must be done within a change set context:
    with um.changeSet(title="replace list item"):
        proxy[1] = 2000
    assert model[1] == 2000
    um.undo()
    assert model[1] == 2
    um.redo()
    assert model[1] == 2000
    with um.changeSet(title="replace nested dict item"):
        proxy[3]["a"] = 456
    assert model[3]["a"] == 456
    um.undo()
    assert model[3]["a"] == 123


def test_undoInfo():
    model = [1, "a", "Q"]
    um = UndoManager()
    proxy = um.setModel(model)
    assert um.undoInfo() == None
    assert um.redoInfo() == None
    with um.changeSet(title="undo action", more="any info"):
        proxy[1] = 2000
    assert um.undoInfo() == {'more': 'any info', 'title': 'undo action'}
    assert um.redoInfo() is None
    um.undo()
    assert um.undoInfo() == None
    assert um.redoInfo() == {'more': 'any info', 'title': 'undo action'}
    um.redo()
    assert um.undoInfo() == {'more': 'any info', 'title': 'undo action'}
    assert um.redoInfo() is None
    um.undo()
    assert um.undoInfo() is None
    with um.changeSet(title="another"):
        proxy[1] = 2000
    assert um.undoInfo() == {'title': 'another'}
    assert um.redoInfo() is None


def test_collections_abc():
    proxy = UndoProxySequence(None, None, None)
    assert isinstance(proxy, Sequence)
    proxy = UndoProxyMapping(None, None, None)
    assert isinstance(proxy, Mapping)
    proxy = UndoProxySet(None, None, None)
    assert isinstance(proxy, Set)


def test_UndoProxy_dispatch():
    assert UndoProxy(1, None) == 1
    assert UndoProxy(1.2, None) == 1.2
    assert UndoProxy("1.2", None) == "1.2"
    assert type(UndoProxy([], None)) == UndoProxySequence
    assert type(UndoProxy({}, None)) == UndoProxyMapping
    assert type(UndoProxy(set(), None)) == UndoProxySet
    assert type(UndoProxy(_AttributeObject(), None)) == UndoProxyAttributeObject


def test_modify_without_changeSet():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with pytest.raises(AssertionError):
        proxy.append("foo")
    assert "foo" not in model

def test_nested_changeSet():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="outer"):
        with pytest.raises(UndoManagerError):
            with um.changeSet(title="inner"):
                pass

def test_undo_within_changeSet():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="test 2"):
        proxy.append(4)
    assert model == [0, 1, 2, 3, 4]
    with um.changeSet(title="test"):
        with pytest.raises(UndoManagerError):
            um.undo()

def test_empty_changeSet():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="test"):
        # nothing
        pass
    assert len(um.undoStack) == 0


class _error_dict(dict):
    def __setitem__(self, key, value):
        raise ValueError("test")


def test_modify_error():
    model = _error_dict()
    um = UndoManager()
    proxy = um.setModel(model)
    with pytest.raises(ValueError):
        with um.changeSet(title="error test"):
            proxy["a"] = 12
    assert um._currentChanges is None
    assert "a" not in model
    # assert that we *didn't* record an undo change
    assert len(um.undoStack) == 0
    assert len(um.undoStack) == 0


def test_rollback_after_error():
    model = [1, 2, _error_dict()]
    um = UndoManager()
    proxy = um.setModel(model)
    with pytest.raises(ValueError):
        with um.changeSet(title="error test"):
            assert len(model) == 3
            proxy.append(12)
            assert len(model) == 4
            proxy[1] = 200
            assert model[1] == 200
            proxy[2]["a"] = 300
    # assert that the first two changes have been rolled back
    assert model == [1, 2, _error_dict()]


def test_replacing_model():
    um = UndoManager()
    proxy = um.setModel({})
    with pytest.raises(AssertionError):
        proxy = um.setModel({})


def test_list_append():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="list test"):
        proxy.append("a")
        proxy.append("b")
    assert len(um.undoStack) == 1
    assert len(um.redoStack) == 0
    assert model == [0, 1, 2, 3, "a", "b"]
    for a, b in zip(model, proxy):
        assert a == b
    assert um.undoInfo() == {"title": "list test"}
    assert um.redoInfo() is None
    assert len(um.undoStack) == 1
    assert len(um.redoStack) == 0
    um.undo()
    assert um.undoInfo() is None
    assert um.redoInfo() == {"title": "list test"}
    assert len(um.undoStack) == 0
    assert len(um.redoStack) == 1
    assert model == [0, 1, 2, 3]
    um.redo()
    assert model == [0, 1, 2, 3, "a", "b"]
    with pytest.raises(UndoManagerError):
        um.redo()

def test_list_insert():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="list test"):
        proxy.insert(2, "a")
        proxy.insert(1, "b")
        proxy.insert(5, "c")
    assert model == [0, "b", 1, "a", 2, "c", 3]
    um.undo()
    assert model == [0, 1, 2, 3]
    um.redo()
    assert model == [0, "b", 1, "a", 2, "c", 3]

def test_list_insert_double():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="list test"):
        proxy.insert(2, "a")
        proxy.insert(2, "b")
    assert model == [0, 1, "b", "a", 2, 3]
    um.undo()
    assert model == [0, 1, 2, 3]
    um.redo()
    assert model == [0, 1, "b", "a", 2, 3]

def test_list_remove():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="list test"):
        del proxy[2]
    assert model == [0, 1, 3]
    um.undo()
    assert model == [0, 1, 2, 3]
    um.redo()
    assert model == [0, 1, 3]

def test_list_remove_double():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="list test"):
        del proxy[1]
        del proxy[1]
    assert model == [0, 3]
    um.undo()
    assert model == [0, 1, 2, 3]
    um.redo()
    assert model == [0, 3]

def test_list_replace():
    model = [0, 1, 2, 3]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="list test"):
        proxy[2] = "a"
    assert model == [0, 1, "a", 3]
    um.undo()
    assert model == [0, 1, 2, 3]
    um.redo()
    assert model == [0, 1, "a", 3]
    um.undo()
    assert model == [0, 1, 2, 3]

def test_list_replace2():
    model = ["a", "b", "c"]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="list test"):
        proxy[1] = "B"
    assert proxy[1] == model[1] == "B"
    um.undo()
    assert model == ["a", "b", "c"]
    um.redo()
    assert model == ["a", "B", "c"]

def test_list_index():
    model = ["a", "b", "c"]
    proxy = UndoProxy(model, None)
    assert len(proxy) == 3
    assert proxy[-1] == "c"
    with pytest.raises(IndexError):
        proxy[100]


def test_dictionary():
    model = {}
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="dict test"):
        proxy["a"] = 12
    assert model == {"a": 12}
    assert model["a"] == proxy["a"]
    with um.changeSet(title="dict test 2"):
        proxy["a"] = 1200
    assert model == {"a": 1200}
    with um.changeSet(title="dict test 3"):
        proxy["b"] = 24
    assert model == {"a": 1200, "b": 24}
    um.undo()
    assert model == {"a": 1200}
    um.undo()
    assert model == {"a": 12}
    um.undo()
    assert model == {}
    um.redo()
    um.redo()
    um.redo()
    assert model == {"a": 1200, "b": 24}
    um.undo()
    with um.changeSet(title="dict test 4"):
        proxy["c"] = 48
        #assert model == {"a": 1200, "c": 24}
    assert model == {"a": 1200, "c": 48}
    with pytest.raises(UndoManagerError):
        um.redo()
    with um.changeSet(title="dict test 5"):
        del proxy["a"]
    assert model == {"c": 48}
    um.undo()
    um.undo()
    assert model == {"a": 1200}


def test_dictionary_iter():
    d = {"a": 1, "b": 2}
    proxy = UndoProxy(d, None)
    assert list(proxy) == ["a", "b"]


def test_dictionary_repr():
    model = {"a": 1, "b": 2}
    proxy = UndoProxy(model, None)
    assert repr(proxy) == "UndoProxyMapping({'a': 1, 'b': 2}, path=())"
    assert len(proxy) == 2


def test_dictionary_multiple():
    model = {}
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="dict test"):
        proxy["a"] = 12
    with um.changeSet(title="dict test multiple"):
        proxy["a"] = 13
        proxy["a"] = 14
    um.undo()
    assert model["a"] == 12
    um.redo()
    assert model["a"] == 14


def test_object():
    model = _AttributeObject()
    um = UndoManager()
    proxy = um.setModel(model)
    assert model.__dict__ == {}
    with um.changeSet(title="object test"):
        proxy.foo = 12
    assert model.__dict__ == {"foo": 12}
    assert proxy.foo == model.foo
    um.undo()
    assert model.__dict__ == {}
    um.redo()
    assert model.__dict__ == {"foo": 12}
    with um.changeSet(title="object test 2"):
        del proxy.foo
    assert model.__dict__ == {}
    um.undo()
    assert model.__dict__ == {"foo": 12}
    with pytest.raises(AssertionError):
        proxy.bar = 123
    with um.changeSet(title="replace test"):
        proxy.foo = 123


def test_tuple_atomic():
    model = [1, 2, (3, 4, 5), 6, 7]
    um = UndoManager()
    proxy = um.setModel(model)
    assert proxy[2] == (3, 4, 5)
    assert type(proxy[2]) == tuple
    with um.changeSet(title="replace item"):
        proxy[1] = (200, 300)
    assert model[1] == (200, 300)
    assert type(proxy[1]) == tuple
    assert type(model[1]) == tuple
    assert model == [1, (200, 300), (3, 4, 5), 6, 7]
    um.undo()
    assert model == [1, 2, (3, 4, 5), 6, 7]


def test_set():
    model = {1, 3, 5, 7}
    um = UndoManager()
    proxy = um.setModel(model)
    assert 1 in proxy
    assert 2 not in proxy
    assert set(proxy) == model
    with um.changeSet(title="add item"):
        proxy.add(9)
    with um.changeSet(title="remove item"):
        proxy.remove(3)
    assert 3 not in proxy
    assert 3 not in model
    assert 9 in proxy
    assert 9 in model
    assert set(proxy) == {1, 5, 7, 9}
    um.undo()
    assert set(proxy) == {1, 3, 5, 7, 9}
    um.undo()
    assert set(proxy) == {1, 3, 5, 7}


def test_set_insert():
    model = [1, 2, 3, 4]
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="insert set"):
        proxy[1] = {1, 2, 3}
    assert model == [1, {1, 2, 3}, 3, 4]
    assert proxy[1] == {1, 2, 3}
    assert isinstance(proxy[1], Set)
    assert not isinstance(proxy[1], set)  # it's an UndoProxy after all
    um.undo()
    assert model == [1, 2, 3, 4]
    um.redo()
    assert model == [1, {1, 2, 3}, 3, 4]


def test_set_add_discard():
    model = {1, 3, 5, 7}
    um = UndoManager()
    proxy = um.setModel(model)
    with um.changeSet(title="add existing value"):
        model.add(3)  # already there
    assert len(um.undoStack) == 0
    with um.changeSet(title="remove non-existing value"):
        model.discard(2)
    assert len(um.undoStack) == 0


def test_callable():
    model = _AttributeObject()
    um = UndoManager()
    proxy = um.setModel(model)
    assert proxy.someMethod(3) == 5


def test_generic_hasItem():
    d = {"a": 1}
    o = _AttributeObject()
    o.foo = 1
    assert hasItem(d, "a")
    assert hasItem(o, "foo")
    assert not hasItem(d, "b")
    assert not hasItem(o, "bar")

def test_generic_getItem():
    d = {"a": 1}
    l = [1]
    o = _AttributeObject()
    o.foo = 1
    assert getItem(d, "a") == 1
    assert getItem(l, 0) == 1
    assert getItem(o, "foo") == 1

def test_generic_addItem():
    d = {"a": 1}
    l = [1]
    o = _AttributeObject()
    o.foo = 1
    addItem(d, "b", 2)
    addItem(l, 1, 2)
    addItem(o, "bar", 2)
    assert getItem(d, "b") == 2
    assert getItem(l, 1) == 2
    assert getItem(o, "bar") == 2
    with pytest.raises(AssertionError):
        addItem(d, "b", 2)
    with pytest.raises(AssertionError):
        addItem(o, "bar", 2)
        
def test_generic_replaceItem():
    d = {"a": 1}
    l = [1]
    o = _AttributeObject()
    o.foo = 1
    replaceItem(d, "a", 2)
    replaceItem(l, 0, 2)
    replaceItem(o, "foo", 2)
    assert getItem(d, "a") == 2
    assert getItem(l, 0) == 2
    assert getItem(o, "foo") == 2
    with pytest.raises(AssertionError):
        replaceItem(d, "b", 2)
    with pytest.raises(AssertionError):
        replaceItem(o, "bar", 2)

def test_generic_removeItem():
    d = {"a": 1}
    l = [1]
    o = _AttributeObject()
    o.foo = 1
    removeItem(d, "a")
    removeItem(l, 0)
    removeItem(o, "foo")
    assert not hasItem(d, "a")
    assert len(l) == 0
    assert not hasItem(o, "foo")

def test_getNestedItem():
    o = _AttributeObject()
    o.foo = "foo"
    d = {"a": [1, 2, 3, {"b": 4, "c": ["a", "b", "c"]}, o]}
    assert getNestedItem(d, ("a", 1)) == 2
    assert getNestedItem(d, ("a", 2)) == 3
    assert getNestedItem(d, ("a", 3, "b")) == 4
    assert getNestedItem(d, ("a", 3, "c", 1)) == "b"
    assert getNestedItem(d, ("a", 4)) == o
    assert getNestedItem(d, ("a", 4, "foo")) == "foo"
    with pytest.raises(AttributeError):
        getNestedItem(d, ("a", 2, "b"))
    with pytest.raises(IndexError):
        getNestedItem(d, ("a", 5))

def test_addNestedItem():
    o = _AttributeObject()
    d = {"a": [1, 2, 3, {"b": 4, "c": ["a", "b", "c", o]}]}
    addNestedItem(d, ("b",), "B")
    assert getNestedItem(d, ("b",)) == "B"
    addNestedItem(d, ("a", 0), "C")
    assert d == {"a": ["C", 1, 2, 3, {"b": 4, "c": ["a", "b", "c", o]}], "b": "B"}
    addNestedItem(d, ("a", 4, "c", 4), "Q")
    assert d == {"a": ["C", 1, 2, 3, {"b": 4, "c": ["a", "b", "c", o, "Q"]}], "b": "B"}
    addNestedItem(d, ("a", 4, "c", 3, "foo"), "QQQ")
    with pytest.raises(AssertionError):
        addNestedItem(d, ("a", 4, "c", 3, "foo"), "QQQ")
    assert getNestedItem(d, ("a", 4, "c", 3, "foo")) == "QQQ"
    assert o.foo == "QQQ"

def test_replaceNestedItem():
    o = _AttributeObject()
    o.foo = 1
    d = {"a": [1, 2, 3, {"b": 4, "c": ["a", "b", "c"], "d": o}]}
    replaceNestedItem(d, ("a", 1), 222)
    assert d == {"a": [1, 222, 3, {"b": 4, "c": ["a", "b", "c"], "d": o}]}
    replaceNestedItem(d, ("a", 3, "d", "foo"), 222)
    assert o.foo == 222
    with pytest.raises(AssertionError):
        replaceNestedItem(d, ("b"), 333)
    with pytest.raises(AssertionError):
        replaceNestedItem(d, ("a", 3, "d", "bar"), 222)

def test_removeNestedItem():
    o = _AttributeObject()
    o.foo = 1
    d = {"a": [1, 2, 3, {"b": 4, "c": ["a", "b", "c"], "d": o}]}
    removeNestedItem(d, ("a", 1))
    assert d == {"a": [1, 3, {"b": 4, "c": ["a", "b", "c"], "d": o}]}
    removeNestedItem(d, ("a", 2, "c", 1))
    assert d == {"a": [1, 3, {"b": 4, "c": ["a", "c"], "d": o}]}
    removeNestedItem(d, ("a", 2, "c"))
    assert d == {"a": [1, 3, {"b": 4, "d": o}]}
    assert hasattr(o, "foo")
    removeNestedItem(d, ("a", 2, "d", "foo"))
    assert not hasattr(o, "foo")


class MyCustomModel:

    """This model class demonstrates a simple case that doesn't fit the
    JSON-like mold, yet can be used with the undo manager anyway via a
    custom proxy.
    """

    def __init__(self, position):
        self.position = position

    def move(self, delta):
        self.position += delta


class MyCustomUndoProxy(UndoProxyBase):

    @staticmethod
    def modelReplaceItem(model, key, value):
        # This method gets registered as a specializer for replaceItem in the
        # registerUndoProxy() call.
        assert key == "move"
        model.move(value)

    def move(self, delta):
        path = self._path + ("move",)  # we use the last part of the path as a method name
        change = Change("replace", path, delta)  # we use the "replace" operator to capture the method call
        invChange = Change("replace", path, -delta)
        self._undoManager.ensureCanAddChange()  # this raises AssertionError if a change can't be added
        self._modelObject.move(delta)           # forward the call to the model object as-is
        self._undoManager.addChange(change, invChange)  # add the change to the undo stack


# We need to register the proxy class so it'll be picked up automatically
registerUndoProxy(MyCustomModel, MyCustomUndoProxy)


def test_custom_proxy():
    model = MyCustomModel(10)
    um = UndoManager()
    proxy = um.setModel(model)
    assert type(proxy) == MyCustomUndoProxy
    with um.changeSet(title="move"):
        proxy.move(10)
    assert model.position == 20
    um.undo()
    assert model.position == 10

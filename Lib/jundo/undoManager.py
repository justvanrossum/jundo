from collections.abc import Callable, Mapping, MutableMapping, Sequence, \
                            MutableSequence, Set, MutableSet
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import singledispatch
from operator import getitem, setitem, delitem, contains
import typing


class UndoManagerError(Exception):
    pass


class UndoManager:

    """An UndoManager manages a stack of undo items and a stack of redo items.
    It records the changes to a model object tree via proxy objects, and can
    roll back these changes or replay them.

        >>> um = UndoManager()

    The root model object is passed to the UndoManager with the setModel()
    method, which returns a proxy for the model.

        >>> model = [1, 2, 4, 8, {"a": 10, "b": 20}]
        >>> proxy = um.setModel(model)

    Before modifications to the model object via the proxy can take place,
    the UndoManager needs to be set up with an internal change set object.

        >>> with um.changeSet(title="a label for this action"):
        ...     proxy[1] = 200
        ...     proxy[4]["b"] = 2000
        ...
        >>> model
        [1, 200, 4, 8, {'a': 10, 'b': 2000}]

    The topmost change set is rolled back by calling the undo() method:

        >>> um.undo()
        >>> model
        [1, 2, 4, 8, {'a': 10, 'b': 20}]

    Redo works similarly:

        >>> um.redo()
        >>> model
        [1, 200, 4, 8, {'a': 10, 'b': 2000}]

    The keyword arguments passed to changeSet() for the topmost undo item
    can be retrieved like this:

        >>> um.undoInfo()
        {'title': 'a label for this action'}

    Likewise for redo. undoInfo() and redoInfo() return None if their
    respective stack is empty:

        >>> um.redoInfo() is None
        True

    Doing undo or redo when its respective stack is empty will raise
    UndoManagerError:

        >>> um.redo()  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        UndoManagerError: empty undo/redo stack

    By default, UndoManager supports JSON-like objects (objects composed of
    strings, numbers, list-like and dictionary-like objects) as well as any
    object type that uses attributes to query and manipulate its data.

    For object types that do not fit this mold, a custom proxy class can be
    registered via the registerUndoProxy() function.

    UndoManager() has an optional argument called `changeMonitor`, which should
    be a callable taking one positional argument. It will be called for every
    change set that is recorded or performed via `um.undo()` or `um.redo()`,
    with the change set as the argument. This mechanism can be used to trigger
    view updates in a GUI application.
    """

    def __init__(self, changeMonitor=None):
        self.undoStack = []
        self.redoStack = []
        self._currentChanges = None  # (info, currentChangeSet, currentInverseChangeSet)
        self._modelObject = None
        self._changeMonitor = changeMonitor

    def setModel(self, model):
        """Set the model object for the undo manager and return a proxy for
        that object. The proxy object should be used instead of the real model
        object to perform modifications.

        This method can only be called once, as the undo history will be tied to
        a single model object.
        """
        assert self._modelObject is None, "model object can only be set once"
        proxy = UndoProxy(model, self)
        self._modelObject = model
        return proxy

    @contextmanager
    def changeSet(self, **info):
        """Returns a context manager that handles a newChangeSet/pushCurrentChangeSet
        pair conveniently.

        Keyword arguments passed to the undoManager.changeSet() call form the
        info dict associated with this change set. One use for this is to
        specify an action name for an undo/redo menu item.
        """
        self.newChangeSet(**info)
        try:
            yield
        except Exception:
            self.rollbackCurrentChangeSet()
            raise
        else:
            self.pushCurrentChangeSet()

    def newChangeSet(self, **info):
        """Prepare a new change set to record changes into. Once all changes
        are done, undoManager.pushCurrentChangeSet() must be called to push the
        recorded changes onto the undo stack.

        In most cases it is better to use the context manager provided by the
        undoManager.changeSet() method, as that takes care of proper pairing
        with a undoManager.pushCurrentChangeSet() call.

        Keyword arguments passed to the undoManager.newChangeSet() call form
        the info dict associated with this change set. One use for this is to
        specify an action name for an undo/redo menu item.
        """
        if self._currentChanges is not None:
            raise UndoManagerError("there already is an active change set")
        self._currentChanges = (info, ChangeSet(), InverseChangeSet())

    def pushCurrentChangeSet(self):
        """Push the changes that were recorded by the current change set to the
        undo stack. A call to undoManager.pushCurrentChangeSet() is always
        paired with a prior call to undoManager.newChangeSet().

        In most cases it is better to use the context manager provided by the
        undoManager.changeSet() method, as that takes care of proper pairing
        with a undoManager.newChangeSet() call.
        """
        assert self._currentChanges is not None
        info, currentChangeSet, currentInverseChangeSet = self._currentChanges
        self._currentChanges = None
        if not currentChangeSet.isEmpty():
            self.undoStack.append((info, currentChangeSet, currentInverseChangeSet))
            self.redoStack = []
            if self._changeMonitor is not None:
                self._changeMonitor(currentChangeSet)
        else:
            assert currentInverseChangeSet.isEmpty()

    def rollbackCurrentChangeSet(self):
        """Roll back the current changes to the model, and discard the current
        change set. Use this when an error occurs and the current change set
        should not be pushed to the undo stack.

        The context manager provided by undoManager.changeSet() automatically
        takes care of this.
        """
        info, currentChangeSet, currentInverseChangeSet = self._currentChanges
        currentInverseChangeSet.applyChanges(self._modelObject)
        self._currentChanges = None

    def ensureCanAddChange(self):
        """Before modifying the model object, check whether the undo manager is
        ready to receive changes.
        """
        assert self._currentChanges is not None, "can't add change, there is no active change set"

    def addChange(self, change, invChange):
        """Add a change and its inverse to the current change set."""
        assert self._currentChanges is not None, "can't add change, there is no active change set"
        info, currentChangeSet, currentInverseChangeSet = self._currentChanges
        currentChangeSet.addChange(change)
        currentInverseChangeSet.addChange(invChange)
        # TODO: a continuous changes monitoring hook should be triggered here
        # Or would that be too fine grained? Imagine multiple points being dragged,
        # that would result in multiple addChange calls for a single drag step.

    def undoInfo(self):
        """Return the info dict for the top change set on the undo stack, or
        None if the stack is empty.

        The info dict is specified when setting up the change set, as keyword
        arguments to changeSet(**info) or newChangeSet(**info).
        """
        if self.undoStack:
            return self.undoStack[-1][0]
        else:
            return None  # empty undo stack

    def redoInfo(self):
        """Return the info dict for the top change set on the redo stack, or
        None if the stack is empty.

        The info dict is specified when setting up the change set, as keyword
        arguments to changeSet(**info) or newChangeSet(**info).
        """
        if self.redoStack:
            return self.redoStack[-1][0]
        else:
            return None  # empty redo stack

    def undo(self):
        """Perform the item on the top of the undo stack, and remove it from
        the stack.

        This will raise UndoManagerError if the undo stack is empty.
        """
        self._performUndo(self.undoStack, self.redoStack)

    def redo(self):
        """Perform the item on the top of the redo stack, and remove it from
        the stack.

        This will raise UndoManagerError if the redo stack is empty.
        """
        self._performUndo(self.redoStack, self.undoStack)

    def _performUndo(self, popStack, pushStack):
        if not popStack:
            raise UndoManagerError("empty undo/redo stack")
        if self._currentChanges is not None:
            raise UndoManagerError("can't undo/redo in a change set context")
        info, changeSet, invChangeSet = popStack.pop()
        invChangeSet.applyChanges(self._modelObject)
        pushStack.append((info, invChangeSet, changeSet))
        if self._changeMonitor is not None:
            self._changeMonitor(invChangeSet)
        # TODO: a continuous changes monitoring hook should also be triggered here


# Change Classes

@dataclass(frozen=True)
class Change:

    """A Change delta is an object with three fields:

    - op: the operation to be performed. One of "add", "replace" or "remove"
    - path: a path identifying a child object in the model object tree
    - value: the value to add or replace, or None when removing the child

    The path object is a tuple containing path elements. A path element is either a
    string (a key or an attribute name) or an integer (a sequence index). An empty
    path represents the root object.

    Examples:
    - ("a",) represents the key "a" if the root object is a dictionary, or the
      attribute "a" if it is a non-container object.
    - (3,) represents the item with index 3 for a sequence root element
    - (3, "a") represents 123 in this object: [2, 4, 8, {"a": 123}]
    """

    op: str
    path: tuple  # path elements are str or int
    value: typing.Any

    def applyChange(self, model):
        if self.op == "add":
            addNestedItem(model, self.path, self.value)
        elif self.op == "replace":
            replaceNestedItem(model, self.path, self.value)
        elif self.op == "remove":
            removeNestedItem(model, self.path)
        else:
            assert 0, self.op


@dataclass
class ChangeSet:

    # TODO: multiple "replace" operators on the same path can be folded into one
    # TODO: perhaps the self.changes list should be frozen into a tuple as soon
    # as the ChangeSet gets pushed to the stack.

    changes: list = field(default_factory=list)

    def __iter__(self):
        return iter(self.changes)

    def addChange(self, change):
        self.changes.append(change)

    def applyChanges(self, model):
        for change in self:
            change.applyChange(model)

    def isEmpty(self):
        return not self.changes


class InverseChangeSet(ChangeSet):

    def __iter__(self):
        return reversed(self.changes)


# Proxy classes

class UndoProxyBase:

    def __init__(self, model, undoManager, path=()):
        self._modelObject = model
        self._undoManager = undoManager
        self._path = path

    def __repr__(self):
        return f"{self.__class__.__name__}({self._modelObject}, path={self._path})"


class UndoProxyContainerBase(UndoProxyBase):

    def _genericGetItem(self, key):
        path = self._path + (key,)
        item = self.modelGetItem(self._modelObject, key)
        return UndoProxy(item, self._undoManager, path)

    def _genericSetItem(self, key, value):
        path = self._path + (key,)
        if self.modelHasItem(self._modelObject, key):
            oldValue = self.modelGetItem(self._modelObject, key)
            change = Change("replace", path, value)
            invChange = Change("replace", path, oldValue)
            setter = self.modelReplaceItem
        else:
            change = Change("add", path, value)
            invChange = Change("remove", path, None)
            setter = self.modelAddItem
        self._undoManager.ensureCanAddChange()
        setter(self._modelObject, key, value)
        self._undoManager.addChange(change, invChange)

    def _genericDelItem(self, key):
        path = self._path + (key,)
        oldValue = self.modelGetItem(self._modelObject, key)
        change = Change("remove", path, None)
        invChange = Change("add", path, oldValue)
        self._undoManager.ensureCanAddChange()
        self.modelRemoveItem(self._modelObject, key)
        self._undoManager.addChange(change, invChange)


class UndoProxySequence(UndoProxyContainerBase, MutableSequence):

    @staticmethod
    def modelHasItem(model, index):
        # The generic code assumes dict-like "contains" behavior, so for sequences
        # we pretend the indices to be "keys" into the sequence. This means that
        # the standard __contains__ behavior of sequences is not useful, and we'll
        # simply return True. We only assert that the index is not out of range,
        # which shouldn't happen here.
        assert 0 <= index < len(model)
        return True

    modelGetItem = getitem

    @staticmethod
    def modelAddItem(model, index, value):
        model.insert(index, value)

    modelReplaceItem = setitem
    modelRemoveItem = delitem

    def __len__(self):
        return len(self._modelObject)

    def _normalizeIndex(self, index):
        numItems = len(self._modelObject)
        if index < 0:
            index += numItems
        if not (0 <= index < numItems):
            raise IndexError("sequence index out of range")
        return index

    def __getitem__(self, index):
        index = self._normalizeIndex(index)
        return self._genericGetItem(index)

    def __setitem__(self, index, item):
        index = self._normalizeIndex(index)
        self._genericSetItem(index, item)

    def __delitem__(self, index):
        index = self._normalizeIndex(index)
        self._genericDelItem(index)

    def insert(self, index, item):
        if index >= len(self):
            index = len(self)
        else:
            index = self._normalizeIndex(index)
        path = self._path + (index,)
        change = Change("add", path, item)
        invChange = Change("remove", path, None)
        self._undoManager.ensureCanAddChange()
        self._modelObject.insert(index, item)
        self._undoManager.addChange(change, invChange)


class UndoProxyMapping(UndoProxyContainerBase, MutableMapping):

    modelHasItem = contains
    modelGetItem = getitem

    @staticmethod
    def modelAddItem(model, key, value):
        assert key not in model
        model[key] = value

    @staticmethod
    def modelReplaceItem(model, key, value):
        assert key in model
        model[key] = value

    modelRemoveItem = delitem

    def __len__(self):
        return len(self._modelObject)

    def __iter__(self):
        return iter(self._modelObject)

    def __getitem__(self, key):
        return self._genericGetItem(key)

    def __setitem__(self, key, value):
        self._genericSetItem(key, value)

    def __delitem__(self, key):
        self._genericDelItem(key)


class UndoProxyAttributeObject(UndoProxyContainerBase):

    modelHasItem = hasattr
    modelGetItem = getattr

    @staticmethod
    def modelAddItem(model, attr, value):
        assert not hasattr(model, attr)
        setattr(model, attr, value)

    @staticmethod
    def modelReplaceItem(model, attr, value):
        assert hasattr(model, attr)
        setattr(model, attr, value)

    modelRemoveItem = delattr

    def __getattr__(self, attr):
        return self._genericGetItem(attr)

    def __setattr__(self, attr, value):
        if attr in ("_modelObject", "_undoManager", "_path"):
            super().__setattr__(attr, value)
            return
        self._genericSetItem(attr, value)

    def __delattr__(self, attr):
        self._genericDelItem(attr)


class UndoProxySet(UndoProxyBase, MutableSet):

    modelHasItem = contains

    @staticmethod
    def modelGetItem(model, value):
        assert 0, "getItem is not implemented for sets"

    @staticmethod
    def modelAddItem(model, value, dummy):
        assert isinstance(value, (int, float, str, tuple))
        assert value not in model
        model.add(value)

    @staticmethod
    def modelReplaceItem(model, key, value):
        assert 0, "replaceItem is not implemented for sets"

    @staticmethod
    def modelRemoveItem(model, value):
        model.remove(value)

    def __len__(self):
        return len(self._modelObject)

    def __iter__(self):
        return iter(self._modelObject)

    def __contains__(self, value):
        return value in self._modelObject

    def add(self, value):
        if value in self._modelObject:
            return  # nothing to do or to undo
        path = self._path + (value,)
        change = Change("add", path, None)
        invChange = Change("remove", path, None)
        self._undoManager.ensureCanAddChange()
        self._modelObject.add(value)
        self._undoManager.addChange(change, invChange)

    def discard(self, value):
        """Remove an element.  Do not raise an exception if absent."""
        if value not in self._modelObject:
            return
        path = self._path + (value,)
        change = Change("remove", path, None)
        invChange = Change("add", path, None)
        self._undoManager.ensureCanAddChange()
        self._modelObject.discard(value)
        self._undoManager.addChange(change, invChange)


class UndoProxyCallable(UndoProxyBase, Callable):

    # This is only for convenience, so one can call methods on the
    # model object via the proxy. It doesn't (can't) do any magic to
    # record changes.

    def __call__(self, *args, **kwargs):
        return self._modelObject(*args, **kwargs)


#
# Functions for querying and modifying nested objects, using path tuples to
# specify a location in the tree.
#
# The modifier functions follow the Change operators and their semantics:
#
#   "add"       Add an item to the container, the item must not yet exist.
#               This corresponds for example to a new key/value pair for a
#               mapping, or an insert/append for a sequence.
#   "replace"   Replace an existing item.
#   "remove"    Remove an existing item.
#

def getNestedItem(obj, path):
    for pathElement in path:
        obj = getItem(obj, pathElement)
    return obj


def addNestedItem(obj, path, value):
    obj = getNestedItem(obj, path[:-1])
    addItem(obj, path[-1], value)


def replaceNestedItem(obj, path, value):
    obj = getNestedItem(obj, path[:-1])
    replaceItem(obj, path[-1], value)


def removeNestedItem(obj, path):
    obj = getNestedItem(obj, path[:-1])
    removeItem(obj, path[-1])


#
# Generic sub-object query and modification functions. The modifier functions
# follow the Change operators and their semantics -- see above.
#
# Specializers are generally provided by the proxy classes, and are registered
# implicitly by the registerUndoProxy() function.
#

@singledispatch
def hasItem(obj, attr):
    return hasattr(obj, attr)


@singledispatch
def getItem(obj, attr):
    return getattr(obj, attr)


@singledispatch
def addItem(obj, attr, value):
    assert not hasattr(obj, attr)
    setattr(obj, attr, value)


@singledispatch
def replaceItem(obj, attr, value):
    assert hasattr(obj, attr)
    setattr(obj, attr, value)


@singledispatch
def removeItem(obj, attr):
    delattr(obj, attr)


@singledispatch
def UndoProxy(model, undoManager, path=()):
    return UndoProxyAttributeObject(model, undoManager, path=path)


def registerUndoProxy(type, handler):
    """Register a proxy handler (usually a class) for a model type. If the
    handler implements specializers for the generic subitem functions:
    register them as well.
    """
    UndoProxy.register(type, handler)
    if hasattr(handler, "modelHasItem"):
        hasItem.register(type, handler.modelHasItem)
    if hasattr(handler, "modelGetItem"):
        getItem.register(type, handler.modelGetItem)
    if hasattr(handler, "modelAddItem"):
        addItem.register(type, handler.modelAddItem)
    if hasattr(handler, "modelReplaceItem"):
        replaceItem.register(type, handler.modelReplaceItem)
    if hasattr(handler, "modelRemoveItem"):
        removeItem.register(type, handler.modelRemoveItem)


def _UndoProxy_atomic(model, undoManager, path=()):
    # This handler is registered for types that will not get a proxy
    # wrapper at all.
    return model


registerUndoProxy(int, _UndoProxy_atomic)
registerUndoProxy(float, _UndoProxy_atomic)
registerUndoProxy(str, _UndoProxy_atomic)
registerUndoProxy(tuple, _UndoProxy_atomic)  # Registering tuple as atomic means any mutable sub items won't be tracked
registerUndoProxy(Mapping, UndoProxyMapping)
registerUndoProxy(Sequence, UndoProxySequence)
registerUndoProxy(Set, UndoProxySet)
registerUndoProxy(Callable, UndoProxyCallable)

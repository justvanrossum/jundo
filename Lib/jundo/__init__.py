"""# jundo

A general purpose library to help implement undo for existing objects.

The main idea is that if one limits oneself to objects that can be viewed as
JSON-like data structures (ie. are composed of strings, numbers, lists and
dictionaries) it is possible to record changes in a completely generic way,
and use these recordings to reconstruct objects or to roll back changes, for
example to implement undo.

A key requirement was that the model objects must be completely decoupled from
the recording mechanism, and will not need any awareness of it.

The way this is implemented here is through proxy objects: instead of modifying
the original model objects directly, one uses proxy objects that mimic the
model object, allowing the proxy to pass on change information (deltas) to an
undo manager.

The undo manager collects change deltas (and their inverses), and can apply
them to the original model object when undo or redo is requested.

The model object is passed to the undo manager with the
`undoManager.setModel(model)`, which returns a proxy for the model. Client code
must use the proxy object instead of the model to modify the model. Here is an
example:

    >>> model = [1, 2, 3, {"a": 123}]
    >>> um = UndoManager()
    >>> proxy = um.setModel(model)
    >>> # Modifications must be done within a change set context:
    >>> with um.changeSet(title="replace list item"):
    ...     proxy[1] = 2000
    ...
    >>> model[1]
    2000
    >>> um.undo()
    >>> model[1]
    2
    >>> um.redo()
    >>> model[1]
    2000
    >>> with um.changeSet(title="replace nested dict item"):
    ...     proxy[3]["a"] = 456
    ...
    >>> model[3]["a"]
    456
    >>> um.undo()
    >>> model[3]["a"]
    123

In this example, only Python list and dict objects are used as containers, but
any type of Mapping or Sequence (in the collections.abc-sense) can be used, or
any object type that uses attribute access to modify its model data. See the
Examples folder for more elaborate examples.

Sets are also supported.

To support model objects that are not JSON-like, custom proxy classes can be
registered via the `registerUndoProxy()` function.

### Acknowledgments

The approach implemented here is inspired by Raph Levien's ideas, as he wrote
them down [here](https://github.com/trufont/trufont/pull/614#issuecomment-446309637).
It also draws inspiration from [jsonpatch](http://jsonpatch.com/).
"""

from .undoManager import UndoManager

__all__ = ["UndoManager"]

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "<unknown>"

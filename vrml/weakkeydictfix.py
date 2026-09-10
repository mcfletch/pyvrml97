"""Module providing patched weakkeydictionary operation"""
import weakref
from typing import Any, Dict, Optional

ref = weakref.ref

class WeakKeyDictionary( weakref.WeakKeyDictionary ):
    """Sub-class to work around error in WeakKeyDictionary implementation

    Python 2.2.2 and 2.2.3c1 both have an annoying
    problem in their __delitem__ for the
    WeakKeyDictionary class.  This class provides
    a work-around for it.
    """
    def __init__(self, dict: Optional[Dict[Any, Any]] = None) -> None:
        """Initialize the WeakKeyDictionary

        dict -- previously-existing weak key records or
            None to create a new dictionary
        """
        self.data: Dict[Any, Any] = {}
        def remove(k: Any, selfref: Any = ref(self)) -> None:  # noqa: B008 - the default is the weak ref
            self = selfref()
            if self is not None and self.data:
                try:
                    self.data.get( k )
                    del self.data[k]
                except (KeyError,RuntimeError):
                    pass
            # now v goes out of scope and is deleted...
        self._remove = remove
        if dict is not None:
            self.update(dict)
    def __delitem__(self, key: Any) -> None:
        """Overridden delitem to avoid scanning"""
        try:
            del self.data[weakref.ref(key)]
        except KeyError:
            raise KeyError( """Item %r does not appear as a key"""%( key,)) from None

"""Module providing patched weakkeydictionary operation"""
import weakref
ref = weakref.ref

class WeakKeyDictionary( weakref.WeakKeyDictionary ):
    """Sub-class to work around error in WeakKeyDictionary implementation

    Python 2.2.2 and 2.2.3c1 both have an annoying
    problem in their __delitem__ for the
    WeakKeyDictionary class.  This class provides
    a work-around for it.
    """
    def __init__(self, dict=None):
        """Initialize the WeakKeyDictionary

        dict -- previously-existing weak key records or
            None to create a new dictionary
        """
        self.data = {}
        def remove(k, selfref=ref(self)):
            self = selfref()
            if self is not None and self.data:
                try:
                    v = self.data.get( k )
                    del self.data[k]
                except (KeyError,RuntimeError):
                    pass
            # now v goes out of scope and is deleted...
        self._remove = remove
        if dict is not None: self.update(dict)
    def __delitem__(self, key):
        """Overridden delitem to avoid scanning"""
        try:
            del self.data[weakref.ref(key)]
        except KeyError:
            raise KeyError( """Item %r does not appear as a key"""%( key,))
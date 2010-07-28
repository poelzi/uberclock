class Enumeration(object):
    """
    Enumeration class for constants
    """
    __slots__ = '_name', '_lookup'

    def __init__(self, name, enumlist):
        self._name = name
        lookup = {}
        i = 0
        for x in enumlist:
            if type(x) is tuple:
                x, i = x
            if type(x) is not str:
                raise TypeError, "enum name is not a string: " + x
            if type(i) is not int:
                raise TypeError, "enum value is not an integer: " + i
            if x in lookup:
                raise ValueError, "enum name is not unique: " + x
            if i in lookup:
                raise ValueError, "enum value is not unique for " + x
            lookup[x] = i
            lookup[i] = x
            i = i + 1
        self._lookup = lookup

    def __getattr__(self, attr):
        try:
            return self._lookup[attr]
        except KeyError:
            raise AttributeError, attr

    def whatis(self, value):
        """
        Return the name that represents this value
        """
        return self._lookup[value]

    def __repr__(self):
        return '<Enumeration %s>' %self._name

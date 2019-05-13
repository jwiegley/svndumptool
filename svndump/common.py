# ===============================================================================
#
# Copyright (C) 2003 Martin Furter <mf@rola.ch>
#
# This file is part of SvnDumpTool
#
# SvnDumpTool is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# SvnDumpTool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SvnDumpTool; see the file COPYING.  If not, write to
# the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#
# ===============================================================================

from __future__ import print_function

import calendar
import time

try:
    import hashlib
except ImportError:
    import md5 as hashlib

__doc__ = """Common functions and classes."""


# perhaps some of these date functions can be replaced by
# functions provided by the svn python bindings +++++
# <sussman> it's our own string format, in libsvn_subr/time.c
# <sussman> svn_time_[to|from]_cstring()
def parse_svn_date_str(dateStr):
    """
    Parse a svn date string and return a tuple containing time_t and micros.
    """

    if len(dateStr) != 27:
        return 0, 0
    if dateStr[19] != "." or dateStr[26] != "Z":
        return 0, 0
    dat = time.strptime(dateStr[:19], "%Y-%m-%dT%H:%M:%S")
    return int(calendar.timegm(dat)), int(dateStr[20:26])


def create_svn_date_str(dateTuple):
    """
    Creates a svn date string from a tuple containing time_t and micros.
    """

    dat = time.gmtime(dateTuple[0])
    dstr = time.strftime("%Y-%m-%dT%H:%M:%S", dat)
    mstr = ".%06dZ" % (dateTuple[1])
    return dstr + mstr


def is_valid_md5_string(md5):
    """
    Checks a md5 string.

    @type md5: object
    @param md5: Index or key.
    @rtype: bool
    @return: True if the string looks like an md5 sum.
    """

    if len(md5) != 32:
        return False
    if md5.lower().strip("0123456789abcdef") != "":
        return False
    return True


def is_valid_sha1_string(sha1):
    """
    Checks a sha1 string.

    @type sha1: object
    @param sha1: SHA1 string.
    @rtype: bool
    @return: True if the string looks like an sha1 sum.
    """

    if len(sha1) != 40:
        return False
    if sha1.lower().strip("0123456789abcdef") != "":
        return False
    return True


class SvnDumpException(Exception):
    """A simple exception class."""

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class ListDictIter:
    """
    Iterator class used by ListDict.
    """

    def __init__(self, listdict, type):
        self.__listdict = listdict
        self.__type = type
        self.__index = 0

    def __iter__(self):
        return self

    def next(self):
        index = self.__index
        if index >= len(self.__listdict):
            raise StopIteration()
        self.__index = index + 1
        if self.__type == 1:
            return self.__listdict.key(index)
        elif self.__type == 2:
            return self.__listdict[index]
        else:
            return self.__listdict.item(index)


class ListDict(dict):
    """
    A mix of list and dict.

    If the key is an int this class acts like a list else like a dict.
    """

    def __init__(self):
        """
        Initialize.
        """
        dict.__init__(self)
        self.__index = []

    def __delitem__(self, key):
        """
        Removes the key/value pair for the specified key or index.

        @type key: object
        @param key: Index or key.
        """
        if type(key) is int:
            index = key
            key = self.__index[index]
        else:
            index = self.__index.index(key)
        del self.__index[index]
        dict.__delitem__(self, key)

    def __getitem__(self, key):
        """
        Returns the value for the specified key or index if it's an int.

        @type key: object
        @param key: Index or key.
        @rtype: object
        @return: An object.
        """
        if type(key) is int:
            key = self.__index[key]
        return dict.__getitem__(self, key)

    def __iter__(self):
        """
        Returns an iterator returning key/value tuples ordered by index.

        @rtype: iterator
        @return: An iterator over the items.
        """
        return ListDictIter(self, 1)

    def __setitem__(self, key, value):
        """
        Adds a key/value pair or replaces the value if the key already exists.

        The key may be an int (=index) when replacing a value.

        @type key: object
        @param key: Key or index if replacing a value.
        @type value: object
        @param value: A value.
        """
        if type(key) is int:
            key = self.__index[key]
        if not self.has_key(key):
            self.__index.append(key)
        dict.__setitem__(self, key, value)

    def clear(self):
        """
        Clears this ListDict.
        """

        dict.clear(self)
        self.__index = []

    def item(self, index):
        """
        Returns the key/value tuple for the given index.

        @type index: int
        @param index: Index of the item (tuple).
        @rtype: tuple
        @return: An item (key/value pair).
        """
        key = self.__index[index]
        return key, dict.__getitem__(self, key)

    def items(self):
        """
        Returns a list of key/value tuples ordered by index.

        @rtype: list
        @return: A list of values.
        """
        ret = []
        for key in self.__index:
            ret.append((key, dict.__getitem__(self, key)))
        return ret

    def iteritems(self):
        """
        Returns an iterator returning key/value tuples ordered by index.

        @rtype: iterator
        @return: An iterator over the items.
        """
        return ListDictIter(self, 0)

    def iterkeys(self):
        """
        Returns an iterator returning keys ordered by index.

        @rtype: iterator
        @return: An iterator over the keys.
        """
        return ListDictIter(self, 1)

    def itervalues(self):
        """
        Returns an iterator returning values ordered by index.

        @rtype: iterator
        @return: An iterator over the values.
        """
        return ListDictIter(self, 2)

    def key(self, index):
        """
        Returns the key for the given index.

        @type index: int
        @param index: Index of the key.
        @rtype: object
        @return: A key.
        """
        return self.__index[index]

    def keys(self):
        """
        Returns a list of keys ordered by index.

        @rtype: list
        @return: A list of keys.
        """
        return self.__index

    def values(self):
        """
        Returns a list of values ordered by index.

        @rtype: list
        @return: A list of values.
        """
        ret = []
        for key in self.__index:
            ret.append(dict.__getitem__(self, key))
        return ret


def sdt_md5():
    """
    Returns a new md5 object.

    For compatibility with python <2.5.
    """
    return hashlib.md5()

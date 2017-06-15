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

from os import stat, remove
from stat import ST_SIZE

from common import *

__doc__ = """SvnDumpNode class."""


class SvnDumpNode:
    """
    A node of a svn dump file.
    """

    def __init__(self, path, action, kind):
        """
        Initializes a new SvnDumpNode.

        @type path: string
        @param path: Path of this node.
        @type action: string
        @param action: Action of this node.
            Valid actions are:
             - 'add'
             - 'delete'
             - 'change'
             - 'replace'
        @type kind: string
        @param kind: Kind of this node ('dir' or 'file').
            If action is 'delete' kind may be the empty string.
        """

        # check action
        if action != "add" and action != "delete" and \
                        action != "change" and action != "replace":
            raise SvnDumpException, "Unknown action '%s'." % action
        # check kind
        if action != "change":
            if kind != "" and kind != "file" and kind != "dir":
                raise SvnDumpException, "Unknown kind '%s'" % kind
        else:
            if kind != "file" and kind != "dir":
                raise SvnDumpException, "Unknown kind '%s'" % kind
        # check path +++

        # path of this node relative to the repository root
        self.__path = path
        # action: 'add', 'change', 'delete' or 'replace'
        self.__action = action
        # kind: 'file', 'dir' or 'node' if not known
        self.__kind = kind
        # list of properties name=>value pairs
        self.__properties = None
        # length of the text (file data)
        self.__text_len = -1
        # md5 hash of the text
        self.__text_md5 = ""
        # the from path if copied else ""
        self.__copy_from_path = ""
        # the from revision if copied else 0
        self.__copy_from_rev = 0
        # offset into the file
        self.__file_offset = -1
        # name of the (temp) file
        self.__file_name = ""
        # delete the temp file
        self.__file_delete = False
        # the file object to read from
        self.__file_obj = None

    def __del__(self):
        """
        Delete method, cleanup temp file if needed.
        """
        if self.__file_delete and self.__file_name != "":
            # delete temp file
            remove(self.__file_name)

    def get_path(self):
        """
        Returns the path of this node.

        @rtype:  string
        @return: The path of this node.
        """
        return self.__path

    def set_path(self, path):
        """
        Sets the path of this node.

        @type path: string
        @param path: New path of this node."""
        self.__path = path

    def get_name(self):
        """
        Returns the name of this node.

        @rtype:  string
        @return: The name of this node.
        """
        return self.__path.split("/")[-1]

    def get_action(self):
        """
        Returns the action of this node.

        @rtype:  string
        @return: Either 'add', 'change', 'delete' or 'replace'.
        """
        return self.__action

    def get_kind(self):
        """
        Returns the kind of this node.

        @rtype: string
        @return: Either 'file', 'dir' or ''.
        """
        return self.__kind

    def get_property(self, name):
        """
        Returns the  value of the property with the given name.

        If the property does not exist None is returned.

        @type name: string
        @param name: A property name.
        @rtype: string
        @return: Value of the property.
        """
        if self.__properties != None and self.__properties.has_key(name):
            return self.__properties[name]
        else:
            return None

    def has_properties(self):
        """
        Returns True if this node has properties.

        @rtype: bool
        @return: True if this node has properties.
        """
        return self.__properties != None

    def get_properties(self):
        """
        Returns the properties as a dict.

        @rtype: dict( string -> string )
        @return: The properties of this node.
        """
        return self.__properties

    def has_text(self):
        """
        Returns true when this node has text.

        @rtype: bool
        @return: True when this node has text.
        """
        return self.__text_len >= 0

    def get_text_length(self):
        """
        Returns the length of the text.

        @rtype: integer
        @return: Length of the text.
        """
        return self.__text_len

    def has_md5(self):
        """
        Returns true when this node has a MD5 sum.

        @rtype: bool
        @return: True when this node has a MD5 sum.
        """
        return len(self.__text_md5) > 0

    def get_text_md5(self):
        """
        Returns the MD5 hash of the text.

        @rtype: string
        @return: MD5 sum of the text.
        """
        return self.__text_md5

    def has_copy_from(self):
        """
        Returns True when this node has copy-from-path and copy-from-rev.

        @rtype: bool
        @return: True if this node has copy-from rev and path.
        """
        return self.__copy_from_rev > 0 and self.__copy_from_path != ""

    def get_copy_from_path(self):
        """
        Returns the path the node has been copied from or an empty string.

        @rtype: string
        @return: copy-from-path.
        """
        return self.__copy_from_path

    def get_copy_from_rev(self):
        """
        Returns the revision the node has been copied from or zero.

        @rtype: integer
        @return: copy-from-rev.
        """
        return self.__copy_from_rev

    def set_copy_from_rev(self, revnr):
        """
        Set the revision the node has been copied from.

        @rtype: integer
        @return: copy-from-rev.
        """
        self.__copy_from_rev = revnr

    def set_copy_from(self, path, revnr):
        """
        Sets copy-from-path and copy-from-rev.

        Only nodes with action 'add' or 'replace' may have copy-from
        revision and path.

        @type path: string
        @param path: copy-from-path
        @type revnr: integer
        @param revnr: copy-from-rev
        """

        if self.__action != "add" and self.__action != "replace":
            raise SvnDumpException, "Cannot set copy-from for action '%s'" \
                                    % self.__action
        self.__copy_from_path = path
        self.__copy_from_rev = revnr

    def set_kind(self, kind):
        """
        Set the kind of this node.

        The kind can only be set if it was empty.

        @type kind: string
        @param kind: New kind, either 'file' or 'dir'.
        """
        if self.__kind != "":
            raise SvnDumpException, "Cannot change node kind"
        if kind != "file" and kind != "dir":
            raise SvnDumpException, "Unknown kind '%s'" % kind
        self.__kind = kind

    def set_property(self, name, value):
        """
        Sets a property of this node.

        Nodes with action 'delete' cannot have properties.

        @type name: string
        @param name: Name of the property.
        @type value: string
        @param value: Value of the property.
        """

        if self.__action == "delete":
            raise SvnDumpException, "Cannot set properties for action '%s'" \
                                    % self.__action
        if self.__properties == None:
            self.__properties = {}
        self.__properties[name] = value

    def del_property(self, name):
        """
        Deletes a property of this node.

        @type name: string
        @param name: Name of the property to delete."""

        if self.__action == "delete":
            raise SvnDumpException, "Cannot delete properties for action '%s'" \
                                    % self.__action
        if self.__properties != None:
            if self.__properties.has_key(name):
                del self.__properties[name]
                if len(self.__properties) == 0:
                    self.__properties = None

    def set_properties(self, properties):
        """
        Sets the properties for this node.

        @type properties: dict( string -> string )
        @param properties: A dict containing the properties.
        """

        if self.__action == "delete":
            raise SvnDumpException, "Cannot set properties for action '%s'" \
                                    % self.__action
        self.__properties = properties

    def set_text_file(self, filename, length=-1, md5="", delete=False):
        """
        Sets the text for this node.

        The text will be read from the specified file.

        @type filename: string
        @param filename: Name of the file containing the text.
        @type length: integer, optional
        @param length: Length of the file.
        @type md5: string, optional
        @param md5: MD5 sum of the text if known.
        @type delete: bool
        @param delete: When True delete the file.
        """

        if self.__action == "delete":
            raise SvnDumpException, "Cannot set text for action '%s'" \
                                    % self.__action
        if self.__kind != "file":
            raise SvnDumpException, "Cannot set text for kind '%s'" \
                                    % self.__kind
        self.__file_name = filename
        self.__file_offset = 0
        # hmm, no destructors, how to delete that damn temp file ? +++
        self.__file_delete = delete
        if length == -1:
            length = stat(filename)[ST_SIZE]
        self.__text_len = length
        self.__text_md5 = md5
        if not is_valid_md5_string(md5):
            self.__calculate_md5()

    def set_text_fileobj(self, fileobj, offset, length, md5):
        """
        Sets the text for this node.

        The text will be read from the specified file object.

        @type fileobj: file object
        @param fileobj: A file object opened for reading and
            containing the text.
        @type offset: integer
        @param offset: Offset of the text.
        @type length: integer
        @param length: Length of the text.
        @type md5: string
        @param md5: MD5 sum of the text.
        """

        if self.__action == "delete":
            raise SvnDumpException, "Cannot set text for action '%s'" \
                                    % self.__action
        if self.__kind != "file":
            raise SvnDumpException, "Cannot set text for kind '%s'" \
                                    % self.__kind
        self.__file_obj = fileobj
        self.__file_offset = offset
        self.__text_len = length
        self.__text_md5 = md5
        # if !is_valid_md5_string( md5 ) or length == -1:
        #    self.__calculate_md5()

    def set_text_node(self, node):
        """
        Sets the text for this node.

        The text will be that of the specified node.

        @type node: SvnDumpNode
        @param node: An other node.
        """

        if self.__action == "delete":
            raise SvnDumpException, "Cannot set text for action '%s'" \
                                    % self.__action
        if self.__kind != "file":
            raise SvnDumpException, "Cannot set text for kind '%s'" \
                                    % self.__kind
        self.__file_name = node.__file_name
        # dunno how to delete temp file so no special action here +++
        self.__file_delete = node.__file_delete
        self.__file_obj = node.__file_obj
        self.__file_offset = node.__file_offset
        self.__text_len = node.__text_len
        self.__text_md5 = node.__text_md5

    def write_text_to_file(self, outfile):
        """
        Writes the text to the given file object.

        @type outfile: file object
        @param outfile: A file object opened for writing.
        """

        if self.__text_len == -1:
            raise SvnDumpException, "Node %s has no text" % self.__path
        if len(self.__file_name) > 0:
            self.__file_obj = open(self.__file_name, "rb")
        else:
            self.__file_obj.seek(self.__file_offset)
        cnt = self.__text_len
        while cnt > 0:
            bcnt = cnt
            if bcnt > 16384:
                bcnt = 16384
            outfile.write(self.__file_obj.read(bcnt))
            cnt = cnt - bcnt
        if len(self.__file_name) > 0:
            self.__file_obj.close()
            self.__file_obj = None

    def text_open(self):
        """
        Open text and return a handle for text read functions.

        Only one handle per dump file should be opened at the same time. A
        node for which the text has been set with set_text_node() virtually
        belongs also to the dump file of the node specified to
        set_text_node().

        Also while the handle is open write_text_to_file() should not be
        called.

        B{See also:} text_reopen(), text_read() and text_close().

        @rtype: 'opaque handle'
        @return: A handle for the text read functions.
        """

        if self.__text_len == -1:
            raise SvnDumpException, "node has no text"

        # create handle
        handle = {}
        if len(self.__file_name) > 0:
            handle["file_obj"] = open(self.__file_name, "rb")
            handle["close"] = True
            handle["offset"] = 0
            handle["length"] = self.__text_len
            handle["pos"] = 0
        else:
            handle["file_obj"] = self.__file_obj
            handle["close"] = False
            handle["offset"] = self.__file_offset
            handle["length"] = self.__text_len
            handle["pos"] = 0
            self.__file_obj.seek(self.__file_offset)

        return handle

    def text_reopen(self, handle):
        """
        Reopen the handle.

        Repositions the handle to the start of the text.

        B{See also:} text_open(), text_read() and text_close().

        @type handle: handle
        @param handle: A handle opened with text_open().
        """

        handle["file_obj"].seek(handle["offset"])
        handle["pos"] = 0

    def text_read(self, handle, count=16384):
        """
        Read some text from a handle.

        B{See also:} text_open(), text_reopen() and text_close().

        @type handle: handle
        @param handle: A handle opened with text_open().
        @type count: integer, optional
        @param count: Count of bytes to read.
        @rtype: string
        @return: The data read.
        """

        # end of text ?
        if handle["pos"] >= handle["length"]:
            return ""

        # is more text requested than remains
        if (handle["pos"] + count) > handle["length"]:
            count = handle["length"] - handle["pos"]
        # read it
        data = handle["file_obj"].read(count)
        handle["pos"] = handle["pos"] + count
        return data

    def text_close(self, handle):
        """
        Close the handle.

        B{See also:} text_open(), text_reopen() and text_read().

        @type handle: handle
        @param handle: A handle opened with text_open().
        """

        if handle["close"]:
            handle["file_obj"].close()

    def __calculate_md5(self):
        """
        Calculates the md5 of the text of this node.
        """

        handle = self.text_open()
        md = sdt_md5()
        data = self.text_read(handle)
        n = 0
        while len(data) > 0:
            n = n + len(data)
            md.update(data)
            data = self.text_read(handle)
        self.__text_md5 = md.hexdigest()
        if self.__text_len == -1:
            self.__text_len = n
        self.text_close(handle)

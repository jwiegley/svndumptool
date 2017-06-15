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

from common import *
from node import SvnDumpNode

__doc__ = """SvnDumpFile class."""


class SvnDumpFile:
    """
    A class for reading and writing svn dump files.
    """

    def __init__(self):
        # states
        self.ST_NONE = 0
        self.ST_READ = 10
        self.ST_EOF = 11
        self.ST_CREATE = 20
        self.ST_WRITE = 21

        # state of this SvnDumpFile
        self.__state = self.ST_NONE
        # name of the dump file
        self.__filename = ""
        # the file object to read from/write to
        self.__file = None
        # end of file
        self.__file_eof = 0
        # UUID of the repository
        self.__uuid = None
        # curent revision number
        self.__rev_nr = 0
        # date of the revision
        self.__rev_date = (0, 0)
        # start offset of the next revision
        self.__rev_start_offset = 0
        # revision properties
        self.__rev_props = {}
        # nodes of the revision (files, dirs)
        self.__nodes = ListDict()
        # offset of a tag list
        self.__tag_start_offset = 0
        # count lines for debugging
        self.__line__counting = 1
        self.__line_nr = 0
        self.__tag_start_line_nr = 0

    def __read_line(self, raiseEof):
        """
        Read one line from teh dump file.

        @type raiseEof: bool
        @param raiseEof: Raise SvnDumpException when True and EOF occured.
        @rtype: bool, string
        @return: (eof, line), line without LF.
        """

        line = self.__file.readline()
        if self.__line__counting != 0:
            self.__line_nr = self.__line_nr + 1
        if len(line) != 0:
            return False, line[:-1]
        self.__file_eof = 1
        if not raiseEof:
            return True, ""
        raise SvnDumpException("unexpected end of file")

    def __read_bin(self, length):
        """
        Read some  bytes.

        @type length: integer
        @param length: Count of bytes to read.
        @rtype: string
        @return: The data read.
        """

        data = self.__file.read(length)
        if self.__line__counting != 0:
            self.__line_nr = self.__line_nr + data.count("\n")
        return data

    def __skip_bin(self, length):
        """
        Skip some bytes.

        @type length: integer
        @param length: Count of bytes to skip.
        """

        if self.__line__counting == 0:
            self.__file.seek(self.__file.tell() + length)
            return
        nBytes = 4096
        while length > 0:
            if length < 4096:
                nBytes = length
            data = self.__file.read(nBytes)
            self.__line_nr = self.__line_nr + data.count("\n")
            length = length - nBytes

    def __skip_empty_line(self):
        """
        Read one line from the dump file and check that it is empty.
        """

        eof, line = self.__read_line(False)
        if eof or len(line) != 0:
            raise SvnDumpException("expected empty line, found '%s'" % line)
        return

    def __get_tag(self, raiseEof):
        """
        Read a Tag line (name: value).

        @type raiseEof: bool
        @param raiseEof: Raise SvnDumpException when True and EOF occured.
        @rtype: list( string )
        @return: A list containing the tag name and value.
        """

        eof, line = self.__read_line(raiseEof)
        if len(line) == 0:
            return []
        words = line.split(" ", 1)
        if len(words) != 2:
            raise SvnDumpException("illegal Tag line '%s'" % line)
        return words

    def __get_tag_list(self):
        """
        Get a list of tags, end is an empty line.

        @rtype: dict( string -> string )
        @return: A dict containing the tags.
        """

        tags = {}
        self.__tag_start_offset = self.__file.tell()
        self.__tag_start_line_nr = self.__line_nr
        tag = self.__get_tag(False)
        while len(tag) == 0:
            if self.__file_eof:
                return tags
            self.__tag_start_offset = self.__file.tell()
            self.__tag_start_line_nr = self.__line_nr
            tag = self.__get_tag(False)
        while len(tag) == 2:
            tags[tag[0]] = tag[1]
            tag = self.__get_tag(True)
        return tags

    def __get_prop_list(self):
        """
        Get a list of properties.

        @rtype: dict( string -> string )
        @return: A dict containing the properties.
        """

        props = ListDict()
        eof, line = self.__read_line(True)
        while line != "PROPS-END":
            # key
            words = line.split()
            if len(words) != 2 or (words[0] != "K" and words[0] != "D"):
                raise SvnDumpException("illegal proprty key ???")
            key = self.__read_bin(int(words[1]))
            self.__skip_empty_line()
            # value
            value = None
            if words[0] == "K":
                eof, line = self.__read_line(True)
                words = line.split()
                if len(words) != 2 or words[0] != "V":
                    raise SvnDumpException("illegal proprty value ???")
                value = self.__read_bin(int(words[1]))
                self.__skip_empty_line()
            # set property
            props[key] = value
            # next line...
            eof, line = self.__read_line(True)
        return props

    def __create_prop_string(self, properties):
        """
        Create a string from a dict containing properties.

        @type properties: dict( string -> string )
        @param properties: A dict containing the properties.
        @rtype: string
        @return: A string containing the properties.
        """

        propStr = ""
        if properties is not None:
            for key, val in properties.items():
                if val is not None:
                    # add/change property
                    propStr = propStr + ("K %d" % len(key)) + "\n" + key + "\n"
                    propStr = propStr + ("V %d" % len(val)) + "\n" + val + "\n"
                else:
                    # delete property
                    propStr = propStr + ("D %d" % len(key)) + "\n" + key + "\n"
            propStr = propStr + "PROPS-END\n"
        return propStr

    # ------------------------------------------------------------
    #  open / create / close

    def open(self, filename):
        """
        Open a dump file for reading and read the header.
        @type filename: string
        @param filename: Name of an existing dump file.
        """

        # check state
        if self.__state != self.ST_NONE:
            raise SvnDumpException("invalid state %d (should be %d)" % \
                                   (self.__state, self.ST_NONE))

        # set parameters
        self.__filename = filename

        # open the file for reading
        self.__file = open(filename, "rb")

        # check that it is a svn dump file
        tag = self.__get_tag(True)
        if tag[0] != "SVN-fs-dump-format-version:":
            raise SvnDumpException("not a svn dump file ???")
        if tag[1] != "2":
            raise SvnDumpException("wrong svn dump file version (expected 2 found %s)" % (tag[1]))
        self.__skip_empty_line()

        # get UUID
        fileoffset = self.__file.tell()
        tag = self.__get_tag(True)
        if len(tag) < 1 or tag[0] != "UUID:":
            # back to start of revision
            self.__file.seek(fileoffset)
            self.__uuid = None
        else:
            # set UUID
            self.__uuid = tag[1]
            self.__skip_empty_line()

        # done initializing
        self.__rev_start_offset = self.__file.tell()
        self.__state = self.ST_READ

    def create_with_rev_0(self, filename, uuid, rev0date):
        """
        Create a new dump file starting with revision 0.

        @type filename: string
        @param filename: Name of the new dump file.
        @type uuid: string
        @param uuid: UUID of the new dump file or None.
        @type rev0date: string
        @param rev0date: Svn date string for revision 0.
        """

        # check state
        if self.__state != self.ST_NONE:
            raise SvnDumpException("invalid state %d (should be %d)" % \
                                   (self.__state, self.ST_NONE))

        # set parameters
        self.__filename = filename
        self.__uuid = uuid

        # check rev0date
        rev0date = self.set_rev_date(rev0date)

        # open file for writing
        self.__file = open(filename, "wb")

        # write header and uuid
        self.__file.writelines(["SVN-fs-dump-format-version: 2\n", "\n"])
        if self.__uuid is not None:
            self.__file.writelines(["UUID: " + self.__uuid + "\n", "\n"])

        # write header and uuid
        self.__file.writelines(["Revision-number: 0\n",
                                "Prop-content-length: 56\n",
                                "Content-length: 56\n",
                                "\n",
                                "K 8\n",
                                "svn:date\n",
                                "V 27\n",
                                rev0date + "\n",
                                "PROPS-END\n",
                                "\n"])

        # done initializing
        self.__state = self.ST_CREATE

    def create_with_rev_n(self, filename, uuid, firstRevNr):
        """
        Create a new dump file.

        @type filename: string
        @param filename: Name of the new dump file.
        @type uuid: string
        @param uuid: UUID of the new dump file or None.
        @type firstRevNr: integer
        @param firstRevNr: First revision number (>0).
        """

        # check state
        if self.__state != self.ST_NONE:
            raise SvnDumpException("invalid state %d (should be %d)" % \
                                   (self.__state, self.ST_NONE))

        # check firstRevNr
        if firstRevNr < 1:
            raise SvnDumpException("invalid firstRevNr %d (should be >= 1)" % (firstRevNr))

        # set parameters
        self.__filename = filename
        self.__uuid = uuid
        self.__rev_nr = firstRevNr - 1

        # open file for writing
        self.__file = open(filename, "wb")

        # write header and uuid
        self.__file.writelines(["SVN-fs-dump-format-version: 2\n", "\n"])
        if self.__uuid is not None:
            self.__file.writelines(["UUID: " + self.__uuid + "\n", "\n"])

        # done initializing
        self.__state = self.ST_CREATE

    def create_like(self, filename, srcfile):
        """
        Creates this dump file like srcfile.

        If the current revision number of srcfile is zero create_with_rev_0()
        is called on this dump file and read_next_rev() is called on srcfile.

        If the current revision number of srcdump is greater than zero
        create_with_rev_n() is called.

        In both cases True is returned if srcdump contains a revision and
        False if srcdump reached EOF.

        @type filename: string
        @param filename: Name of the new dump file.
        @type srcfile: SvnDumpFile
        @param srcfile: A dump file.
        @rtype: bool
        @return: False if EOF occured on srcfile.
        """

        hasrev = srcfile.has_revision()
        if srcfile.get_rev_nr() == 0:
            # create new dump with revision 0
            self.create_with_rev_0(filename, srcfile.get_uuid(),
                                   srcfile.get_rev_date_str())
            srcfile.read_next_rev()
        else:
            # create new dump starting with the same revNr as srcdump
            self.create_with_rev_n(filename, srcfile.get_uuid(),
                                   srcfile.get_rev_nr())
        return srcfile.has_revision()

    def close(self):
        """
        Close this svn dump file.
        """

        # close only if state != ST_NONE
        if self.__state != self.ST_NONE:
            self.__file.close()
            self.__line_nr = 0
            self.__file_eof = 0
            self.__filename = None
            self.__uuid = None
            self.__file = None
            self.__rev_props = None
            self.__nodes.clear()
            self.__state = self.ST_NONE

    # ------------------------------------------------------------
    #  read methods

    def read_next_rev(self):
        """
        Read the next revision.

        @rtype: bool
        @return: False if EOF occured.
        """

        # check state
        if self.__state != self.ST_READ:
            raise SvnDumpException("invalid state %d (should be %d)" % \
                                   (self.__state, self.ST_READ))

        # check for end of file
        if self.__file_eof:
            self.__state = self.ST_EOF
            return False

        # go to start of revision
        if self.__rev_start_offset != self.__file.tell():
            self.__file.seek(self.__rev_start_offset)

        # get rev tags
        tags = self.__get_tag_list()
        self.__rev_nr = int(tags["Revision-number:"])

        # read revision properties
        self.__rev_props = self.__get_prop_list()
        self.__skip_empty_line()
        if not self.__rev_props.has_key("svn:log"):
            self.__rev_props["svn:log"] = ""
        if not self.__rev_props.has_key("svn:author"):
            self.__rev_props["svn:author"] = ""
        if self.__rev_props.has_key("svn:date"):
            self.set_rev_date(self.__rev_props["svn:date"])
        else:
            self.set_rev_date("")

        # read nodes (files, dirs)
        self.__nodes.clear()
        # self.nodeList = []
        tags = self.__get_tag_list()
        while len(tags) != 0:
            # check that it's not the next revision
            if tags.has_key("Revision-number:"):
                # go back to start of tag list
                self.__file.seek(self.__tag_start_offset)
                self.__line_nr = self.__tag_start_line_nr
                break
            # get node properties
            if tags.has_key("Prop-content-length:"):
                properties = self.__get_prop_list()
            else:
                properties = None
            # skip node data
            if tags.has_key("Text-content-length:"):
                tags["Text-content-length:"] = int(tags["Text-content-length:"])
                offset = self.__file.tell()
                self.__skip_bin(tags["Text-content-length:"])
                self.__skip_empty_line()
            else:
                offset = 0
            # add node
            path = tags["Node-path:"].lstrip('/')
            action = tags["Node-action:"]
            kind = ""
            if tags.has_key("Node-kind:"):
                kind = tags["Node-kind:"]
            node = SvnDumpNode(path, action, kind)
            if properties is not None:
                node.set_properties(properties)
            if tags.has_key("Node-copyfrom-path:"):
                node.set_copy_from(tags["Node-copyfrom-path:"].lstrip('/'),
                                   int(tags["Node-copyfrom-rev:"]))
            if tags.has_key("Text-content-md5:"):
                md5 = tags["Text-content-md5:"]
            else:
                md5 = ""
            if tags.has_key("Text-content-length:"):
                node.set_text_fileobj(self.__file, offset,
                                      int(tags["Text-content-length:"]),
                                      md5)
            upath = (action[0].upper(), path)
            self.__nodes[upath] = node
            # next one...
            tags = self.__get_tag_list()

        self.__rev_start_offset = self.__file.tell()
        return True

    def has_revision(self):
        """
        Returns false when EOF occured.

        @rtype: bool
        @return: False if EOF occured.
        """
        return self.__state == self.ST_READ or self.__state == self.ST_WRITE

    def get_uuid(self):
        """
        Returns the UUID of this dump file.

        @rtype: string
        @return: UUID of this dump file or None if it doesn't have one.
        """
        return self.__uuid

    def get_rev_nr(self):
        """
        Returns the current revision number.

        @rtype: integer
        @return: The current revision number.
        """
        return self.__rev_nr

    def get_rev_date(self):
        """
        Returns the date of the current revision as ( time_t, micros ).

        @rtype: list( integer )
        @return: The revision date.
        """
        return self.__rev_date

    def get_rev_date_str(self):
        """
        Returns the date of the current revision as string.

        @rtype: string
        @return: The revision date.
        """
        return self.__rev_props["svn:date"]

    def get_rev_author(self):
        """
        Returns the author of the current revision.

        @rtype: string
        @return: Author of the current revision.
        """
        return self.__rev_props["svn:author"]

    def get_rev_log(self):
        """
        Returns the log message of the current revision.

        @rtype: string
        @return: The log message.
        """
        return self.__rev_props["svn:log"]

    def get_rev_prop_names(self):
        """
        Returns a list of revision property names of the current revision.

        @rtype: list( string )
        @return: A list of revision property names.
        """
        return self.__rev_props.keys()

    def has_rev_prop(self, name):
        """
        Returns true if the revision has a property with the specified name.

        @rtype: bool
        @return: True if the revision has that property.
        """
        return self.__rev_props.has_key(name)

    def get_rev_props(self):
        """
        Returns a dict containing the revision properties.

        @rtype: dict( string -> string )
        @return: The revision properties.
        """
        return self.__rev_props

    def get_rev_prop_value(self, name):
        """
        Returns the value of the revision property with the specified name.

        @type name: string
        @param name: Name of the property.
        @rtype: string
        @return: The value of the revision property.
        """
        return self.__rev_props[name]

    def get_node_count(self):
        """
        Returns the count of nodes of the current revision.

        @rtype: integer
        @return: Node count of the curent revision.
        """
        return len(self.__nodes)

    def get_node(self, index):
        """
        Returns the node at the given index.

        @type index: integer
        @param index: Index of the node to return.
        @rtype: SvnDumpNode
        @return: The node at the given index.
        """
        return self.__nodes[index]

    def get_nodes_by_path(self, path, actions="ACDR"):
        """
        Returns a list of nodes matching path and actions.

        Actions is a string that may contain one or more of the letters
        A, C, D and R which are the first letters of the actions Add, Change,
        Delete and Replace.

        @type path: string
        @param path: Path of the node.
        @type actions: string
        @param actions: Actions to search for.
        """

        nodes = []
        for a in actions:
            upath = (a, path)
            if self.__nodes.has_key(upath):
                nodes.append(self.__nodes[upath])
        return nodes

    def get_nodes_iter(self):
        """
        Returns an iterator returning the nodes.
        """

        return self.__nodes.values()

    # ------------------------------------------------------------
    #  write methods

    def set_rev_date(self, dateStr):
        """
        Check a date string, set and return a valid one.

        @type dateStr: string
        @param dateStr: A svn date string.
        @rtype: string
        @return: A svn date string.
        """
        self.__rev_date = parse_svn_date_str(dateStr)
        self.__rev_props["svn:date"] = create_svn_date_str(self.__rev_date)
        return self.__rev_props["svn:date"]

    def set_rev_author(self, author):
        """
        Set the author of this revision.

        @type author: string
        @param author: The author to set for this revision.
        """
        self.__rev_props["svn:author"] = author

    def set_rev_log(self, logMsg):
        """
        Set the log message of this revision.

        @type logMsg: string
        @param logMsg: The log message to set for this revision.
        """
        self.__rev_props["svn:log"] = logMsg

    def set_rev_prop_value(self, name, value):
        """
        Set the value of the revision property with the specified name to the given value.

        @type name: string
        @param name: Name of the property.
        @type value: string
        @param value: Value of the property.
        """
        if name == "svn:date":
            self.set_rev_date(value)
        else:
            self.__rev_props[name] = value

    def set_uuid(self, uuid):
        """
        Returns the UUID of this dump file.

        @type uuid: string
        @param uuid: UUID to set for this dump file (may be None).
        """
        self.__uuid = uuid

    def add_rev_from_dump(self, dump):
        """
        Add the current revision of the specified SvnDumpFile to this one.
        
        @type dump: SvnDumpFile
        @param dump: A dump file.
        """

        # check of state is done in add_rev
        # add revision and revprops
        self.add_rev(dump.get_rev_props())

        # add nodes
        index = 0
        nodeCount = dump.get_node_count()
        while index < nodeCount:
            self.add_node(dump.get_node(index))
            index = index + 1

    def add_rev(self, revProps):
        """
        Add a new revision to this dump file.

        @type revProps: dict( string -> string )
        @param revProps: A dict with revision properties.
        """

        # check state
        if self.__state != self.ST_WRITE and self.__state != self.ST_CREATE:
            raise SvnDumpException("invalid state %d (should be %d or %d)" % (
                self.__state, self.ST_CREATE, self.ST_WRITE))

        # set rev nr and check rev props
        self.__rev_nr = self.__rev_nr + 1
        if not revProps.has_key("svn:date"):
            revProps["svn:date"] = self.set_rev_date("")
        else:
            revProps["svn:date"] = self.set_rev_date(revProps["svn:date"])
        if not revProps.has_key("svn:author"):
            revProps["svn:author"] = ""
        if not revProps.has_key("svn:log"):
            revProps["svn:log"] = ""
        self.__rev_props = revProps

        propStr = self.__create_prop_string(revProps)
        # write revision
        self.__file.writelines(["Revision-number: %d\n" % self.__rev_nr,
                                "Prop-content-length: %d\n" % len(propStr),
                                "Content-length: %d\n" % len(propStr),
                                "\n",
                                propStr,
                                "\n"])

        # we have a revision now
        self.__state = self.ST_WRITE

    def add_node(self, node):
        """
        Add a node to the current revision.

        This method uses SvnDumpNode.write_text_to_file().

        @type node: SvnDumpNode
        @param node: The node to add.
        """

        # check state
        if self.__state != self.ST_WRITE:
            raise SvnDumpException("invalid state %d (should be %d)" % \
                                   (self.__state, self.ST_WRITE))

        # write the node
        self.__file.write("Node-path: " + node.get_path() + "\n")

        # write kind if we know it (cvs2svn emits add's with copy-from
        # without kind so we do this here independent of the action)
        kind = node.get_kind()
        if len(kind) > 0:
            self.__file.write("Node-kind: %s\n" % kind)

        action = node.get_action()
        self.__file.write("Node-action: " + action + "\n")
        if action != "delete":
            # copied ?
            if node.get_copy_from_rev() != 0:
                self.__file.write("Node-copyfrom-rev: %d\n" % \
                                  node.get_copy_from_rev())
                self.__file.write("Node-copyfrom-path: " + \
                                  node.get_copy_from_path() + "\n")
            # calculate length's of properties text and total
            propstr = self.__create_prop_string(node.get_properties())
            proplen = len(propstr)
            textlen = node.get_text_length()
            if node.has_text():
                totlen = proplen + textlen
            else:
                totlen = proplen
            # write length's of properties text and total
            if proplen > 0:
                self.__file.write("Prop-content-length: %d\n" % proplen)
            if node.has_text():
                self.__file.write("Text-content-length: %d\n" % textlen)
            if node.has_md5():
                self.__file.write("Text-content-md5: %s\n" % node.get_text_md5())
            if proplen > 0 or node.has_text():
                self.__file.write("Content-length: %d\n" % totlen)
                self.__file.write("\n")
            # write properties
            if proplen > 0:
                self.__file.write(propstr)
            # write text
            if node.has_text():
                node.write_text_to_file(self.__file)
            self.__file.write("\n")
        # CR after each node
        self.__file.write("\n")


class SvnDumpFileWithHistory(SvnDumpFile):
    def __init__(self):
        SvnDumpFile.__init__(self)
        # errors
        self.ERR_REV_DATE_OLDER = 1
        self.ERR_NODE_MD5_FAIL = 2
        self.ERR_NODE_EXISTS = 3
        self.ERR_NODE_NO_PARENT = 4
        self.ERR_NODE_PARENT_NOT_DIR = 5
        self.ERR_NODE_NO_COPY_SRC = 6
        self.ERR_NODE_GONE = 7
        # node history for this
        self.__enable_nodehist = False
        self.__nodehist = {}
        # check actions
        self.__enable_check_node_actions = False
        # check dates
        self.__enable_check_rev_dates = False
        self.__prev_date = (0, 0)
        # check md5 sums
        self.__enable_check_node_md5 = False
        # revision errors
        self.__rev_errors = {}

    def set_enable_node_history(self, enable):
        """
        Set the check md5 sums flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__enable_nodehist = enable

    def set_check_actions(self, docheck):
        """
        Set the check actions flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__enable_check_node_actions = docheck
        # checking node actions requires keeping node history,
        # but it can also be enabled otherwise, so don't disable
        # it if not checking node actions
        if self.__enable_check_node_actions:
            self.set_enable_node_history(True)

    def set_check_dates(self, docheck):
        """
        Set the check dates flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__enable_check_rev_dates = docheck

    def set_check_md5(self, docheck):
        """
        Set the check md5 sums flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__enable_check_node_md5 = docheck

    def get_rev_errors(self, revnr=None):
        """
        Returns a list of the dump errors for the given revision. (Obviously)
        It will only report errors enabled by set_check_xxxx.

        @type revnr: int
        @param revnr: (Optional) Number of desired revision
        @rtype: list of lists (of lists)
        @return: Each element in the list is a list representing one error,
            with the following members:
                - The error type (SvnDumpFile.ERR_XXXX)
                - A list of error information:
                    - for ERR_REV_DATE_OLDER: [ revdatestr, prevdatestr ]
                    - for ERR_NODE_MD5_FAIL: [ path, md5calc, md5node ]
                    - for ERR_NODE_XXXX: [ path, action, ... ]
                        - for ERR_NODE_NO_PARENT: [ path, action, parentpath ]
                        - for ERR_NODE_PARENT_NOT_DIR: [ path, action, parentpath ]
                        - for ERR_NODE_NO_COPY_SRC: [ path, action, cfrev, cfpath ]
            Errors in this list are guaranteed to be in order of revision
            errors, then node errors in the same order as when iterated via
            get_nodes_iter().
        """

        # use the current rev number if not gien
        if revnr is None:
            revnr = self.get_rev_nr()
        if self.__rev_errors.has_key(revnr):
            return self.__rev_errors[revnr]
        else:
            return None

    def __add_rev_error(self, revnr, errinfo):
        """
        Adds the given error information to the ListDict for the given revision

        @type revnr: int
        @param revnr: (Optional) Number of desired revision
        @type errinfo: list
        @param errinfo: Information about the error
        """

        if self.__rev_errors.has_key(revnr):
            self.__rev_errors[revnr].append(errinfo)
        else:
            self.__rev_errors[revnr] = [errinfo]

    def __check_rev_dates(self):
        """
        Check the date for the current revision
        """
        if self.__enable_check_rev_dates:
            date = self.get_rev_date()
            if date < self.__prev_date:
                self.__add_rev_error(self.get_rev_nr(),
                                     [self.ERR_REV_DATE_OLDER, [self.get_rev_date_str(),
                                                                create_svn_date_str(self.__prev_date)]], )
            self.__prev_date = date

    def __check_node_md5(self, node):
        """
        Check the md5sum for the current node

        @type node: SvnDumpNode
        @param node: Current node
        """
        if self.__enable_check_node_md5 and node.has_text():
            md = sdt_md5()
            handle = node.text_open()
            data = node.text_read(handle)
            n = 0
            while len(data) > 0:
                n = n + len(data)
                md.update(data)
                data = node.text_read(handle)
            node.text_close(handle)
            md5sum = md.hexdigest()
            if node.get_text_md5() != md5sum:
                self.__add_rev_error(self.get_rev_nr(),
                                     [self.ERR_NODE_MD5_FAIL,
                                      [node.get_path(), md5sum, node.get_text_md5()]], )

    def __nodehist_init(self):
        """
        Initialize the node history
        """

        # the root always exists and is a directory
        self.__nodehist = {"": ["D", [0, 999999999]]}
        self.__rev_errors.clear()

    def nodehist_get_kind(self, revnr, path):
        """
        Returns the kind of a node if it exists, else None.

        @type revnr: int
        @param revnr: Current revision number.
        @type path: string
        @param path: Path of a node.
        @rtype: string
        @return: "D" for dirs, "F" for files or None.
        """
        return self.__nodehist_get_kind(revnr, path)

    def __nodehist_get_kind(self, revnr, path):
        """
        Returns the kind of a node if it exists, else None.

        @type revnr: int
        @param revnr: Current revision number.
        @type path: string
        @param path: Path of a node.
        @rtype: string
        @return: "D" for dirs, "F" for files or None.
        """
        if not self.__nodehist.has_key(path):
            return None
        nodehist = self.__nodehist[path]
        i = self.__nodehist_get_rev_index(nodehist, revnr)
        if i is None:
            return None
        return nodehist[0][0]

    def __nodehist_get_rev_index(self, nodehist, revnr):
        """
        Returns the index into the node history or None.

        @type nodehist: list
        @param nodehist: History of a node.
        @type revnr: int
        @param revnr: Current revision number.
        """
        i = len(nodehist) - 1
        while i > 0 and revnr < nodehist[i][0]:
            i -= 1
        if i == 0:
            return None
        if revnr > nodehist[i][1] and nodehist[i][1] >= 0:
            return None
        return i

    def __nodehist_add_node(self, revnr, node):
        """
        Adds a node to the history, recursively if it has copy-from path/rev.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Node to add.
        """
        path = node.get_path()
        if not self.__nodehist.has_key(path):
            # create revision list for path
            kind = "D"
            if node.get_kind() == "file":
                kind = "F"
            self.__nodehist[path] = [(kind)]
        # add revision range
        self.__nodehist[path].append([revnr, -1])
        kind = self.__nodehist[path][0][0]
        # continue only if it's a dir with copy-from
        if kind == "F" or not node.has_copy_from():
            return
        # recursive copy
        cfpath = node.get_copy_from_path() + "/"
        cfpathlen = len(cfpath)
        cfrev = node.get_copy_from_rev()
        path += "/"
        for cfnodepath in self.__nodehist.keys()[:]:
            if cfnodepath.startswith(cfpath):
                cfnodehist = self.__nodehist[cfnodepath]
                i = self.__nodehist_get_rev_index(cfnodehist, cfrev)
                if i is not None:
                    npath = path + cfnodepath[cfpathlen:]
                    # add new path
                    if not self.__nodehist.has_key(npath):
                        # create revision list for npath
                        kind = "D"
                        if node.get_kind() == "file":
                            kind = "F"
                        self.__nodehist[npath] = [cfnodehist[0]]
                    # add revision range
                    self.__nodehist[npath].append([revnr, -1])

    def __nodehist_delete_node(self, revnr, node):
        """
        Deletes a node from the history, recursively if it is a directory.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Node to add.
        """
        # set end revision
        path = node.get_path()
        self.__nodehist[path][-1][1] = revnr - 1
        kind = self.__nodehist[path][0][0]
        # continue only if it's a dir
        if kind == "F":
            return
        # recursive delete
        path += "/"
        for nodepath in self.__nodehist.keys()[:]:
            if nodepath.startswith(path):
                nodehist = self.__nodehist[nodepath]
                if nodehist[-1][1] == -1:
                    nodehist[-1][1] = revnr - 1

    def __nodehist_process_node(self, node):
        """
        Checks the action of a node and keeps it's history.

        @type node: SvnDumpNode
        @param node: Current node.
        """
        if not self.__enable_nodehist:
            return
        revnr = self.get_rev_nr()
        path = node.get_path()
        action = node.get_action()
        kind = self.__nodehist_get_kind(revnr, path)
        err = False
        if action == "add":
            if self.__enable_check_node_actions:
                # path must not exist
                if kind is not None:
                    self.__add_rev_error(revnr, [self.ERR_NODE_EXISTS,
                                                 [path, action]], )
                    err = True
                else:
                    # parent must be a dir
                    slash = path.rfind("/")
                    if slash > 0:
                        ppath = path[:slash]
                        pkind = self.__nodehist_get_kind(revnr, ppath)
                        if pkind is None:
                            self.__add_rev_error(revnr,
                                                 [self.ERR_NODE_NO_PARENT,
                                                  [path, action, ppath]], )
                            err = True
                        elif pkind != "D":
                            self.__add_rev_error(revnr,
                                                 [self.ERR_NODE_PARENT_NOT_DIR,
                                                  [path, action, ppath]], )
                            err = True
                    # copy-from must exist
                    if node.has_copy_from():
                        cfrev = node.get_copy_from_rev()
                        cfpath = node.get_copy_from_path()
                        if self.__nodehist_get_kind(cfrev, cfpath) is None:
                            self.__add_rev_error(revnr,
                                                 [self.ERR_NODE_NO_COPY_SRC,
                                                  [path, action, cfrev, cfpath]], )
                            err = True
            if not err or self.__state == self.ST_WRITE:
                self.__nodehist_add_node(revnr, node)
        elif action == "delete":
            if self.__enable_check_node_actions:
                # path must exist
                if kind is None:
                    self.__add_rev_error(revnr,
                                         [self.ERR_NODE_GONE, [path, action]], )
                    err = True
            if not err or self.__state == self.ST_WRITE:
                self.__nodehist_delete_node(revnr, node)
        else:
            if self.__enable_check_node_actions:
                # path must exist
                if kind is None:
                    self.__add_rev_error(revnr,
                                         [self.ERR_NODE_GONE, [path, action]], )
                    err = True
            # replace = delete & add; changes can be ignored
            if action == "replace" and node.has_copy_from():
                if not err or self.__state == self.ST_WRITE:
                    self.__nodehist_delete_node(revnr, node)
                    self.__nodehist_add_node(revnr, node)

    def open(self, filename):
        """
        Open a dump file for reading and read the header.
        @type filename: string
        @param filename: Name of an existing dump file.
        """

        SvnDumpFile.open(self, filename)
        self.__nodehist_init()

    def create_with_rev_0(self, filename, uuid, rev0date):
        """
        Create a new dump file starting with revision 0.

        @type filename: string
        @param filename: Name of the new dump file.
        @type uuid: string
        @param uuid: UUID of the new dump file or None.
        @type rev0date: string
        @param rev0date: Svn date string for revision 0.
        """

        SvnDumpFile.create_with_rev_0(self, filename, uuid, rev0date)
        self.__nodehist_init()

    def create_with_rev_n(self, filename, uuid, firstRevNr):
        """
        Create a new dump file.

        @type filename: string
        @param filename: Name of the new dump file.
        @type uuid: string
        @param uuid: UUID of the new dump file or None.
        @type firstRevNr: integer
        @param firstRevNr: First revision number (>0).
        """

        SvnDumpFile.create_with_rev_n(self, filename, uuid, firstRevNr)
        self.__nodehist_init()

    def close(self):
        """
        Close this svn dump file.
        """

        SvnDumpFile.close(self)
        # +++ maybe close should call a protected _close() function which
        # does this here? (clearing things too often doesn't hurt too much)
        self.__nodehist = {}
        self.__rev_errors.clear()
        self.__prev_date = (0, 0)

    def read_next_rev(self):
        """
        Read the next revision.

        @rtype: bool
        @return: False if EOF occured.
        """

        SvnDumpFile.read_next_rev(self)
        self.__check_rev_dates()
        for node in self.get_nodes_iter():
            self.__check_node_md5(node)
            self.__nodehist_process_node(node)

    def add_rev(self, revProps):
        """
        Add a new revision to this dump file.

        @type revProps: dict( string -> string )
        @param revProps: A dict with revision properties.
        """

        SvnDumpFile.add_rev(self, revProps)
        self.__check_rev_dates()

    def add_node(self, node):
        """
        Add a node to the current revision.

        This method uses SvnDumpNode.write_text_to_file().

        @type node: SvnDumpNode
        @param node: The node to add.
        """

        SvnDumpFile.add_node(self, node)
        # self.__check_node_md5() # here for completeness, but redundant!
        self.__nodehist_process_node(node)

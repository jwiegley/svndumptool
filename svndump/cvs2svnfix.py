# ===============================================================================
#
# Copyright (C) 2007 Martin Furter <mf@rola.ch>
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

import sys
from optparse import OptionParser

from svndump import __version, copy_dump_file
from common import create_svn_date_str
from file import SvnDumpFile

__doc__ = """Various tools."""


# -------------------------------------------------------------------------------
# check

class SvnDumpCvs2SvnFix:
    """
    A class for cvs2svn created dump files.
    """

    def __init__(self):
        """
        Initialize.
        """

        self.__history = {}

    def execute(self, inputfile, outputfile):
        """
        Fix a cvs2svn created dump file.

        @type inputfile: string
        @param inputfile: Name of the cvs2svn created dump file.
        @type outputfile: string
        @param outputfile: Name of the fixed dump file.
        """

        indump = SvnDumpFile()
        indump.open(inputfile)
        has_rev = indump.read_next_rev()
        outdump = SvnDumpFile()
        outdump.create_like(outputfile, indump)
        rc = 0
        self.__history = {}

        while has_rev and rc == 0:
            outdump.add_rev(indump.get_rev_props())
            for node in indump.get_nodes_iter():
                msglist = self.__fix_node(indump.get_rev_nr(), node)
                if msglist is not None:
                    rc = 1
                    print("Error in r%d node %s:" %
                          (indump.get_rev_nr(), node.get_path()))
                    for msg in msglist:
                        print("  " + msg)
                    break
                outdump.add_node(node)
            has_rev = indump.read_next_rev()

        indump.close()
        return rc

    def __fix_node(self, revnr, node):
        """
        Checks the action of a node and keeps it's history.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Current node.
        """
        path = node.get_path()
        action = node.get_action()
        kind = None
        if action == "add":
            # path must not exist
            if self.__node_kind(revnr, path) is not None:
                return ["Node already exists."]
            # parent must be a dir
            slash = path.rfind("/")
            if slash > 0:
                ppath = path[:slash]
                pkind = self.__node_kind(revnr, ppath)
                if pkind is None:
                    return ["Parent doesn't exist."]
                elif pkind != "dir":
                    return ["Parent is not a directory."]
            # copy-from must exist
            if node.has_copy_from():
                kind = self.__node_kind(node.get_copy_from_rev(),
                                        node.get_copy_from_path())
                if kind is None:
                    frompath = "  r%d %s" % (node.get_copy_from_rev(),
                                             node.get_copy_from_path())
                    return ["Copy-from path doesn't exist.", frompath]
            if node.get_kind() == "":
                # missing node kind, fix it!
                if kind is None:
                    return ["Unable to fix node."]
                node.set_kind(kind)
                print("Set kind '%s' in r%d for %s" %
                      (kind, revnr, node.get_path()))
            self.__add_node(revnr, node)
        elif action == "delete":
            # path must exist
            kind = self.__node_kind(revnr, path)
            if kind is None:
                return ["Node doesn't exist."]
            self.__delete_node(revnr, node)
        else:
            # path must exist
            kind = self.__node_kind(revnr, path)
            if kind is None:
                return ["Node doesn't exist."]
            # replace = delete & add; changes can be ignored
            if action == "replace" and node.has_copy_from():
                self.__delete_node(revnr, node)
                self.__add_node(revnr, node)
            if node.get_kind() == "":
                # missing node kind, fix it!
                if kind is None:
                    return ["Unable to fix node."]
                node.set_kind(kind)
                print("Set kind '%s' in r%d for %s" %
                      (kind, revnr, node.get_path()))
        return None

    def __node_kind(self, revnr, path):
        """
        Returns the kind of a node if it exists, else None.

        @type revnr: int
        @param revnr: Current revision number.
        @type path: string
        @param path: Path of a node.
        @rtype: string
        @return: "dir" for dirs, "file" for files or None.
        """
        if not self.__history.has_key(path):
            return None
        nodehist = self.__history[path]
        i = self.__rev_index(nodehist, revnr)
        if i is None:
            return None
        return nodehist[0]

    def __rev_index(self, nodehist, revnr):
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
        if revnr > nodehist[i][1] >= 0:
            return None
        return i

    def __add_node(self, revnr, node):
        """
        Adds a node to the history, recursively if it has copy-from path/rev.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Node to add.
        """
        path = node.get_path()
        if not self.__history.has_key(path):
            # create revision list for path
            self.__history[path] = [(node.get_kind())]
        # add revision range
        self.__history[path].append([revnr, -1])
        kind = self.__history[path][0]
        # continue only if it's a dir with copy-from
        if kind == "file" or not node.has_copy_from():
            return
        # recursive copy
        cfpath = node.get_copy_from_path() + "/"
        cfpathlen = len(cfpath)
        cfrev = node.get_copy_from_rev()
        path += "/"
        for cfnodepath in self.__history.keys()[:]:
            if cfnodepath.startswith(cfpath):
                cfnodehist = self.__history[cfnodepath]
                i = self.__rev_index(cfnodehist, cfrev)
                if i is not None:
                    npath = path + cfnodepath[cfpathlen:]
                    # add new path
                    if not self.__history.has_key(npath):
                        # create revision list for npath
                        self.__history[npath] = [cfnodehist[0]]
                    # add revision range
                    self.__history[npath].append([revnr, -1])

    def __delete_node(self, revnr, node):
        """
        Deletes a node from the history, recursively if it is a directory.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Node to add.
        """
        # set end revision
        path = node.get_path()
        self.__history[path][-1][1] = revnr - 1
        kind = self.__history[path][0]
        # continue only if it's a dir
        if kind == "file":
            return
        # recursive delete
        path += "/"
        for nodepath in self.__history.keys()[:]:
            if nodepath.startswith(path):
                nodehist = self.__history[nodepath]
                if nodehist[-1][1] == -1:
                    nodehist[-1][1] = revnr - 1


def svndump_cvs2svnfix_cmdline(appname, args):
    """
    Parses the commandline and executes the cvs2svnfix.

    Usage:

        >>> svndump_cvs2svnfix_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: int
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] inputfile outputfile" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    c2sfix = SvnDumpCvs2SvnFix()
    (options, args) = parser.parse_args(args)

    if len(args) != 2:
        print("Please specify exactly one input and one output file name.")
        return 1

    return c2sfix.execute(args[0], args[1])

# ===============================================================================
#
# Copyright (C) 2003 Martin Furter <mf@rola.ch>
# Copyright (C) 2013 Tom Taxon <tom@ourloudhouse.com>
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

from optparse import OptionParser
import os
import re
import sys

from svndump import __version, SvnDumpFile


class LargeFileLister:
    """
    A class for listing the n largest files in a repository
    """

    def __init__(self, max_files=20):
        """
        Creates a LargeFileLister class.

        @type max_files: int
        @param max_files: The number of largest files to print
        """
        self.__max_files = max_files
        self.__large_files = []
        self.__smallest_file = 0

    def process_node(self, dump, node):
        if node.get_kind() == "file":
            size = node.get_text_length()
            if size > self.__smallest_file:
                self.__large_files.append((size, dump.get_rev_nr(), node));
                self.__large_files.sort(key=lambda tup: tup[0])
                if len(self.__large_files) > self.__max_files:
                    self.__large_files.pop(0)
                if len(self.__large_files) == self.__max_files:
                    self.__smallest_file = self.__large_files[0][0]

    def done(self, dump):
        self.__large_files.reverse();
        max_size = self.__large_files[0][0]
        max_rev = 0
        for tup in self.__large_files:
            max_rev = max(max_rev, tup[1])
        size_len = max(4, len(str(max_size)))
        rev_len = max(8, len(str(max_rev)))
        print(" %-*s %-*s Path" % (size_len, "Size", rev_len, "Revision"))
        for tup in self.__large_files:
            print(" %*d %*d %s" % (size_len, tup[0], rev_len, tup[1], tup[2].get_path()))


def list_files(srcfile, lister):
    """
    List the largest files from the dump file.

    @type srcfile: string
    @param srcfile: Source filename.
    @type dstfile: string
    @param dstfile: Destination filename.
    """

    # SvnDumpFile classes for reading/writing dumps
    srcdmp = SvnDumpFile()
    # open source file
    srcdmp.open(srcfile)
    hasrev = srcdmp.read_next_rev()
    if hasrev:
        while hasrev:
            if srcdmp.get_node_count() > 0:
                for node in srcdmp.get_nodes_iter():
                    lister.process_node(srcdmp, node)
            hasrev = srcdmp.read_next_rev()
    else:
        print("no revisions in the source dump '%s' ???" % srcfile)
    lister.done(srcdmp)

    # cleanup
    srcdmp.close()


def svndump_list_large_files(appname, args):
    """
    Parses the commandline and lists the large files based on the options.

    Usage:

        >>> svndump_list_arge_files( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s source" % appname
    usage += "\n\nThis command lists the largest files in the dump file"
    parser = OptionParser(usage=usage, version="%prog " + __version)

    parser.add_option("-n", "--num", action="store", type="int", dest="max_files", default=20,
                      help="the maximum number of files to show (default=20).")

    (options, args) = parser.parse_args(args)

    if len(args) != 1:
        print("Specify a dump file from which to list the large files")
        return 1

    list_files(args[0], LargeFileLister(options.max_files))
    return 0

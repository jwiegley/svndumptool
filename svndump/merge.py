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

import sys
import re
from optparse import OptionParser

from svndump import __version
from file import SvnDumpFile
from node import SvnDumpNode

__doc__ = """Clases and functions for merging dump files."""


class SvnDumpMerge:
    """
    A class for merging svn dump files.
    """

    # handle copyfrom-rev !!!

    def __init__(self):
        """
        Initialize.
        """

        # output file name
        self.__out_file = ""
        # date for revision 0
        self.__out_r0_date = "9999-99-99T99:99:99.999999Z"
        # list additional directories
        self.__out_dirs = []
        # log message for directory creating revision
        self.__out_message = ""
        # author for the additional revision
        self.__out_author = "svndumpmerge"

        # variables used for input dump files
        # file names
        self.__in_files = []
        # path renames [ [ ( from, to ), ... ], ... ]
        self.__in_renames = []
        # path regex substitutions [ [ ( search, replace ), ... ], ... ]
        self.__in_regex_subs = []
        # mkdir excludes [ {}, ... ]
        self.__in_excludes = []
        # revision number mappings [ {}, ... ]
        self.__in_rev_nr_maps = []
        # dump files (class SvnDumpFile)
        self.__in_dumps = []
        # revision dates of the dumps
        self.__in_rev_dates = []

    def set_output_file(self, filename, startRev=0):
        """
        Sets the output file name and optional start revision.

        @type filename: string
        @param filename: Name of the output dump file.
        @type startRev: integer
        @param startRev: Start revision number, default is 0.
        """

        self.__out_file = filename
        self.outStartRev = startRev

    def add_input_file(self, filename):
        """
        Adds an input file and returns it's index.

        @type filename: string
        @param filename: Name of a input dump file.
        @rtype: integer
        @return: Index of the input file.
        """

        index = len(self.__in_files)
        self.__in_files = self.__in_files + [filename]
        self.__in_renames = self.__in_renames + [[]]
        self.__in_regex_subs = self.__in_regex_subs + [[]]
        self.__in_excludes = self.__in_excludes + [{}]
        self.__in_rev_nr_maps = self.__in_rev_nr_maps + [{}]
        return index

    def add_rename(self, index, prefixFrom, prefixTo):
        """
        Adds a path prefix reanme.

        @type index: integer
        @param index: Index of the dump file.
        @type prefixFrom: string
        @param prefixFrom: From-path prefix (directory).
        @type prefixTo: string
        @param prefixTo: To-path prefix (directory).
        """

        # make sure that prefixFrom starts and ends with a /
        if prefixFrom[0:1] == "/":
            prefixFrom = prefixFrom[1:]
        if prefixFrom[len(prefixFrom) - 1:] != "/":
            prefixFrom = prefixFrom + "/"
        # make sure that prefixTo starts and ends with a /
        if prefixTo[0:1] == "/":
            prefixTo = prefixTo[1:]
        if prefixTo[len(prefixTo) - 1:] != "/":
            prefixTo = prefixTo + "/"
        # add the rename
        self.__in_renames[index] = self.__in_renames[index] + \
                                   [(prefixFrom, prefixTo)]

    def add_regex_sub(self, index, reSearch, reReplace):
        """
        Adds a path prefix rename.

        @type index: integer
        @param index: Index of the dump file.
        @type reSearch: string
        @param reSearch: Search regular expression.
        @type reReplace: string
        @param reReplace: Replace regular expression.
        """

        # compile regex object
        reSearch = re.compile(reSearch)
        # add the rename
        self.__in_regex_subs[index] = self.__in_regex_subs[index] + \
                                      [(reSearch, reReplace)]

    def add_mkdir_exclude(self, index, dirName):
        """
        Adds a mkdir exclude.

        @type index: integer
        @param index: Index of the dump file.
        @type dirName: string
        @param dirName: Name of the directory.
        """

        # add the mkdir exclude
        self.__in_excludes[index][dirName] = None

    def add_directory(self, dirName):
        """
        Adds an additional directory ('mkdir').

        @type dirName: string
        @param dirName: Name of the directory.
        """
        if dirName[0:1] == "/":
            dirName = dirName[1:]
        if dirName[-1:] == "/":
            dirName = dirName[:-1]
        self.__out_dirs = self.__out_dirs + [dirName]

    def set_log_message(self, msg):
        """
        Set log message for additional dirs revision.

        @type msg: string
        @param msg: Log message.
        """
        self.__out_message = msg

    def merge(self):
        """
        Executes the merge.
        """

        if len(self.__in_files) == 0:
            print("merge: no input files specified")
            return
        if len(self.__out_file) == 0:
            print("merge: no output file specified")
            return

        # open input dump files
        for inFile in self.__in_files:
            inDump = SvnDumpFile()
            inDump.open(inFile)
            inDump.read_next_rev()
            self.__in_dumps = self.__in_dumps + [inDump]
            if inDump.get_rev_date_str() < self.__out_r0_date:
                self.__out_r0_date = inDump.get_rev_date_str()

        # remove empty dumps
        dumpCount = self.__remove_empty_dumps()
        if dumpCount == 0:
            return

        # open output file
        self.outDump = SvnDumpFile()
        if self.outStartRev == 0:
            self.outDump.create_with_rev_0(self.__out_file,
                                           self.__in_dumps[0].get_uuid(), self.__out_r0_date)
        else:
            self.outDump.create_with_rev_n(self.__out_file,
                                           self.__in_dumps[0].get_uuid(), self.outStartRev)

        # skip revision 0 of all dumps
        for inDump in self.__in_dumps:
            if inDump.get_rev_nr() == 0:
                # +++ what about r0 revprops?
                inDump.read_next_rev()

        # remove empty dumps
        dumpCount = self.__remove_empty_dumps()
        if dumpCount == 0:
            self.outDump.close()
            return

        # get revision dates
        oldest = None
        oldestStr = ""
        for index in range(len(self.__in_dumps)):
            revDat = self.__in_dumps[index].get_rev_date()
            self.__in_rev_dates.append(revDat)
            if oldest is None or revDat < oldest:
                oldest = revDat
                oldestStr = self.__in_dumps[index].get_rev_date_str()

        # add additional directories
        if len(self.__out_dirs) > 0:
            self.outDump.add_rev({"svn:log": self.__out_message,
                                  "svn:author": self.__out_author,
                                  "svn:date": oldestStr})
            for dirName in self.__out_dirs:
                node = SvnDumpNode(dirName, "add", "dir")
                self.outDump.add_node(node)

        # loop over all revisions
        while dumpCount > 0:
            # find index of the oldest revision
            oldestIndex = 0
            for index in range(1, dumpCount):
                if self.__in_rev_dates[index] < self.__in_rev_dates[oldestIndex]:
                    oldestIndex = index
            # copy revision
            self.__copy_revision(oldestIndex)
            print("Revision: %-8d from r%-8d %s" % (self.outDump.get_rev_nr(),
                                                    self.__in_dumps[oldestIndex].get_rev_nr(),
                                                    self.__in_files[oldestIndex]))
            # read next revision
            srcDump = self.__in_dumps[oldestIndex]
            if srcDump.read_next_rev():
                self.__in_rev_dates[oldestIndex] = srcDump.get_rev_date()
            else:
                dumpCount = self.__remove_empty_dumps()

        # close output
        print("created %d revisions" % self.outDump.get_rev_nr())
        self.outDump.close()

    def __copy_revision(self, dumpIndex):
        """
        Copies a revision from inDump[dumpIndex] to outDump.

        @type dumpIndex: integer
        @param dumpIndex: Index of the input dump file.
        """

        srcDump = self.__in_dumps[dumpIndex]

        # add revision and revprops
        self.outDump.add_rev(srcDump.get_rev_props())

        # add nodes
        index = 0
        nodeCount = srcDump.get_node_count()
        while index < nodeCount:
            node = srcDump.get_node(index)
            newNode = self.__change_node(dumpIndex, node)
            if newNode is not None:
                self.outDump.add_node(newNode)
            index = index + 1

        # add revision info
        self.__in_rev_nr_maps[dumpIndex][srcDump.get_rev_nr()] = \
            self.outDump.get_rev_nr()

    def __change_node(self, dumpIndex, node):
        """
        Creates a new node if the path changed, else returns the old node.

        @type dumpIndex: integer
        @param dumpIndex: Index of the input dump file.
        @type node: SvnDumpNode
        @param node: A node.
        """

        path = node.get_path()
        # mkdir exclude check
        if node.get_kind() == "dir" and node.get_action() == "add":
            if path in self.__in_excludes[dumpIndex]:
                return None
        fromPath = ""
        fromRev = 0
        if node.has_copy_from():
            fromPath = node.get_copy_from_path()
            fromRev = node.get_copy_from_rev()
        change = 0
        newPath = self.__rename_path(path, dumpIndex)
        newFromPath = fromPath
        newFromRev = fromRev
        if path != newPath:
            change = 1
        if fromRev > 0:
            newFromPath = self.__rename_path(fromPath, dumpIndex)
            if fromPath != newFromPath:
                change = 1
            newFromRev = self.__in_rev_nr_maps[dumpIndex][fromRev]
            if fromRev != newFromRev:
                change = 1

        newMergeInfo = ""
        if node.has_properties():
            properties = node.get_properties()
            if properties.has_key('svn:mergeinfo'):
                mergeInfo = properties['svn:mergeinfo']
                for line in mergeInfo.split('\n'):
                    m = re.match('^(.*):(.*)', line)
                    if m is not None:
                        mergePath = m.group(1)
                        revPart = m.group(2)
                        newMergePath = self.__rename_path(mergePath, dumpIndex)
                        if not newMergePath.startswith("/"):
                            newMergePath = "/" + newMergePath
                        if len(newMergeInfo) != 0:
                            newMergeInfo = newMergeInfo + "\n"
                        newMergeInfo = newMergeInfo + newMergePath + ":"
                        revSep = ""
                        for rm in re.finditer('(\d+)(?:-(\d+))?,?', revPart):
                            mergeFrom = int(rm.group(1))
                            newMergeFrom = self.__in_rev_nr_maps[dumpIndex][mergeFrom]
                            newMergeInfo = newMergeInfo + revSep + str(newMergeFrom)
                            revSep = ","
                            if rm.group(2) is not None:
                                mergeTo = int(rm.group(2))
                                newMergeTo = self.__in_rev_nr_maps[dumpIndex][mergeTo]
                                newMergeInfo = newMergeInfo + "-" + str(newMergeTo)

                if mergeInfo != newMergeInfo:
                    change = 1

        if not change:
            # no change needed
            return node

        # do the rename
        newNode = SvnDumpNode(newPath, node.get_action(), node.get_kind())
        if node.has_copy_from():
            newNode.set_copy_from(newFromPath, newFromRev)
        if node.has_properties():
            newNode.set_properties(node.get_properties())
            if len(newMergeInfo) > 0:
                newNode.set_property('svn:mergeinfo', newMergeInfo)
        if node.has_text():
            newNode.set_text_node(node)
        return newNode

    def __rename_path(self, path, dumpIndex):
        """
        Applies the renames to the path and returns the new path.

        @type path: string
        @param path: A path.
        @type renames: list( ( string, string ) )
        @param renames: List of rename tuples.
        @rtype: string
        @return Renamed path.
        """

        # ensure that path does not have a leading slash
        if len(path) > 1 and path[0:1] == "/":
            path = path[1:]
        sPath = path + "/"
        for sPfx, dPfx in self.__in_renames[dumpIndex]:
            sLen = len(sPfx)
            if sPfx == "/":
                return dPfx + path
            elif sPath[:sLen] == sPfx:
                if len(path) <= len(sPfx):
                    # it's the full path
                    return dPfx[0:len(dPfx) - 1]
                else:
                    # there's a suffix
                    return dPfx + path[sLen:]
        for reSearch, sReplace in self.__in_regex_subs[dumpIndex]:
            path = reSearch.sub(sReplace, path, count=1)
        return path

    def __remove_empty_dumps(self):
        """
        Removes dump files which reached EOF and returns the count of dumps.

        @rtype: integer
        @return: Count of remaining input dump files.
        """

        index = 0
        while index < len(self.__in_dumps):
            inDump = self.__in_dumps[index]
            if inDump.has_revision():
                index = index + 1
            else:
                inDump.close()
                eidx = index + 1
                self.__in_files[index:eidx] = []
                self.__in_renames[index:eidx] = []
                self.__in_regex_subs[index:eidx] = []
                self.__in_excludes[index:eidx] = []
                self.__in_rev_nr_maps[index:eidx] = []
                self.__in_dumps[index:eidx] = []
                self.__in_rev_dates[index:eidx] = []
        return index


def __svndump_merge_opt_i(option, opt, value, parser, *args):
    """
    Option parser callback for input file '-i <filename>'.
    """
    merge = args[0]
    vars = args[1]
    vars["fileindex"] = merge.add_input_file(value)


def __svndump_merge_opt_r(option, opt, value, parser, *args):
    """
    Option parser callback for rename '-r from to'.
    """
    merge = args[0]
    vars = args[1]
    merge.add_rename(vars["fileIndex"], value[0], value[1])


def __svndump_merge_opt_s(option, opt, value, parser, *args):
    """
    Option parser callback for regex substitution '-s search replace'.
    """
    merge = args[0]
    vars = args[1]
    merge.add_regex_sub(vars["fileIndex"], value[0], value[1])


def __svndump_merge_opt_x(option, opt, value, parser, *args):
    """
    Option parser callback for mkdir exclude '-x dir'.
    """
    merge = args[0]
    vars = args[1]
    merge.add_mkdir_exclude(vars["fileIndex"], value)


def __svndump_merge_opt_o(option, opt, value, parser, *args):
    """
    Option parser callback for output file '-o filename'.
    """
    merge = args[0]
    vars = args[1]
    merge.set_output_file(value)
    vars["outFileSet"] = 1


def __svndump_merge_opt_d(option, opt, value, parser, *args):
    """
    Option parser callback for mkdir '-d dirname'.
    """
    merge = args[0]
    vars = args[1]
    merge.add_directory(value)


def __svndump_merge_opt_m(option, opt, value, parser, *args):
    """
    Option parser callback for message '-m message'.
    """
    merge = args[0]
    vars = args[1]
    merge.set_log_message(value)
    vars["logMsgSet"] = 1


def __svndump_merge_example(option, opt, value, parser, *args):
    """
    Option parser callback for example output.
    
    Prints a little usage example.
    """

    print("")
    print(args[2] + " \\")
    print("  -i proj1.dmp \\")
    print("  -r trunk trunk/proj1 -r tags tags/proj1 -r branches branches/proj1 \\")
    print("  -i proj2.dmp \\")
    print("  -r trunk trunk/proj2 -r tags tags/proj2 -r branches branches/proj2 \\")
    print("  -o merged.dmp \\")
    print("  -d trunk -d tags -d branches")
    print("")
    print("This commandline merges the svn dump files proj1.dmp and proj2.dmp")
    print("into one big dump file named merged.dmp.")
    print("The contents of trunk of proj1 will be moved to trunk/proj1 and ")
    print("tags into tags/proj1 and branches into branches/proj1. The same")
    print("renames are done with trunk tags and branches of proj2.")
    print("The directories trunk tags and branches would not exist in the new")
    print("dump file if they weren't created with the -d options.")
    print("")
    sys.exit(0)


def svndump_merge_cmdline(appname, args):
    """
    Parses the commandline and executes the merge.

    Usage:

        >>> svndump_merge_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options]" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    merge = SvnDumpMerge()
    vars = {}
    vars["fileIndex"] = -1
    vars["outFileSet"] = 0
    vars["logMsgSet"] = 0
    cbargs = (merge, vars, appname)
    parser.add_option("-i", "--input-file",
                      action="callback", callback=__svndump_merge_opt_i,
                      callback_args=cbargs,
                      dest="infile",
                      nargs=1, type="string",
                      help="adds an input dump filename.")
    parser.add_option("-r", "--rename",
                      action="callback", callback=__svndump_merge_opt_r,
                      callback_args=cbargs,
                      dest=" from to",
                      nargs=2, type="string",
                      help="adds a rename to the previously added file.")
    parser.add_option("-s", "--regex-substitute",
                      action="callback", callback=__svndump_merge_opt_s,
                      callback_args=cbargs,
                      dest=" ""search"" ""replace""",
                      nargs=2, type="string",
                      help="performs regular expression search and replace")
    parser.add_option("-x", "--mkdir-exclude",
                      action="callback", callback=__svndump_merge_opt_x,
                      callback_args=cbargs,
                      dest="dir",
                      nargs=1, type="string",
                      help="exclude mkdir from the previously added file.")
    parser.add_option("-o", "--output-file",
                      action="callback", callback=__svndump_merge_opt_o,
                      callback_args=cbargs,
                      nargs=1, type="string",
                      dest="outfile",
                      help="sets the output filename.")
    parser.add_option("-d", "--mkdir",
                      action="callback", callback=__svndump_merge_opt_d,
                      callback_args=cbargs,
                      nargs=1, type="string",
                      dest="dir",
                      help="create an additional directory.")
    parser.add_option("-m", "--message",
                      action="callback", callback=__svndump_merge_opt_m,
                      callback_args=cbargs,
                      nargs=1, type="string",
                      dest="msg",
                      help="logmessage for the directory creating revision.")
    parser.add_option("--example",
                      action="callback", callback=__svndump_merge_example,
                      callback_args=cbargs,
                      nargs=0,
                      dest="",
                      help="show a little usage example.")
    (options, args) = parser.parse_args(args)

    merge.merge()
    return 0

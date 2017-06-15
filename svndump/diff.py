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

from optparse import OptionParser

from svndump import __version
from file import SvnDumpFile
from common import sdt_md5

__doc__ = """Diff functions and classes."""


class SvnDumpDiffCallback:
    """
    Callback class for SvnDumpDiff.

    The methods of this class get called by SvnDumpDiff and output the diff
    results.
    """

    def __init__(self, verbosity):
        """
        Initialize.

        @type verbosity: integer
        @param verbosity: Verbosity level, 0=quiet, 1=normal, 2=verbose.
        """
        self.verbosity = verbosity
        self.diffs = False
        self.filename1 = ""
        self.filename2 = ""
        self.revnr1 = -1
        self.revnr2 = -1
        self.action = ""
        self.kind = ""
        self.path = ""
        self.index1 = -1
        self.index2 = -1
        self.__ignores = {}
        self.__ignore_revprop = {}
        self.__ignore_property = {}
        self.__rev_printed = False
        self.__node_printed = False
        self.__prophdr_printed = False
        self.__summary = {}

    def add_ignore(self, type):
        """
        Adds an ignore.

        Valid types are:
         - types of rev_diff()
         - types of node_diff()
         - types of text_diff()
         - 'RevPropDiff'
         - 'RevPropMissing'
         - 'NodeMissing'
         - 'WrongMD5'
         - 'PropDiff'
         - 'PropMissing'

        @type type: string
        @param type: Diff type to ignore.
        """
        self.__ignores[type] = None

    def add_revprop_ignore(self, name):
        """
        Adds a revision property name to ignore.

        @type name: string
        @param name: Revprop name.
        """
        self.__ignore_revprop[name] = None

    def add_property_ignore(self, name):
        """
        Adds a property name to ignore.

        @type name: string
        @param name: A property name.
        """
        self.__ignore_property[name] = None

    def had_diffs(self):
        """
        Returns True when diffs were found which were not ignored.

        @rtype: bool
        @return: True when diffs were found.
        """
        return self.diffs

    def comparing(self, filename1, filename2):
        """
        Called at the beginning.

        @type filename1: string
        @param filename1: Name of the first file.
        @type filename2: string
        @param filename2: Name of the second file.
        """

        self.filename1 = filename1
        self.filename2 = filename2
        if self.verbosity > 0:
            print("Comparing")
            print("  dump1: '%s'" % self.filename1)
            print("  dump2: '%s'" % self.filename2)

    def compare_done(self):
        """
        Called at the end of the diff.
        """

        if self.verbosity > 0:
            if self.diffs:
                print("Done, found diffs.")
                if len(self.__summary) > 0:
                    print("  %-15s %7s %7s" % ("type", "total", "showed"))
                for type in self.__summary:
                    counts = self.__summary[type]
                    print("  %-15s %7d %7d" % (type, counts[0], counts[1]))
            else:
                print("Done.")

    def __summary_inc(self, type, show):
        """
        Increase the count for the given type in the summary.

        @type type: string
        @param type: A diff type.
        @type show: bool
        @param show: True if the type is not ignored.
        """
        s = 0
        if show:
            s = 1
        if self.__summary.has_key(type):
            counts = self.__summary[type]
            self.__summary[type] = [counts[0] + 1, counts[1] + s]
        else:
            self.__summary[type] = [1, s]

    def next_revision(self, revnr1, revnr2):
        """
        Called when starting to compare a new revision.

        @type revnr1: integer
        @param revnr1: Revision number of the first file.
        @type revnr2: integer
        @param revnr2: Revision number of the second file.
        """

        self.revnr1 = revnr1
        self.revnr2 = revnr2
        self.__rev_printed = False
        self.__prophdr_printed = False
        if self.verbosity > 1:
            self.__print_rev()

    def __print_rev(self):
        """
        Prints the revision numbers if not allready done.
        """
        if not self.__rev_printed:
            self.__rev_printed = True
            print("Revision: %d/%d" % (self.revnr1, self.revnr2))

    def next_node(self, node, index1, index2):
        """
        Called when starting to compare a new node.

        @type node: SvnDumpNode
        @param node: Next node beeing diffed.
        @type index1: integer
        @param index1: Index of the node in the first dump.
        @type index2: integer
        @param index2: Index of the node in the second dump.
        """

        self.action = node.get_action()
        self.kind = node.get_kind()
        self.path = node.get_path()
        self.index1 = index1
        self.index2 = index2
        self.__node_printed = False
        self.__prophdr_printed = False
        if self.verbosity > 1:
            self.__print_node()

    def __print_node(self):
        """
        Prints the node (action, kind, path) if not allready done.
        """
        self.__print_rev()
        if not self.__node_printed:
            self.__node_printed = True
            print("  Node: %s %s '%s' (%d/%d)" %
                  (self.action, self.kind, self.path, self.index1, self.index2))

    def rev_diff(self, type, value1, value2):
        """
        Called when a difference has been found.

        Called with the following types:
         - 'UUID'
         - 'RevNr'
         - 'RevDate'
         - 'RevDateStr'
         - 'NodeCount'

        @type type: string
        @param type: A diff type.
        @type value1: string
        @param value1: Value of first dump.
        @type value2: string
        @param value2: Value of second dump.
        """

        show = True
        if self.__ignores.has_key(type):
            show = False
        self.__summary_inc(type, show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_rev()
                print("+ Different %s:" % type)
                print("    dump1: '%s'" % value1)
                print("    dump2: '%s'" % value2)

    def revprop_diff(self, name, value1, value2):
        """
        Called when a revprop is in one dump only.

        @type name: string
        @param name: Name of the revision property.
        @type value1: string
        @param value1: Value of first dump.
        @type value2: string
        @param value2: Value of second dump.
        """

        show = True
        if self.__ignores.has_key("RevPropDiff"):
            show = False
        if self.__ignore_revprop.has_key(name):
            show = False
        self.__summary_inc("RevPropDiff", show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_rev()
                if not self.__prophdr_printed:
                    self.__prophdr_printed = True
                    print("  Properties:")
                print("    Property '%s'" % name)
                print("      dump1: '%s'" % value1)
                print("      dump2: '%s'" % value2)

    def revprop_missing(self, dumpnr, name, value):
        """
        Called when a revprop is in one dump only.

        @type dumpnr: integer
        @param dumpnr: Number of the dump file, 1 = first, 2 = second.
        @type name: string
        @param name: Name of the revision property.
        @type value: string
        @param value: Value of first dump.
        """

        show = True
        if self.__ignores.has_key("RevPropMissing"):
            show = False
        if self.__ignore_revprop.has_key(name):
            show = False
        self.__summary_inc("RevPropMissing", show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_rev()
                if not self.__prophdr_printed:
                    self.__prophdr_printed = True
                    print("  Properties:")
                print("    Property '%s' missing in dump%d" % (name, dumpnr))
                print("      dump%d: '%s'" % (3 - dumpnr, value))

    def node_diff(self, type, value1, value2):
        """
        Called when a difference has been found.

        Called with the following types:
         - 'Path'
         - 'Action'
         - 'Kind'
         - 'CopyFromPath'
         - 'CopyFromRev'
         - 'HasText'
         - 'TextLen'
         - 'TextMD5'

        @type type: string
        @param type: A diff type.
        @type value1: string
        @param value1: Value of first dump.
        @type value2: string
        @param value2: Value of second dump.
        """

        show = True
        if self.__ignores.has_key(type):
            show = False
        self.__summary_inc(type, show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_rev()
                self.__print_node()
                print("+   Different %s:" % type)
                print("      dump1: '%s'" % value1)
                print("      dump2: '%s'" % value2)

    def node_missing(self, dumpnr, node):
        """
        Called when a node exists in one dump only.

        @type dumpnr: integer
        @param dumpnr: Number of the dump file, 1 = first, 2 = second.
        @type node: SvnDumpNode
        @param node: Node of the other dump.
        """

        show = True
        if self.__ignores.has_key("NodeMissing"):
            show = False
        self.__summary_inc("NodeMissing", show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_rev()
                print("+ Node missing in dump%d:" % dumpnr)
                print("    Node: %s %s '%s'" %
                      (node.get_action(), node.get_kind(), node.get_path()))

    def wrong_md5(self, dumpnr, should, calc):
        """
        Called when text has worng MD5.

        @type dumpnr: integer
        @param dumpnr: Number of the dump file, 1 = first, 2 = second.
        @type should: string
        @param should: MD5 sum in the dump file.
        @type calc: string
        @param calc: Calculated MD5 sum.
        """

        show = True
        if self.__ignores.has_key("WrongMD5"):
            show = False
        self.__summary_inc("WrongMD5", show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_node()
                print("+   Wrong MD5 in dump%d:" % dumpnr)
                print("      should be:   '%s'" % should)
                print("      calculated:  '%s'" % calc)

    def text_diff(self, type):
        """
        Called when text differs.

        Called with the following types:
         - 'EOL'
         - 'Text'

        @type type: string
        @param type: A diff type.
        """

        show = True
        if self.__ignores.has_key(type):
            show = False
        self.__summary_inc(type, show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_node()
                print("+   Text differs (type '%s')" % type)

    def prop_diff(self, name, value1, value2):
        """
        Called when a revprop is in one dump only.

        @type name: string
        @param name: Name of the property.
        @type value1: string
        @param value1: Value of first dump.
        @type value2: string
        @param value2: Value of second dump.
        """

        show = True
        if self.__ignores.has_key("PropDiff"):
            show = False
        if self.__ignore_property.has_key(name):
            show = False
        self.__summary_inc("PropDiff", show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_node()
                if not self.__prophdr_printed:
                    self.__prophdr_printed = True
                    print("    Properties:")
                print("+     Property '%s'" % name)
                print("        dump1: '%s'" % value1)
                print("        dump2: '%s'" % value2)

    def prop_missing(self, dumpnr, name, value):
        """
        Called when a revprop is in one dump only.

        @type dumpnr: integer
        @param dumpnr: Number of the dump file, 1 = first, 2 = second.
        @type name: string
        @param name: Name of the property.
        @type value: string
        @param value: Value of first dump.
        """

        show = True
        if self.__ignores.has_key("PropMissing"):
            show = False
        if self.__ignore_property.has_key(name):
            show = False
        self.__summary_inc("PropMissing", show)
        if show:
            self.diffs = True
            if self.verbosity > 0:
                self.__print_node()
                if not self.__prophdr_printed:
                    self.__prophdr_printed = True
                    print("    Properties:")
                print("+     Property '%s' missing in dump%d" % (name, dumpnr))
                print("        dump%d: '%s'" % (3 - dumpnr, value))


class SvnDumpDiff:
    """
    A class for comparing svn dump files.
    """

    def __init__(self, filename1, filename2):
        """
        Initialize.

        @type filename1: string
        @param filename1: First dump file name.
        @type filename2: string
        @param filename2: Second dump file name.
        """

        self.__filename1 = filename1
        self.__filename2 = filename2
        self.__check_eol = False

    def set_check_eol(self, check=True):
        """
        Set or clear the check-eol flag.

        @type check: bool
        @param check: True for doing EOL check.
        """
        self.__check_eol = check

    def execute(self, callback):
        """
        Execute the diff.

        @type callback: SvnDumpDiffCallback
        @param callback: Callback object for diffs found.
        """

        # diff started
        callback.comparing(self.__filename1, self.__filename2)

        # open files
        dump1 = SvnDumpFile()
        dump2 = SvnDumpFile()
        dump1.open(self.__filename1)
        dump2.open(self.__filename2)

        # compare uuid
        if dump1.get_uuid() != dump2.get_uuid():
            callback.rev_diff("UUID", dump1.get_uuid(), dump2.get_uuid())

        hasrev1 = dump1.read_next_rev()
        hasrev2 = dump2.read_next_rev()

        while hasrev1 and hasrev2:
            # compare rev numbers
            if dump1.get_rev_nr() != dump2.get_rev_nr():
                callback.rev_diff("RevNr", dump1.get_rev_nr(), dump2.get_rev_nr())
                # error has been reported so set both flags to false
                hasrev1 = False
                hasrev2 = False
                break

            # next revision...
            callback.next_revision(dump1.get_rev_nr(), dump2.get_rev_nr())

            # compare rev date
            if dump1.get_rev_date() != dump2.get_rev_date():
                callback.rev_diff("RevDate",
                                  str(dump1.get_rev_date()),
                                  str(dump2.get_rev_date()))
            if dump1.get_rev_date_str() != dump2.get_rev_date_str():
                callback.rev_diff("RevDateStr", dump1.get_rev_date_str(), dump2.get_rev_date_str())

            # compare rev author
            # compare rev log
            # compare rev props
            self.__compare_properties(True, dump1.get_rev_props(),
                                      dump2.get_rev_props(), callback)
            # compare nodes
            self.__compare_nodes(dump1, dump2, callback)

            # read next revision
            hasrev1 = dump1.read_next_rev()
            hasrev2 = dump2.read_next_rev()

        if hasrev1 or hasrev2:
            print("random error ;-) (different rev nr or EOF of one file)")

        # done.
        callback.compare_done()

    def __compare_nodes(self, dump1, dump2, callback):
        """
        Compares the nodes of the current revision of two dump files.

        @type dump1: SvnDumpFile
        @param dump1: First dump file.
        @type dump2: SvnDumpFile
        @param dump2: Second dump file.
        @type callback: SvnDumpDiffCallback
        @param callback: Callback object for diffs found.
        """

        n1 = dump1.get_node_count()
        n2 = dump2.get_node_count()

        if n1 != n2:
            callback.rev_diff("NodeCount", n1, n2)

        list2 = {}
        for i in range(0, n2):
            node = dump2.get_node(i)
            list2[node.get_action() + ":" + node.get_path()] = i
        indexlist = []
        for i in range(0, n1):
            node = dump1.get_node(i)
            nodekey = node.get_action() + ":" + node.get_path()
            if list2.has_key(nodekey):
                i2 = list2[nodekey]
                del list2[nodekey]
            else:
                i2 = -1
            indexlist.append([i, i2])
        for nodekey, i2 in list2.items():
            indexlist.append([-1, i2])

        for indices in indexlist:
            if indices[0] == -1:
                node2 = dump2.get_node(indices[1])
                callback.node_missing(1, node2)
            elif indices[1] == -1:
                node1 = dump1.get_node(indices[0])
                callback.node_missing(2, node1)
            else:
                node1 = dump1.get_node(indices[0])
                node2 = dump2.get_node(indices[1])
                callback.next_node(node1, indices[0], indices[1])
                self.__compare_node(node1, node2, callback)

    def __compare_node(self, node1, node2, callback):
        """
        Compare two nodes.

        @type node1: SvnDumpNode
        @param node1: First dump node.
        @type node2: SvnDumpNode
        @param node2: Second dump node.
        @type callback: SvnDumpDiffCallback
        @param callback: Callback object for diffs found.
        """

        # compare path
        if node1.get_path() != node2.get_path():
            callback.node_diff("Path", node1.get_path(), node2.get_path())
            return
        # compare action
        if node1.get_action() != node2.get_action():
            callback.node_diff("Action", node1.get_action(), node2.get_action())
            return
        # compare kind
        if node1.get_kind() != node2.get_kind():
            callback.node_diff("Kind", node1.get_kind(), node2.get_kind())
            return
        # compare copy-from-path
        if node1.get_copy_from_path() != node2.get_copy_from_path():
            callback.node_diff("CopyFromPath", node1.get_copy_from_path(), node2.get_copy_from_path())
            return
        # compare copy-from-rev
        if node1.get_copy_from_rev() != node2.get_copy_from_rev():
            callback.node_diff("CopyFromRev", node1.get_copy_from_rev(), node2.get_copy_from_rev())
            return
        # compare props
        self.__compare_properties(False, node1.get_properties(),
                                  node2.get_properties(), callback)
        # compare text
        if node1.has_text() != node2.has_text():
            callback.node_diff("HasText", node1.has_text(), node2.has_text())
            return
        if not node1.has_text():
            # no text to compare
            return
        if node1.get_text_length() != node2.get_text_length():
            callback.node_diff("TextLen", node1.get_text_length(), node2.get_text_length())
        if node1.get_text_md5() != node2.get_text_md5():
            callback.node_diff("TextMD5", node1.get_text_md5(), node2.get_text_md5())
        md1 = sdt_md5()
        md2 = sdt_md5()
        handle1 = node1.text_open()
        handle2 = node2.text_open()
        str1 = node1.text_read(handle1)
        str2 = node2.text_read(handle2)
        n1 = len(str1)
        n2 = len(str2)
        cmpstr1 = ""
        cmpstr2 = ""
        defreadcount = 16384
        readcount1 = defreadcount
        readcount2 = defreadcount
        # how to compare: 0=normal, 1=eol-check, 2=had a diff
        cmpmode = 0
        forceloop = False
        while n1 > 0 or n2 > 0 or forceloop:
            forceloop = False
            if n1 > 0:
                md1.update(str1)
                cmpstr1 += str1
            if n2 > 0:
                md2.update(str2)
                cmpstr2 += str2
            if cmpstr1 == cmpstr2:
                # save last char for possible eol compare
                cmpstr1 = cmpstr1[-1:]
                cmpstr2 = cmpstr2[-1:]
            elif cmpmode == 0:
                # binary compare had a diff
                if self.__check_eol:
                    # start doing eol checks
                    cmpmode = 1
                    forceloop = True
                else:
                    # no eol check so files differ
                    cmpmode = 2
                    cmpstr1 = ""
                    cmpstr2 = ""
            elif cmpmode == 1:
                # eol-diff or real diff?
                cn1 = len(cmpstr1) - 1
                cn2 = len(cmpstr2) - 1
                i1 = 0
                i2 = 0
                while i1 < cn1 and i2 < cn2:
                    if ((cmpstr1[i1] == '\n' or cmpstr1[i1] == '\r') and
                            (cmpstr2[i2] == '\n' or cmpstr2[i2] == '\r')):
                        # check for LF/CRLF/CR sequence
                        if cmpstr1[i1] == '\r' and cmpstr1[i1 + 1] == '\n':
                            i1 += 1
                        if cmpstr2[i2] == '\r' and cmpstr2[i2 + 1] == '\n':
                            i2 += 1
                    elif cmpstr1[i1] != cmpstr2[i2]:
                        # found a diff
                        cmpmode = 2
                        cmpstr1 = ""
                        cmpstr2 = ""
                        break
                    # next...
                    i1 += 1
                    i2 += 1
                # remove processed data from cmpstr and adjust readcount
                cmpstr1 = cmpstr1[i1:]
                cmpstr2 = cmpstr2[i2:]
                cn1 = len(cmpstr1)
                cn2 = len(cmpstr2)
                if cmpmode == 1:
                    # adjust readcount
                    if cn1 > cn2:
                        readcount1 = defreadcount + cn1 - cn2
                        readcount2 = defreadcount
                    else:
                        readcount1 = defreadcount
                        readcount2 = defreadcount + cn2 - cn1
                    # if n1 > 0 and n2 > 0 and cn1 > 0 and cn2 > 0:
                    if n1 > 0 or n2 > 0:
                        forceloop = True
                else:
                    # reset readcount
                    readcount1 = defreadcount
                    readcount2 = defreadcount
            else:
                # cmpmode = 2: just clear compare strings
                cmpstr1 = ""
                cmpstr2 = ""
            # read more text...
            if n1 > 0:
                str1 = node1.text_read(handle1, readcount1)
                n1 = len(str1)
            if n2 > 0:
                str2 = node2.text_read(handle2, readcount2)
                n2 = len(str2)
        if cmpmode == 1:
            # compare trailing data (can only occur in eol-check mode)
            cmpstr1 = cmpstr1.replace("\r\n", "\n").replace("\r", "\n")
            cmpstr2 = cmpstr2.replace("\r\n", "\n").replace("\r", "\n")
            if cmpstr1 != cmpstr2:
                cmpmode = 2
        mdstr1 = md1.hexdigest()
        mdstr2 = md2.hexdigest()
        if node1.get_text_md5() != mdstr1:
            callback.wrong_md5(1, node1.get_text_md5(), mdstr1)
        if node2.get_text_md5() != mdstr2:
            callback.wrong_md5(2, node2.get_text_md5(), mdstr2)
        if cmpmode == 1:
            callback.text_diff("EOL")
        elif cmpmode == 2:
            callback.text_diff("Text")

    def __compare_properties(self, revprops, props1, props2, callback):
        """
        Compare properties.

        @type revprops: bool
        @param revprops: True when comparing revision properties.
        @type props1: dict( string -> string )
        @param props1: Dict containing the properties of the first dump.
        @type props2: dict( string -> string )
        @param props2: Dict containing the properties of the second dump.
        @type callback: SvnDumpDiffCallback
        @param callback: Callback object for diffs found.
        """

        if props1 == None and props2 == None:
            return
        if props1 == None:
            props1 = {}
        if props2 == None:
            props2 = {}
        common = []
        for name in props1:
            if props2.has_key(name):
                common.append(name)
            elif revprops:
                callback.revprop_missing(2, name, props1[name])
            else:
                callback.prop_missing(2, name, props1[name])
        for name in props2:
            if props1.has_key(name):
                pass
            elif revprops:
                callback.revprop_missing(1, name, props2[name])
            else:
                callback.prop_missing(1, name, props2[name])
        for name in common:
            if props1[name] != props2[name]:
                if revprops:
                    callback.revprop_diff(name, props1[name], props2[name])
                else:
                    callback.prop_diff(name, props1[name], props2[name])


def svndump_diff_cmdline(appname, args):
    """
    Parses the commandline and executes the diff.

    Usage:

        >>> svndump_diff_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dump1 dump2" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    parser.add_option("-e", "--check-eol",
                      action="store_const", dest="eol", const=1, default=0,
                      help="check for EOL differences")
    parser.add_option("-q", "--quiet",
                      action="store_const", dest="verbose", const=0, default=1,
                      help="quiet output")
    parser.add_option("-v", "--verbose",
                      action="store_const", dest="verbose", const=2,
                      help="verbose output")
    ignores = ["UUID", "RevNr", "RevDate", "RevDateStr", "NodeCount",
               "Path", "Action", "Kind", "CopyFromPath", "CopyFromRev",
               "HasText", "TextLen", "TextMD5", "EOL", "Text",
               "PropDiff", "PropMissing", "RevPropDiff", "RevPropMissing"]
    ignore_help = "'" + ignores[0] + "'"
    for i in ignores[1:-1]:
        ignore_help = ignore_help + ", '" + i + "'"
    ignore_help = ignore_help + " and '" + ignores[-1] + "'"
    ignore_help = "Ignore types of differences. This option can be " + \
                  "specified more than once. Valid types are " + ignore_help
    parser.add_option("-I", "--ignore",
                      action="append", dest="ignores",
                      type="choice", choices=ignores,
                      help=ignore_help)
    parser.add_option("--ignore-revprop",
                      action="append", dest="ignorerevprop", type="string",
                      help="ignore a differing/missing revision property")
    parser.add_option("--ignore-property",
                      action="append", dest="ignoreproperty", type="string",
                      help="ignore a differing/missing property")

    (options, args) = parser.parse_args(args)

    if len(args) != 2:
        print("please specify exactly two dump files.")
        return 1

    diff = SvnDumpDiff(args[0], args[1])
    callback = SvnDumpDiffCallback(options.verbose)

    # check-eol ?
    if options.eol != 0:
        diff.set_check_eol()
    # set the ignores
    if options.ignores != None:
        for i in options.ignores:
            callback.add_ignore(i)
    # set revprop ignores
    if options.ignorerevprop != None:
        for i in options.ignorerevprop:
            callback.add_revprop_ignore(i)
    # set property ignores
    if options.ignoreproperty != None:
        for i in options.ignoreproperty:
            callback.add_property_ignore(i)

    diff.execute(callback)
    if callback.had_diffs():
        return 1
    else:
        return 0

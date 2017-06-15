# ===============================================================================
#
# Copyright (C) 2007 Martin Furter <mf@rola.ch>
# Copyright (C) 2007 Chris Foote <cafoote@yahoo.com>
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
from node import SvnDumpNode

__doc__ = """Classes and functions for editing file's in a dump file."""


class SvnDumpEdit:
    """
    A class for editing files in a svn dump file.
    """

    def __init__(self):
        """
        Initialize.
        """

        # input file name
        self.__in_file = ""
        # output file name
        self.__out_file = ""
        # dry-run, do not create an output file
        self.dry_run = True
        # verbosity ( 0 = Silent, 1 = Normal, 2 = Verbose )
        self.verbose = 1
        # edit files
        self.__edit_files = {}

    def set_input_file(self, filename):
        """
        Sets the input dump file name.

        @type filename: string
        @param filename: Name of the input file.
        """
        self.__in_file = filename

    def set_output_file(self, filename):
        """
        Sets the output dump file name and clears the dry-run flag.

        @type filename: string
        @param filename: Name of the output file.
        """
        self.__out_file = filename
        self.dry_run = False

    def replace(self, revision, filename, replacefile):
        """
        Add a file to be replaced.

        @type revision: int
        @param revision: Revision of the file to replace.
        @type filename: string
        @param filename: In repos path of file to replace.
        @type replacefile: string
        @param replacefile: Path to the replacement file.
        """
        rev = self.__edit_files.setdefault(revision, {})
        fn = rev.setdefault(filename, {})
        fn['replace'] = replacefile

    def propdel(self, revision, filename, propname):
        """
        Add a propert to be deleted from a file.

        @type revision: int
        @param revision: Revision of the file to edit.
        @type filename: string
        @param filename: In repos path of file to edit.
        @type propname: string
        @param propname: Property name to delete.
        """
        rev = self.__edit_files.setdefault(revision, {})
        fn = rev.setdefault(filename, {})
        fn['propdel'] = propname

    def print_files(self):
        """
        Print a list of the files to be edited.
        """
        for (r, rev) in self.__edit_files.iteritems():
            print("Edit Revision %d" % r)
            for (f, fn) in rev.iteritems():
                print("  %s:" % f)
                for (e, arg) in fn.iteritems():
                    print("    + %-9s -> %s" % (e, arg))

    def __print(self, level, msg):
        """
        Print msg if the verbosity is >= level.

        @type level: int
        @param level: The verbosity level at which to print msg.
        @type msg: string
        @param msg: The message to print.
        """
        if self.verbose >= level:
            print(msg)

    def execute(self):
        """
        Executes the Edit.
        """

        # +++ catch exception and return errorcode
        srcdmp = SvnDumpFile()
        srcdmp.open(self.__in_file)

        dstdmp = None

        hasrev = srcdmp.read_next_rev()
        if hasrev:
            if not self.dry_run:
                dstdmp = SvnDumpFile()
                if srcdmp.get_rev_nr() == 0:
                    # create new dump with revision 0
                    dstdmp.create_with_rev_0(self.__out_file,
                                             srcdmp.get_uuid(),
                                             srcdmp.get_rev_date_str())
                    hasrev = srcdmp.read_next_rev()
                else:
                    # create new dump starting with the same revNr
                    # as the input dump file
                    dstdmp.create_with_rev_n(self.__out_file,
                                             srcdmp.get_uuid(),
                                             srcdmp.get_rev_nr())
            # now copy all the revisions
            while hasrev:
                self.__process_rev(srcdmp, dstdmp)
                hasrev = srcdmp.read_next_rev()

    def __process_rev(self, srcdmp, dstdmp):
        """
        Process one revision.

        @type srcdmp: SvnDumpFile
        @param srcdmp: The source dump file.
        @type dstdmp: SvnDumpFile
        @param dstdmp: The destination dump file.
        """

        rev = self.__edit_files.get(srcdmp.get_rev_nr())
        level = (rev and 1) or 2
        self.__print(level, "\n\n*** r%d ***\n" % srcdmp.get_rev_nr())

        # add revision and revprops
        if dstdmp != None:
            dstdmp.add_rev(srcdmp.get_rev_props())

        # process nodes
        index = 0
        nodeCount = srcdmp.get_node_count()
        while index < nodeCount:
            node = srcdmp.get_node(index)

            fn = rev and rev.get(node.get_path())
            level = (fn and 1) or 2
            self.__print(level, "  '%s'" % node.get_path())
            if fn:
                for (k, v) in fn.iteritems():
                    if k == 'replace':
                        node = self.__replace_file(node, v)
                    elif k == 'propdel':
                        if node.get_property(v) != None:
                            self.__print(1, "    delete property '%s'" % v)
                            node.del_property(v)

            if dstdmp != None:
                dstdmp.add_node(node)
            index = index + 1

    def __replace_file(self, node, replacement_path):
        """
        Replace the contents of a node.

        @type node: SvnDumpNode
        @param node: The node to replace the contents of.
        @type replacement_path: string
        @param replacement_path: The path to the replacement file.
        @rtype: SvnDumpNode
        @return: The converted node.
        """

        if node.get_text_length() == -1:
            # no text
            self.__print(1, "    no content to replace.")
            return node

        self.__print(1, "    replace content with '%s'" % replacement_path)
        if self.dry_run:
            # do not replace with --dry-run
            return node

        # do the replacement
        newnode = SvnDumpNode(node.get_path(), node.get_action(),
                              node.get_kind())
        if node.has_copy_from():
            newnode.set_copy_from(node.get_copy_from_path(),
                                  node.get_copy_from_rev())
        if node.has_properties():
            newnode.set_properties(node.get_properties())

        newnode.set_text_file(replacement_path)

        return newnode


def __svndump_edit_opt_replace(option, opt, value, parser, *args):
    """
    Option parser callback for replace '--replace filename'.
    """
    if parser.values.revnr == -1:
        raise OptionValueError("Cannot use '%s' without first setting a revision with '-r'." % opt)
    if parser.values.filename == "":
        raise OptionValueError("Cannot use '%s' without first setting a filename with '-f'." % opt)

    edit = args[0]
    edit.replace(parser.values.revnr, parser.values.filename, value)


def __svndump_edit_opt_propdel(option, opt, value, parser, *args):
    """
    Option parser callback for propdel '--propdel propname'.
    """
    if parser.values.revnr == -1:
        raise OptionValueError("Cannot use '%s' without first setting a revision with '-r'." % opt)
    if parser.values.filename == "":
        raise OptionValueError("Cannot use '%s' without first setting a filename with '-f'." % opt)

    edit = args[0]
    edit.propdel(parser.values.revnr, parser.values.filename, value)


def svndump_edit_cmdline(appname, args):
    """
    Parses the commandline and executes the edit.

    Usage:

        >>> svndump_edit_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list(string)
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] src [dst]" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    edit = SvnDumpEdit()
    cbargs = (edit,)
    parser.add_option("-r", "--revision",
                      action="store", type="int", dest='revnr',
                      default=-1,
                      help="revision number to edit.")
    parser.add_option("-f", "--file",
                      action="store", type="string", dest='filename',
                      help="filename of repos path to edit.")
    parser.add_option("--replace",
                      action="callback", callback=__svndump_edit_opt_replace,
                      callback_args=cbargs, type="string",
                      help="path of a replacement file.")
    parser.add_option("--propdel",
                      action="callback", callback=__svndump_edit_opt_propdel,
                      callback_args=cbargs, type="string",
                      help="prop name to delete.")
    parser.add_option("-q", "--quiet",
                      action="store_const", dest="verbose", const=0,
                      help="quiet output.")
    parser.add_option("-v", "--verbose",
                      action="store_const", dest="verbose", const=2, default=1,
                      help="verbose output.")
    parser.add_option("--dry-run",
                      action="store_true", dest="dry_run", default=False,
                      help="just show what would be done but don't do it.")
    (options, args) = parser.parse_args(args)

    if len(args) < 1 or len(args) > 2:
        print("please specify one source and optionally one destination file.")
        return 1
    edit.set_input_file(args[0])
    if len(args) == 2:
        edit.set_output_file(args[1])
    edit.verbose = options.verbose
    if options.dry_run:
        edit.dry_run = options.dry_run

    if edit.verbose >= 2:
        edit.print_files()

    edit.execute()
    return 0

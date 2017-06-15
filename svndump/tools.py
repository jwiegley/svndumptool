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
from optparse import OptionParser

from svndump import __version, copy_dump_file
from common import create_svn_date_str
from file import SvnDumpFileWithHistory, SvnDumpFile

__doc__ = """Various tools."""


# -------------------------------------------------------------------------------
# copy

def svndump_copy_cmdline(appname, args):
    """
    Parses the commandline and executes the copy.

    Usage:

        >>> svndump_copy_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] source destination" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) != 2:
        print("specify exactly one source and one destination dump file.")
        return 1

    copy_dump_file(args[0], args[1])
    return 0


# -------------------------------------------------------------------------------
# export

class SvnDumpExport:
    """
    A class for exporting files from a svn dump files.
    """

    def __init__(self):
        """
        Initialize.
        """

        # files to export, { rev -> { repos-path -> filename, ... }, ... }
        self.__exports = {}

    def add_export_file(self, revnr, repospath, filename):
        """
        Add a file to export.

        @type revnr: integer
        @param revnr: Revision number.
        @type repospath: string
        @param repospath: Path of the file in the repository.
        @type filename: string
        @param filename: Name of the exported file.
        """

        if repospath.startswith('/'):
            repospath = repospath[1:]
        if not self.__exports.has_key(revnr):
            self.__exports[revnr] = {}
        self.__exports[revnr][repospath] = filename

    def has_exports(self):
        '''
        Were files listed for export?

        @rtype: boolean
        @return: True means there are files listed to
                 export, False means there are not.
        '''
        return len(self.__exports) > 0

    def execute(self, dumpfilename, directory):
        """
        Executes the export.

        @type dumpfilename: string
        @param dumpfilename: Name of the svn dump file.
        @type directory: string
        @param directory: Directory to store the exported files.
        """

        dump = SvnDumpFile()
        dump.open(dumpfilename)

        while dump.read_next_rev():
            revnr = dump.get_rev_nr()
            if self.__exports.has_key(revnr):
                for path, filename in self.__exports[revnr].iteritems():
                    print("r%-6d %s" % (revnr, path))
                    nodes = dump.get_nodes_by_path(path, "ACR")
                    saved = False
                    for node in nodes:
                        if node.has_text():
                            outfile = open(filename, "wb")
                            node.write_text_to_file(outfile)
                            outfile.close()
                            saved = True
                            print("  saved as %s" % filename)
                    if not saved:
                        if len(nodes) == 0:
                            print("  not found")
                        else:
                            print("  has no text")
        dump.close()
        return 0


def __svndump_export_opt_e(option, opt, value, parser, *args):
    """
    Option parser callback for rename '-r from to'.
    """
    export = args[0]
    export.add_export_file(int(value[0]), value[1], value[2])


def svndump_export_cmdline(appname, args):
    """
    Parses the commandline and executes the export.

    Usage:

        >>> svndump_export_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dumpfile" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    export = SvnDumpExport()
    parser.add_option("-e", "--export",
                      action="callback", callback=__svndump_export_opt_e,
                      callback_args=(export,),
                      dest=" rev repospath filename",
                      nargs=3, type="string",
                      help="adds a file to export.")
    parser.add_option("-d", "--directory",
                      action="store", type="string",
                      dest="dir", default=".",
                      help="set the directory for the exported files.")
    (options, args) = parser.parse_args(args)

    if not export.has_exports():
        print("Warning: there are no files specified to export.", file=sys.stderr)
        print("         Use -e/--export to specify files", file=sys.stderr)
        print("", file=sys.stderr)
        parser.print_help(file=sys.stderr)
        return 1
    return export.execute(args[0], options.dir)


# -------------------------------------------------------------------------------
# check

class SvnDumpCheck:
    """
    A class for checking svn dump files.
    """

    def __init__(self):
        """
        Initialize.
        """

        # check actions
        self.__check_actions = False
        # check dates
        self.__check_dates = False
        # check md5 sums
        self.__check_md5 = False
        # verbose output
        self.__verbose = False

    def set_check_actions(self, docheck):
        """
        Set the check actions flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__check_actions = docheck

    def set_check_dates(self, docheck):
        """
        Set the check dates flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__check_dates = docheck

    def set_check_md5(self, docheck):
        """
        Set the check md5 sums flag to the given value.

        @type docheck: bool
        @param docheck: New value for the flag.
        """

        self.__check_md5 = docheck

    def set_verbose(self, doverbose):
        """
        Set for verbose output mode
        """

        self.__verbose = doverbose

    def execute(self, dumpfilename):
        """
        Check a dump file.

        @type dumpfilename: string
        @param dumpfilename: Name of the file to check.
        """

        print("\nChecking file " + dumpfilename)
        dump = SvnDumpFileWithHistory()
        if self.__check_actions:
            dump.set_check_actions(True)
        if self.__check_dates:
            dump.set_check_dates(True)
        if self.__check_md5:
            dump.set_check_md5(True)
        dump.open(dumpfilename)
        rc = 0

        while dump.read_next_rev():
            self.__next_rev()
            revnr = dump.get_rev_nr()
            if self.__verbose:
                self.__print_rev(revnr)
            if self.__print_rev_errors(dump):
                rc = 1
            for node in dump.get_nodes_iter():
                self.__next_node()
                if self.__verbose:
                    self.__print_node(revnr, node)
                    self.__print_action(node)
                if self.__print_node_errors(dump, node):
                    rc = 1
        dump.close()
        print(["OK", "Not OK"][rc])
        return rc

    def __next_rev(self):
        """
        Clears the rev_printed flag.
        """
        self.__rev_printed = False

    def __print_rev(self, revnr):
        """
        Prints the revision number if not already done.

        @type revnr: int
        @param revnr: Current revision number.
        """
        if not self.__rev_printed:
            self.__rev_printed = True
            print("  Revision %d" % revnr)

    def __next_node(self):
        """
        Clears the node_printed flag.
        """
        self.__node_printed = False
        self.__action_printed = False

    def __print_node(self, revnr, node):
        """
        Prints the revision number and node path if not already done.

        @type revnr: int
        @param revnr: Current revision number.
        @type node: SvnDumpNode
        @param node: Current node.
        """
        if not self.__node_printed:
            self.__node_printed = True
            self.__print_rev(revnr)
            print("    Node: %s" % node.get_path())

    def __print_action(self, node):
        """
        Prints the node action if not already done.

        @type node: SvnDumpNode
        @param node: Current node.
        """
        if not self.__action_printed:
            self.__action_printed = True
            actionmsg = "    Action: %s" % node.get_action()
            if node.has_copy_from():
                actionmsg += ", copied from r%d %s" % (
                    node.get_copy_from_rev(),
                    node.get_copy_from_path())
            print(actionmsg)

    def __print_rev_errors(self, dump):
        """
        Prints all revision errors for the current dump revision

        @type dump: SvnDumpFile
        @param dump: Current dump file.
        """

        rc = 0
        errlist = dump.get_rev_errors()
        if errlist is None:
            return rc
        revnr = dump.get_rev_nr()
        for err in errlist:
            if err[0] == SvnDumpFile.ERR_REV_DATE_OLDER:
                rc = 1
                self.print_rev(revnr)
                revdate = parse_svn_date_str(err[1][0])
                prevdate = parse_svn_date_str(err[1][1])
                print("    rev date: %s  %10d.%06d" % (
                    err[1][0], revdate[0], revdate[1]))
                print("    previous: %s  %10d.%06d" % (
                    err[1][1], prevdate[0], prevdate[1]))
        return rc

    def __print_node_errors(self, dump, node):
        """
        Prints all node errors for the current dump node

        @type dump: SvnDumpFile
        @param dump: Current dump file.
        """

        rc = 0
        errlist = dump.get_rev_errors()
        if errlist is None:
            return rc
        revnr = dump.get_rev_nr()
        for err in errlist:
            if node.get_path() == err[1][0]:
                rc = 1
                self.__print_node(revnr, node)
                if err[0] == SvnDumpFile.ERR_NODE_MD5_FAIL:
                    print("      ERROR - md5 calc: %s" % err[1][0])
                    print("        diff than md5 node: %s" % err[1][1])
                if err[0] == SvnDumpFile.ERR_NODE_EXISTS:
                    print("      ERROR - Node already exists.")
                if err[0] == SvnDumpFile.ERR_NODE_NO_PARENT:
                    print("      ERROR - Parent doesn't exist.")
                if err[0] == SvnDumpFile.ERR_NODE_PARENT_NOT_DIR:
                    print("      ERROR - Parent is not a directory.")
                if err[0] == SvnDumpFile.ERR_NODE_NO_COPY_SRC:
                    print("      ERROR - Copy-from path doesn't exist."
                          "  r%d %s" % (err[1][2], err[1][3]))
                if err[0] == SvnDumpFile.ERR_NODE_GONE:
                    print("      ERROR - Node doesn't exist.")
        return rc


def svndump_check_cmdline(appname, args):
    """
    Parses the commandline and executes the check.

    Usage:

        >>> svndump_check_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dumpfiles..." % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    check = SvnDumpCheck()
    parser.add_option("-a", "--check-actions",
                      action="store_true", dest="check_actions", default=False,
                      help="check actions like add/change/delete")
    parser.add_option("-d", "--check-dates",
                      action="store_true", dest="check_dates", default=False,
                      help="check that svn:date increases")
    parser.add_option("-m", "--check-md5",
                      action="store_true", dest="check_md5", default=False,
                      help="check md5 sums of the files")
    parser.add_option("-A", "--all-checks",
                      action="store_true", dest="check_all", default=False,
                      help="do all checks")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="verbose output")
    (options, args) = parser.parse_args(args)

    checks = False
    if options.check_actions or options.check_all:
        check.set_check_actions(True)
        checks = True
    if options.check_dates or options.check_all:
        check.set_check_dates(True)
        checks = True
    if options.check_md5 or options.check_all:
        check.set_check_md5(True)
        checks = True
    if options.verbose:
        check.set_verbose(True)

    if not checks:
        print("Please specify at least one check option.")
        return 0

    rc = 0
    for filename in args:
        if check.execute(filename) != 0:
            rc = 1
    return rc


# -------------------------------------------------------------------------------
# ls

class SvnDumpLs:
    """
    A class for listing files in a dump.
    """

    def __init__(self, revNr):
        """
        Initialize.
        """

        self.revNr = revNr
        if revNr == -1:
            self.revNr = 2000000000

    def execute(self, dumpfilename):
        """
        Print file list of a dump file.

        @type dumpfilename: string
        @param dumpfilename: Name of the file to log.
        """

        # pass 1: search copy-from revisions
        dump = SvnDumpFile()
        dump.open(dumpfilename)
        copyfromrevs = {}
        filedict = {}

        while dump.read_next_rev():
            revnr = dump.get_rev_nr()
            if revnr > self.revNr:
                break
            for node in dump.get_nodes_iter():
                # action = actions[node.get_action()]
                action = node.get_action()
                path = node.get_path()
                if path == "" or path[0] != "/":
                    path = "/" + path
                if action == "add" and node.has_copy_from():
                    copyfromrevs[node.get_copy_from_rev()] = True
        dump.close()

        # pass 2: do the work
        dump = SvnDumpFile()
        dump.open(dumpfilename)
        filedict = {}

        prevrevnr = 0
        while dump.read_next_rev():
            revnr = dump.get_rev_nr()
            # loop over missing revisions
            prevrevnr += 1
            while prevrevnr < revnr:
                if copyfromrevs.has_key(prevrevnr):
                    copyfromrevs[prevrevnr] = filedict.keys()[:]
                prevrevnr += 1
            if revnr > self.revNr:
                break
            for node in dump.get_nodes_iter():
                action = node.get_action()
                path = node.get_path()
                if path == "" or path[0] != "/":
                    path = "/" + path
                if action == "add":
                    filedict[path] = path
                    if node.has_copy_from():
                        frompath = node.get_copy_from_path() + "/"
                        if frompath[0] != "/":
                            frompath = "/" + frompath
                        fromlen = len(frompath)
                        topath = path + "/"
                        for path in copyfromrevs[node.get_copy_from_rev()]:
                            if path.startswith(frompath):
                                newpath = topath + path[fromlen:]
                                filedict[newpath] = newpath
                elif action == "delete":
                    del filedict[path]
                    if path[-1] != "/":
                        path = path + "/"
                    for subpath in filedict.keys()[:]:
                        if subpath.startswith(path):
                            del filedict[subpath]
            if copyfromrevs.has_key(revnr):
                copyfromrevs[revnr] = filedict.keys()[:]
        dump.close()

        filelist = []
        for path in filedict:
            filelist.append(path)
        filelist.sort()
        for path in filelist:
            print(path)

        return 0

    def old_execute(self, dumpfilename):
        """
        Print file list of a dump file.

        @type dumpfilename: string
        @param dumpfilename: Name of the file to log.
        """

        dump = SvnDumpFile()
        dump.open(dumpfilename)
        actions = {"add": "A", "change": "M", "delete": "D", "replace": "R"}
        lines = ""

        while dump.read_next_rev():
            revnr = dump.get_rev_nr()
            if revnr == self.revNr or self.revNr == -1:
                lines = ""
                for node in dump.get_nodes_iter():
                    action = actions[node.get_action()]
                    path = node.get_path()
                    if path == "" or path[0] != "/":
                        path = "/" + path
                    if node.has_copy_from():
                        fpath = node.get_copy_from_path()
                        frev = node.get_copy_from_rev()
                        if fpath == "" or fpath[0] != "/":
                            fpath = "/" + fpath
                        path += " (from %s:%d)" % (fpath, frev)
                    lines += "   %s %s\n" % (action, path)
                if revnr == self.revNr:
                    print(lines, end='')
                    lines = ""
                    break
        if len(lines) > 0:
            print(lines, end='')

        dump.close()
        return 0


def svndump_ls_cmdline(appname, args):
    """
    Parses the commandline and executes the ls.

    Usage:

        >>> svndump_ls_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dumpfiles..." % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    parser.add_option("-r", "--revision",
                      action="store", type="int",
                      dest="revnr", default=-1,
                      help="revision number")
    (options, args) = parser.parse_args(args)

    log = SvnDumpLs(options.revnr)

    if len(args) == 1:
        return log.execute(args[0])
    elif len(args) == 0:
        print("Specify a dump file.")
        return 1
    else:
        print("Specify only one dump file.")
        return 1


# -------------------------------------------------------------------------------
# log

class SvnDumpLog:
    """
    A class for checking svn dump files.
    """

    def __init__(self):
        """
        Initialize.
        """

        # verbose
        self.__verbose = False
        # revision range
        self.__from_rev = -1
        self.__to_rev = 2000000000

    def set_verbose(self, verbose):
        """
        Set the verbose flag to the given value.

        @type verbose: bool
        @param verbose: New value for the flag.
        """

        self.__verbose = verbose

    def set_revision(self, revision):
        """
        Set the revision range to the given value.

        @type revision: string
        @param revision: A revision number or a range (X:Y).
        """

        if revision == None:
            return True
        if len(revision) == 0:
            return True
        parts = revision.split(":")
        n = len(parts)
        if n == 1:
            try:
                self.__from_rev = int(parts[0])
            except ValueError:
                print("Wrong format of revision argument '%s'" % revision)
                return False
            self.__to_rev = self.__from_rev
        elif n == 2:
            try:
                self.__from_rev = int(parts[0])
                if parts[1] != "HEAD":
                    self.__to_rev = int(parts[1])
            except ValueError:
                print("Wrong format of revision argument '%s'" % revision)
                return False
        else:
            print("Wrong format of revision argument '%s'" % revision)
            return False
        return True

    def execute(self, dumpfilename):
        """
        Print log of a dump file.

        @type dumpfilename: string
        @param dumpfilename: Name of the file to log.
        """

        print("\n\n" + "=" * 72)
        line = "-" * 72
        print("Dumpfile: " + dumpfilename)
        dump = SvnDumpFile()
        dump.open(dumpfilename)
        actions = {"add": "A", "change": "M", "delete": "D", "replace": "R"}

        while dump.read_next_rev():
            revnr = dump.get_rev_nr()
            if revnr >= self.__from_rev and revnr <= self.__to_rev:
                author = dump.get_rev_author()
                date = dump.get_rev_date_str()
                log = dump.get_rev_log()
                linecnt = len(log.split("\n"))
                lines = "%d line" % linecnt
                if linecnt > 1:
                    lines += "s"
                print(line)
                print("r%d | %s | %s | %s" % (revnr, author, date, lines))
                if self.__verbose:
                    print("Changed paths:")
                    for node in dump.get_nodes_iter():
                        action = actions[node.get_action()]
                        path = node.get_path()
                        if path == "" or path[0] != "/":
                            path = "/" + path
                        if node.has_copy_from():
                            fpath = node.get_copy_from_path()
                            frev = node.get_copy_from_rev()
                            if fpath == "" or fpath[0] != "/":
                                fpath = "/" + fpath
                            path += " (from %s:%d)" % (fpath, frev)
                        print("   %s %s" % (action, path))
                print("\n" + log.rstrip() + "\n")

        print(line)
        dump.close()
        return 0


def svndump_log_cmdline(appname, args):
    """
    Parses the commandline and executes the log.

    Usage:

        >>> svndump_log_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] dumpfiles..." % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    log = SvnDumpLog()
    parser.add_option("-r", "--revision",
                      action="store", type="string",
                      dest="revision", default=None,
                      help="revision number or range (X:Y)")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="verbose output")
    (options, args) = parser.parse_args(args)

    log.set_verbose(options.verbose)
    if not log.set_revision(options.revision):
        return 1

    rc = 0
    for filename in args:
        if log.execute(filename) != 0:
            rc = 1
    return rc


# -------------------------------------------------------------------------------
# join

def join_dumpfiles(inputlist, outfilename):
    """
    Joins dump files.

    @type inputlist: list
    @param inputlist: A list containing the input filenames.
    @type outfilename: string
    @param outfilename: Name of the output dump file.
    @rtype: int
    @return: 0 for success.
    """

    outdump = None
    noutrev = 0
    lastrev = -1
    for filename in inputlist:
        print("reading %s ..." % filename)
        ninrev = 0
        indump = SvnDumpFile()
        indump.open(filename)
        hasrev = indump.read_next_rev()
        if hasrev:
            if outdump == None:
                outdump = SvnDumpFile()
                if indump.get_rev_nr() == 0:
                    # create new dump with revision 0
                    outdump.create_with_rev_0(outfilename, indump.get_uuid(),
                                              indump.get_rev_date_str())
                    hasrev = indump.read_next_rev()
                else:
                    # create new dump starting with the
                    # same revNr as the original dump
                    outdump.create_with_rev_n(outfilename, indump.get_uuid(),
                                              indump.get_rev_nr())
            else:
                # check rev number
                if indump.get_rev_nr() == 0:
                    hasrev = indump.read_next_rev()
                if hasrev:
                    if (lastrev + 1) != indump.get_rev_nr():
                        print("renumbering of revisions not supported.")
                        print("last rev was %d, next is %d." % (lastrev,
                                                                indump.get_rev_nr()))
                        indump.close()
                        outdump.close()
                        return 1
            while hasrev:
                outdump.add_rev_from_dump(indump)
                ninrev += 1
                lastrev = indump.get_rev_nr()
                hasrev = indump.read_next_rev()
        indump.close()
        print("  copied %d revisions." % ninrev)
        noutrev += ninrev
    outdump.close()
    print("wrote %d revisions, last was r%d." % (noutrev, lastrev))


def svndump_join_cmdline(appname, args):
    """
    Parses the commandline and executes the join.

    Usage:

        >>> svndump_join_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s -o outputfile dumpfiles..." % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    parser.add_option("-o", "--output-file",
                      action="store", type="string",
                      dest="outfile", default=None,
                      help="set the name of the output dump file.")
    (options, args) = parser.parse_args(args)

    if options.outfile == None:
        print("please specify the output dump file (option -o).")
        return 1
    if len(args) == 0:
        print("please specify at least one input dump file.")
        return 1

    return join_dumpfiles(args, options.outfile)


# -------------------------------------------------------------------------------
# split

def split_dumpfiles(inputfilename, outlist):
    """
    Splits a dump file.

    @type inputfilename: string
    @param inputfilename: Name of the input file.
    @type outlist: list
    @param outlist: List of tuples containing start revnr, end revnr and filename.
    @rtype: int
    @return: 0 for success.
    """

    if len(outlist) == 0:
        return 0

    outlist = outlist[:]
    outlist.sort()
    parallel = False
    for i in range(0, len(outlist) - 1):
        if outlist[i][1] > outlist[i + 1][0]:
            parallel = True
            break

    if not parallel:
        indump = SvnDumpFile()
        indump.open(inputfilename)
        index = 0
        startrev = outlist[index][0]
        endrev = outlist[index][1]
        outfile = outlist[index][2]
        outdump = None
        while indump.read_next_rev():
            revnr = indump.get_rev_nr()
            if outdump == None:
                if revnr >= startrev:
                    outdump = SvnDumpFile()
                    if revnr == 0:
                        # create new dump with revision 0
                        outdump.create_with_rev_0(outfile, indump.get_uuid(),
                                                  indump.get_rev_date_str())
                    else:
                        # create new dump starting with the
                        # same revNr as the original dump
                        outdump.create_with_rev_n(outfile, indump.get_uuid(),
                                                  indump.get_rev_nr())
            if outdump != None:
                # have an output file, copy the revision if revnr > 0
                if revnr > 0:
                    outdump.add_rev_from_dump(indump)
                if revnr >= endrev:
                    # end revision reached
                    outdump.close()
                    outdump = None
                    index += 1
                    if index >= len(outlist):
                        # done.
                        break
                    # next range
                    startrev = outlist[index][0]
                    endrev = outlist[index][1]
                    outfile = outlist[index][2]
        if outdump != None:
            outdump.close()
        indump.close()
    else:
        print("overlapping revision ranges not supported (yet).")
        return 1
    return 0


def svndump_split_cmdline(appname, args):
    """
    Parses the commandline and executes the split.

    Usage:

        >>> svndump_split_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s inputfile [startrev endrev filename]..." % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) == 0:
        return 0
    if (len(args) % 3) != 1:
        print("illegal number of args.")
        return 0

    infile = args[0]
    outlist = []
    for i in range(1, len(args), 3):
        outlist.append((int(args[i]), int(args[i + 1]), args[i + 2]))

    return split_dumpfiles(infile, outlist)

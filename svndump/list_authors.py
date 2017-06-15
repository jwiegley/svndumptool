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


def list_authors(srcfile, git_fmt):
    """
    List all the authors from the dump file.

    @type srcfile: string
    @param srcfile: Source filename.
    @type git_fmt: boolean
    @param rev_prop: Whether or not to output in git author file format
    """

    # SvnDumpFile classes for reading/writing dumps
    srcdmp = SvnDumpFile()
    # open source file
    authors = []
    srcdmp.open(srcfile)
    hasrev = srcdmp.read_next_rev()
    if hasrev:
        while hasrev:
            if srcdmp.has_rev_prop("svn:author"):
                author = srcdmp.get_rev_prop_value("svn:author")
                if author not in authors:
                    authors.append(author)
            hasrev = srcdmp.read_next_rev()
    else:
        print("no revisions in the source dump '%s' ???" % srcfile)

    authors.sort()
    fmt = "%s"
    if git_fmt:
        fmt = "%s = RealName <email>"
    for author in authors:
        print(fmt % author)
    # cleanup
    srcdmp.close()


def svndump_list_authors(appname, args):
    """
    Parses the commandline and lists the large files based on the options.

    Usage:

        >>> svndump_list_authors( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s dumpfile" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)

    parser.add_option("-t", "--git-author-format", action="store_true", dest="git_fmt", default=False,
                      help="output the authors in a format suitable for creating a git authors transform file (user_name = RealName <email>).")
    (options, args) = parser.parse_args(args)

    if len(args) != 1:
        print("Specify a dump file from which to list the authors")
        return 1

    list_authors(args[0], options.git_fmt)
    return 0

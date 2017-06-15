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

from svndump import __version, SvnDumpFile
from node import SvnDumpNode


def copy_adding_git_ignore(srcfile, dstfile):
    """
    Copy a dump file adding .gitignore files in all directories that have
    an svn:ignore property.

    @type srcfile: string
    @param srcfile: Source filename.
    @type dstfile: string
    @param dstfile: Destination filename.
    """

    # SvnDumpFile classes for reading/writing dumps
    srcdmp = SvnDumpFile()
    dstdmp = SvnDumpFile()

    # open source file
    srcdmp.open(srcfile)
    gitignores = {}
    # used to ensure that copyfrom-revs are correct after the copy.  If
    # there are any empty revision in the source dump file, the copyfrom-revs
    # could be affected.
    revmap = {}

    hasrev = srcdmp.read_next_rev()
    if hasrev:
        # create the dump file
        dstdmp.create_like(dstfile, srcdmp)
        # now copy all the revisions
        while hasrev:
            dstdmp.add_rev(srcdmp.get_rev_props())
            for node in srcdmp.get_nodes_iter():
                if node.has_copy_from():
                    node.set_copy_from(node.get_copy_from_path(), revmap[node.get_copy_from_rev()])
                # add the original node
                dstdmp.add_node(node)
                if node.get_property("svn:ignore") is not None:
                    # find out what the change is and act on it appropriately
                    path = node.get_path() + "/.gitignore"
                    action = node.get_action()
                    if (action == "change" or action == "add"):
                        if (path in gitignores):
                            # already saw this one - it is a change to the .gitignore file
                            newnode = SvnDumpNode(path, "change", "file")
                        else:
                            # haven't seen this one yet
                            newnode = SvnDumpNode(path, "add", "file")
                            gitignores[path] = True
                        f = open("gitignore", "wb");
                        f.write(node.get_property("svn:ignore"))
                        f.close()
                        newnode.set_text_file("gitignore")
                        dstdmp.add_node(newnode)
                        os.remove("gitignore")
                    elif (action == "delete"):
                        newnode = SvnDumpNode(path, "delete", "file")
                        dstdmp.add_node(newnode)
                        del gitignores[path]
                    else:
                        print("Unhandled action: '%s'" % action)
            revmap[srcdmp.get_rev_nr()] = dstdmp.get_rev_nr()
            hasrev = srcdmp.read_next_rev()
    else:
        print("no revisions in the source dump '%s' ???" % srcfile)

    # cleanup
    srcdmp.close()
    dstdmp.close()


def svndump_add_git_ignore(appname, args):
    """
    Parses the commandline and executes the transformation.

    Usage:

        >>> svndump_add_git_ignore( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s source destination\n\n" % appname
    usage += "This is useful when preparing a dump file that will\nultimately be imported into a git repository."
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) != 2:
        print("specify a source dump file and a destination dump file")
        return 1

    copy_adding_git_ignore(args[0], args[1])
    return 0

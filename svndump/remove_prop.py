# ===============================================================================
#
# Copyright (C) 2003 Martin Furter <mf@rola.ch>
# Copyright (C) 2013 Tom Taxon <tom@ourloudhouse.com>
# Copyright (C) 2015 Ole Martin Handeland <svndumptool-contribs@olemartin.org>
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
import re

from svndump import __version, SvnDumpFile


def copy_remove_prop(propname, regex, srcfile, dstfile):
    """
    Copy a dump file while removing all properties with values matching a given regex.

    @type srcfile: string
    @param srcfile: Source filename.
    @type dstfile: string
    @param dstfile: Destination filename.
    """

    _regex = re.compile(regex, re.M)

    # SvnDumpFile classes for reading/writing dumps
    srcdmp = SvnDumpFile()
    dstdmp = SvnDumpFile()

    # open source file
    srcdmp.open(srcfile)

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

                propvalue = node.get_property(propname)
                if propvalue is not None and _regex.match(propvalue):
                    print("removing property " + propname + " with value " + propvalue.strip())
                    node.del_property(propname)
                dstdmp.add_node(node)

            revmap[srcdmp.get_rev_nr()] = dstdmp.get_rev_nr()
            hasrev = srcdmp.read_next_rev()
    else:
        print("no revisions in the source dump '%s' ???" % srcfile)

    # cleanup
    srcdmp.close()
    dstdmp.close()


def svndump_remove_prop(appname, args):
    """
    Parses the commandline and executes the transformation.

    Usage:

        >>> svndump_remove_prop( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s propname regex source destination\n\n" % appname
    usage += "This removes all properties with a value matching the given regex"
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) != 4:
        print("specify a property name, regex, source dump file and a destination dump file")
        return 1

    copy_remove_prop(args[0], args[1], args[2], args[3])
    return 0

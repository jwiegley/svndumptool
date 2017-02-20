#===============================================================================
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
#===============================================================================

#import 
__all__ = [ "common", "cvs2svnfix", "diff", "eolfix", "file", "merge",
            "node", "props", "sanitize", "tools" ]

import re
import common
from file import SvnDumpFile

__doc__ = """A package for processing subversion dump files."""
__version = "0.8.0"

def copy_dump_file( srcfile, dstfile, transformer=None ):
    """
    Copy a dump file.

    @type srcfile: string
    @param srcfile: Source filename.
    @type dstfile: string
    @param dstfile: Destination filename.
    @type transformer: class with method transform(dump)
    @param transformer: A class to perform a transformation on each revision, or None.
    """

    # SvnDumpFile classes for reading/writing dumps
    srcdmp = SvnDumpFile()
    dstdmp = SvnDumpFile()

	# Copy_from_rev casacading
    oldRevToNewRev = dict()

    # open source file
    srcdmp.open( srcfile )

    hasrev = srcdmp.read_next_rev()
    if hasrev:
        # create the dump file
        dstdmp.create_like( dstfile, srcdmp )
        # now copy all the revisions
        while hasrev:
            if transformer != None:
                transformer.transform( srcdmp )
            for node in srcdmp.get_nodes_iter():
                if node.has_copy_from():
                    if oldRevToNewRev.has_key(node.get_copy_from_rev()):
                        node.set_copy_from_rev(oldRevToNewRev[node.get_copy_from_rev()])
                    else:
                        #We have a problem, the copy from revision is missing.
						#We look for a previous revision containing the file
                        found = False
                        candidate = node.get_copy_from_rev()
                        while candidate > 0 and not found:
                            candidate = candidate - 1
                            found = oldRevToNewRev.has_key(candidate)
                        if found:
							oldRevToNewRev[node.get_copy_from_rev()] = candidate
							node.set_copy_from_rev(candidate)
            dstdmp.add_rev_from_dump( srcdmp )
            oldRevToNewRev[srcdmp.get_rev_nr()] = dstdmp.get_rev_nr()
            hasrev = srcdmp.read_next_rev()
    else:
        print "no revisions in the source dump '%s' ???" % srcfile

    # cleanup
    srcdmp.close()
    dstdmp.close()

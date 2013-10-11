#!/usr/bin/env python
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

import sys

from svndump import __version
from svndump.cvs2svnfix import svndump_cvs2svnfix_cmdline
from svndump.diff import svndump_diff_cmdline
from svndump.edit import svndump_edit_cmdline
from svndump.eolfix import svndump_eol_fix_cmdline
from svndump.merge import svndump_merge_cmdline
from svndump.props import svndump_transform_revprop_cmdline, \
                          svndump_transform_prop_cmdline, \
                          svndump_eolfix_revprop_cmdline, \
                          svndump_eolfix_prop_cmdline, \
                          svndump_apply_autoprops_cmdline
from svndump.sanitize import svndump_sanitize_cmdline
from svndump.tools import svndump_copy_cmdline, svndump_export_cmdline, \
                          svndump_check_cmdline, svndump_log_cmdline, \
                          svndump_ls_cmdline, \
                          svndump_join_cmdline, svndump_split_cmdline
from svndump.list_authors import svndump_list_authors
__commands = {
    "apply-autoprops":      svndump_apply_autoprops_cmdline,
    "check":                svndump_check_cmdline,
    "copy":                 svndump_copy_cmdline,
    "cvs2svnfix":           svndump_cvs2svnfix_cmdline,
    "diff":                 svndump_diff_cmdline,
    "list-authors":         svndump_list_authors,
    "edit":                 svndump_edit_cmdline,
    "eolfix":               svndump_eol_fix_cmdline,
    "eolfix-prop":          svndump_eolfix_prop_cmdline,
    "eolfix-revprop":       svndump_eolfix_revprop_cmdline,
    "export":               svndump_export_cmdline,
    "join":                 svndump_join_cmdline,
    "log":                  svndump_log_cmdline,
    "ls":                   svndump_ls_cmdline,
    "merge":                svndump_merge_cmdline,
    "sanitize":             svndump_sanitize_cmdline,
    "split":                svndump_split_cmdline,
    "transform-prop":       svndump_transform_prop_cmdline,
    "transform-revprop":    svndump_transform_revprop_cmdline,
}

def __help( appname, args ):
    rc = 0
    if len(args) == 1 and __commands.has_key( args[0] ):
        __commands[args[0]]( appname + " " + args[0], [ "-h" ] )
    else:
        print ""
        print "svndumptool.py command [options]"
        print ""
        print "  commands:"
        print "    apply-autoprops      apply auto-props to added files"
        print "    check                check a dump file"
        print "    copy                 copy a dump file"
        print "    cvs2svnfix           fix a cvs2svn created dump file"
        print "    diff                 show differences between two dump files"
        print "    edit                 edit files in a dump file"
        print "    eolfix               fix EOL of text files in a dump"
        print "    eolfix-revprop       fix EOL of revision property"
        print "    eolfix-prop          fix EOL of node property"
        print "    export               export files from a dump file"
        print "    join                 join dump files"
        print "    list-authors         list all the authors in a dump file"
        print "    log                  show the log of a dump file"
        print "    ls                   list files of a given revision"
        print "    merge                merge dump files"
        print "    sanitize             sanitize dump files"
        print "    split                split dump files"
        print "    transform-revprop    transform a revision property"
        print "    transform-prop       transform a node property"
        print "    --version            print the version"
        print ""
        print "  use 'svndumptool.py command -h' for help about the commands."
        print ""
    return rc

def __print_version( appname, args ):
    print appname + " " + __version
    return 0

if __name__ == '__main__':
    appname = sys.argv[0].replace( "\\", "/" )
    n = appname.rfind( "/" )
    if n >= 0:
        appname = appname[n+1:]
    pfx = appname[0:7]
    cmd = appname[7:-3]
    sfx = appname[-3:]
    func = __help;
    args = []
    argidx = 0
    if pfx == "svndump" and sfx == ".py" and __commands.has_key( cmd ):
        func = __commands[cmd]
        argidx = 1
    elif len( sys.argv ) > 1:
        cmd = sys.argv[1]
        if __commands.has_key( cmd ):
            func = __commands[cmd]
            appname += " " + cmd
        elif cmd == "--version":
            func = __print_version
        argidx = 2
    if argidx < len( sys.argv ):
        args = sys.argv[argidx:]
    sys.exit( func( appname, args ) )


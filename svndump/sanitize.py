#!/usr/bin/env python
# ===============================================================================
#
# Copyright (C) 2003 Martin Furter <mf@rola.ch>
# Copyright (C) 2007 CommProve, Inc. (Eli Carter <eli.carter@commprove.com>)
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

import os
import sys
import tempfile
import random
import string

try:
    import hashlib
except ImportError:
    import md5 as hashlib

from svndump import __version
from optparse import OptionParser
from file import SvnDumpFile
from __init__ import copy_dump_file


class SanitizeDumpFile(object):
    def __init__(self, options):
        self.__options = options
        self.sanitize_salt = self.salthex_to_salt(options.salt)
        print("Using salt %s" % (options.salt,))
        self.sanitized_authors = []

    def transform(self, dump):
        """The dump object passed to this method has been set to the revision
        we're to transform"""
        rev_props = dump.get_rev_props()
        self.sanitize_rev_props(rev_props)
        for node in dump.get_nodes_iter():
            node = self.sanitize_node(node)

    def salthex_to_salt(self, salthex):
        bytehex = []
        for i in range(0, len(salthex), 2):
            bytehex.append(salthex[i:i + 2])
        bytes = [chr(string.atoi(h, 16)) for h in bytehex]
        return ''.join(bytes)

    def sanitize_rev_props(self, rev_props):
        for k in rev_props.iterkeys():
            if self.__options.logs and k == 'svn:log':
                rev_props['svn:log'] = self.hash(rev_props['svn:log'])
            elif self.__options.usernames and k == 'svn:author':
                author = rev_props['svn:author']
                try:
                    i = self.sanitized_authors.index(author)
                except ValueError:
                    i = len(self.sanitized_authors)
                    self.sanitized_authors.append(author)
                rev_props['svn:author'] = "author%s" % (i,)
            elif k == 'svn:date':
                pass  # leave this for now.
            else:
                print("Couldn't sanitize %s: \"%s\"" % (k, rev_props[k]))
        return rev_props

    # Sanitize the data using a salted md5sum
    def hash(self, data):
        return hashlib.md5(self.sanitize_salt + data).hexdigest()

    def sanitize_path(self, path):
        parts = path.split('/')
        sparts = []
        for part in parts:
            if part in self.__options.filename_excludes:
                spart = part
            else:
                spart = self.hash(part)
            sparts.append(spart)
        spath = '/'.join(sparts)
        return spath

    def sanitize_node(self, node):
        if self.__options.file_data_method != "none" and node.has_text():
            # Write the original data to a temp file
            (fd, origname) = tempfile.mkstemp(prefix="svndumptool")
            origdatafile = os.fdopen(fd, "wb+")
            node.write_text_to_file(origdatafile)
            origdatafile.seek(0)
            # New data tempfile
            (fd, newname) = tempfile.mkstemp(prefix="svndumptool")
            newdatafile = os.fdopen(fd, "wb+")
            if self.__options.file_data_method == "whole":
                # Calculate the salted md5sum
                md5sum = sdt_md5()
                md5sum.update(self.sanitize_salt)
                while True:
                    data = origdatafile.read(1024 ** 2)
                    if not len(data):
                        break
                    md5sum.update(data)
                # Write the sanitized data to another temp file.
                newdatafile.write("%s\n" % md5sum.hexdigest())
            elif self.__options.file_data_method == "line":
                # Write the sanitized data to another temp file.
                newdatafile.writelines(["%s\n" % self.hash(line) for line in origdatafile.readlines()])
            else:
                assert False, "self.__options.file_data_method has impossible value \"%s\"" % (
                self.__options.file_data_method,)
            # clean up new tempfile handle
            newdatafile.close()
            # clean up the original tempfile
            origdatafile.close()
            os.remove(origname)
            # Set the new content.
            node.set_text_file(newname, delete=True)

        if self.__options.filenames and node.get_path():
            node.set_path(self.sanitize_path(node.get_path()))
        if self.__options.filenames and node.has_copy_from():
            path = node.get_copy_from_path()
            rev = node.get_copy_from_rev()
            path = self.sanitize_path(path)
            node.set_copy_from(path, rev)
        # TODO: Properties?
        return node


def generate_salthex():
    salt = ''.join(["%02x" % (random.randrange(0, 256),) for x in range(8)])
    return salt


def svndump_sanitize_cmdline(appname, args):
    """
    Parses the commandline and executes the sanitization.

    Usage:

        >>> svndump_sanitize_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s [options] source destination" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    parser.add_option("-f", "--no-file-data",
                      help="Do not sanitize file data.  (Equivalent to --file-data=none.)",
                      action="store_const", const="none", dest="file_data_method", default=True)
    parser.add_option("-m", "--file-data",
                      help="Method to sanitize file data: whole, line, none.  Default is whole.",
                      type="choice", choices=["whole", "line", "none"],
                      action="store", dest="file_data_method", default="whole")
    parser.add_option("-n", "--no-filenames",
                      help="Do not sanitize filenames",
                      action="store_false", dest="filenames", default=True)
    parser.add_option("-e", "--exclude-filename",
                      help="Do not sanitize this filename.  May be used multiple times.",
                      action="append", dest="filename_excludes", default=[])
    parser.add_option("-u", "--no-usernames",
                      help="Do not sanitize usernames",
                      action="store_false", dest="usernames", default=True)
    parser.add_option("-l", "--no-logs",
                      help="Do not sanitize log messages",
                      action="store_false", dest="logs", default=True)
    random_salt = generate_salthex()
    parser.add_option("-s", "--salt",
                      help="Specify the salt to use in hex",
                      dest="salt", default=random_salt)

    (options, args) = parser.parse_args(args)

    if len(args) != 2:
        print("specify exactly one source and one destination dump file.")
        return 1

    sanitizer = SanitizeDumpFile(options)
    copy_dump_file(args[0], args[1], sanitizer)
    return 0


def sdt_md5():
    """
    Returns a new md5 object.
    
    For compatibility with python <2.5.
    """
    return hashlib.md5()

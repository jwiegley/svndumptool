# ===============================================================================
#
# Copyright (C) 2003 Martin Furter <mf@rola.ch>
# Copyright (C) 2007 CommProve, Inc (Eli Carter <eli.carter@commprove.com>)
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

from svndump import __version, copy_dump_file, SvnDumpFile


def re_sub(pattern, replacement, string):
    print("New replacement:")

    def _r(m):
        # Now this is ugly.
        # Python has a "feature" where unmatched groups return None
        # then re.sub chokes on this.
        # see http://bugs.python.org/issue1519638

        # this works around and hooks into the internal of the re module...

        # the match object is replaced with a wrapper that
        # returns "" instead of None for unmatched groups

        class _m:
            def __init__(self, m):
                self.m = m
                self.string = m.string

            def group(self, n):
                return m.group(n) or ""

        return re._expand(pattern, _m(m), replacement)

    newValue = re.sub(pattern, _r, string)
    print(" - Previous value => %s \n - New value => %s " % (string, newValue))
    return newValue


class RevisionPropertyTransformer:
    """
    A class for transforming the revision properties of a dump file class.
    """

    def __init__(self, propertyName, regexStr, replaceTemplate):
        """
        Creates a RevisionPropertyTransformer class.

        @type propertyName: string
        @param propertyName: Name of the property to transform.
        @type regexStr: string
        @param regexStr: The regular expression to match the value against.
        @type replaceTemplate: string
        @param replaceTemplate: The replacement string (may contain group references, e.g. \1).
        """
        self.__property_name = propertyName
        self.__pattern = re.compile(regexStr)
        self.__replace_template = replaceTemplate

    def transform(self, dump):
        if dump.has_rev_prop(self.__property_name):
            value = dump.get_rev_prop_value(self.__property_name)
            matcher = self.__pattern.match(value)
            if matcher:
                replace_str = matcher.expand(self.__replace_template)
                dump.set_rev_prop_value(self.__property_name, replace_str)


def svndump_transform_revprop_cmdline(appname, args):
    """
    Parses the commandline and executes the transformation.

    Usage:

        >>> svndump_transform_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s propname regex replace source destination" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) != 5:
        print("specify exactly one propname to transform, one regex to match the value against,\n"
              "one replacement string, one source dump file and one destination dump file.")
        return 1

    copy_dump_file(args[3], args[4], RevisionPropertyTransformer(args[0], args[1], args[2]))
    return 0


class EolRevisionPropertyTransformer:
    """
    A class for fixing EOL of the revision properties of a dump file class.
    """

    def __init__(self, propertyName):
        """
        Creates a EolRevisionPropertyTransformer class.

        @type propertyName: string
        @param propertyName: Name of the property to transform.
        """
        self.__property_name = propertyName

    def transform(self, dump):
        if dump.has_rev_prop(self.__property_name):
            value = dump.get_rev_prop_value(self.__property_name)
            if value is not None:
                newValue = value.replace("\r\n", "\n")
                if newValue != value:
                    dump.set_rev_prop_value(self.__property_name, newValue)


def svndump_eolfix_revprop_cmdline(appname, args):
    """
    Parses the commandline and executes the transformation.

    Usage:

        >>> svndump_eolfix_revprop_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s propname source destination" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) != 3:
        print("specify exactly one propname to fix EOL, one source dump file and one destination dump file.")
        return 1

    copy_dump_file(args[1], args[2], EolRevisionPropertyTransformer(args[0]))
    return 0


class PropertyTransformer:
    """
    A class for transforming the properties of a dump file class.
    """

    def __init__(self, propertyName, regexStr, replaceTemplate):
        """
        Creates a RevisionPropertyTransformer class.

        @type propertyName: string
        @param propertyName: Name of the property to transform.
        @type regexStr: string
        @param regexStr: The regular expression to match the value against.
        @type replaceTemplate: string
        @param replaceTemplate: The replacement string (may contain group references, e.g. \1).
        """
        self.__property_name = propertyName
        self.__pattern = re.compile(regexStr, re.M)
        self.__replace_template = replaceTemplate

    def transform(self, dump):
        for node in dump.get_nodes_iter():
            value = node.get_property(self.__property_name)
            if value is not None:
                newvalue = re_sub(self.__pattern, self.__replace_template, value)
                node.set_property(self.__property_name, newvalue)


def svndump_transform_prop_cmdline(appname, args):
    """
    Parses the commandline and executes the transformation.

    Usage:

        >>> svndump_transform_prop_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s propname regex replace source destination" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) != 5:
        print("specify exactly one propname to transform, one regex to match the value against,\n"
              "one replacement string, one source dump file and one destination dump file.")
        return 1

    copy_dump_file(args[3], args[4], PropertyTransformer(args[0], args[1], args[2]))
    return 0


class EolPropertyTransformer:
    """
    A class for fixing EOL of the properties of a dump file class.
    """

    def __init__(self, propertyName):
        """
        Creates a EolPropertyTransformer class.

        @type propertyName: string
        @param propertyName: Name of the property to transform.
        """
        self.__property_name = propertyName

    def transform(self, dump):
        for node in dump.get_nodes_iter():
            value = node.get_property(self.__property_name)
            if value is not None:
                newValue = value.replace("\r\n", "\n")
                if newValue != value:
                    node.set_property(self.__property_name, newValue)


def svndump_eolfix_prop_cmdline(appname, args):
    """
    Parses the commandline and executes the transformation.

    Usage:

        >>> svndump_eolfix_prop_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    usage = "usage: %s propname source destination" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    (options, args) = parser.parse_args(args)

    if len(args) != 3:
        print("specify exactly one propname to fix EOL, one source dump file and one destination dump file.")
        return 1

    copy_dump_file(args[1], args[2], EolPropertyTransformer(args[0]))
    return 0


class SvnConfigParser:
    """
    A class similar to ConfigParser which actually works with SVN's config.
    """

    def __init__(self, filename):
        """
        Initialize the object and read the config file.

        @type filename: string
        @param filename: Name of the config file.
        """
        self._sections = {}
        ifd = open(filename, "r")
        section = None
        key = None
        val = None
        for line in ifd:
            line = line.rstrip()
            sline = line.lstrip()
            if line != sline:
                # continuation, append to the value
                if key is not None:
                    val += " " + sline
            elif key is not None:
                # end of continuation, store the key/value pair
                if section is not None:
                    self._sections[section][key] = val
                key = None
            if len(sline) == 0 or sline[0] in (';', '#'):
                # empty line or comment line
                pass
            elif line[0] == '[' and line[-1] == ']':
                # new section
                section = line[1:-1]
                self._sections[section] = {}
            else:
                ceq = line.find("=")
                cco = line.find(":")
                if ceq < 0 or (cco < ceq and cco >= 0):
                    ceq = cco
                if ceq >= 0:
                    # key/value pair
                    key = line[0:ceq].rstrip()
                    val = line[ceq + 1:].lstrip()
        # store the last key/value pair
        if section is not None and key is not None:
            self._sections[section][key] = val

    def get(self, section, key):
        """
        Returns the value for the specified key in the specified section.

        @type section: string
        @param section: Name of the section.
        @type key: string
        @param key: Key in the section.
        @rtype: string
        @return: Value for the specified key or empty string if not found.
        """
        if not self._sections.has_key(section):
            return ""
        sdict = self._sections[section]
        if not sdict.has_key(key):
            return ""
        return sdict[key]

    def items(self, section):
        """
        Returns all key/value pairs in the specified section.

        @type section: string
        @param section: Name of the section.
        @rtype: ((key,value)...)
        @return: List of key/value pairs.
        """
        if not self._sections.has_key(section):
            return []
        return self._sections[section].items()


class ApplyAutoprops:
    """
    A class for applying auto-props to a Subversion dump file.
    """

    def __init__(self, inputfilename, outputfilename, configfile):
        """
        Initializes the ApplyAutoprops object.

        @type inputfilename: string
        @param inputfilename: Name of the input dump file.
        @type outputfilename: string
        @param outputfilename: Name of the output dump file.
        @type configfile: string
        @param configfile: Name of the Subversion config file.
        """
        self.configfile = configfile
        self.inputfilename = inputfilename
        self.outputfilename = outputfilename
        self.autoprops = []

    def apply(self):
        """
        Applies the auto-props.
        """
        try:
            self._read_config()
            inDump = SvnDumpFile()
            outDump = SvnDumpFile()
            inDump.open(self.inputfilename)
            inDump.read_next_rev()
            outDump.create_like(self.outputfilename, inDump)
            while inDump.has_revision():
                print("revision %d" % inDump.get_rev_nr())
                outDump.add_rev(inDump.get_rev_props())
                for index in range(0, inDump.get_node_count()):
                    node = inDump.get_node(index)
                    action = node.get_action()
                    if action in ("add", "replace"):
                        self._set_properties(node)
                    elif action == "change" and node.has_properties():
                        self._set_properties(node)
                    outDump.add_node(node)
                inDump.read_next_rev()
            inDump.close()
            outDump.close()
        except Exception as ex:
            print("Error:", ex)
            return 1
        return 0

    def _set_properties(self, node):
        """
        Set the auto-props.

        @type node: SvnDumpNode
        @param node: Node to set the properties on.
        """

        name = node.get_name()
        propkeys = ""
        for regex, properties in self.autoprops:
            if regex.match(name):
                for pname, pval in properties:
                    node.set_property(pname, pval)
                    propkeys += ", " + pname
        if len(propkeys) > 0:
            print("  " + node.get_path())
            print("    set " + propkeys[2:])

    def _read_config(self):
        """
        Reads the auto-props config.
        """
        cfg = SvnConfigParser(self.configfile)
        for key, value in cfg.items("auto-props"):
            regex = self._make_regex(key)
            properties = self._split_properties(value)
            self.autoprops.append((regex, properties))

    def _make_regex(self, expr):
        """
        Convert the apr_fnmatch expression into a regular expression.

        @type expr: string
        @param expr: An apr_fnmatch expression.
        @rtype: re.Regex
        @return: Compiled regular expression.
        """
        replacements = {
            "\\": "\\\\",
            "(": "\\(",
            ")": "\\)",
            "{": "\\{",
            "}": "\\}",
            "|": "\\|",
            "^": "\\^",
            "$": "\\$",
            "+": "\\+",
            ".": "\\.",
            "?": ".",
            "*": ".*",
        }
        rexpr = ""
        for c in expr:
            if c in replacements:
                c = replacements[c]
            rexpr += c
        return re.compile("^%s$" % rexpr)

    def _split_properties(self, propstring):
        """
        Splits the value of a key in the auto-props section.

        @type propstring: string
        @param propstring: A property string.
        @rtype: ((str,str)...)
        @return: Tuple containing property name and value tuples.
        """
        properties = []
        for property in propstring.split(";"):
            namevalue = property.split("=", 1)
            if len(namevalue) == 1:
                namevalue.append("")
            name = namevalue[0].strip()
            value = namevalue[1].strip()
            if value == "" and name in ("svn:executable", "svn:needs-lock"):
                value = "*"
            properties.append((name, value))
        return tuple(properties)


class SVNConfigFile:
    '''
    Determine a default SVN configuration file for the given system type.
    '''

    def __init__(self, envvar=None, pathelements=None, platform=None):
        if platform is None:
            platform = sys.platform

        if platform == 'win32':
            self.envsep = '%'
            self.envstr = lambda: '%s%s%s' % (self.envsep, self.envvar, self.envsep)
            if envvar is None:
                envvar = 'APPDATA'
            if pathelements is None:
                pathelements = ['Subversion', 'config']
        else:
            self.envsep = '$'
            self.envstr = lambda: '%s%s' % (self.envsep, self.envvar)
            if envvar is None:
                envvar = 'HOME'
            if pathelements is None:
                pathelements = ['.subversion', 'config']

        self.envvar = envvar
        self.pathelements = pathelements

    def path(self):
        '''
        System compatible representation of the path (with the environment
        variable expanded.)
        '''
        home = os.environ[self.envvar]
        return os.path.join(home, *self.pathelements)

    def __str__(self):
        '''
        Human readable string representation of the path.
        '''
        return os.path.join(self.envstr(), *self.pathelements)


def svndump_apply_autoprops_cmdline(appname, args):
    """
    Parses the commandline and applies the automatic properties.

    Usage:

        >>> svndump_apply_autoprops_cmdline( sys.argv[0], sys.argv[1:] )

    @type appname: string
    @param appname: Name of the application (used in help text).
    @type args: list( string )
    @param args: Commandline arguments.
    @rtype: integer
    @return: Return code (0 = OK).
    """

    svnconf = SVNConfigFile()

    usage = "usage: %s [options] inputdump outputdump" % appname
    parser = OptionParser(usage=usage, version="%prog " + __version)
    parser.add_option("--config-file",
                      action="store", dest="configfile", default=None,
                      help="Subversion config file (default: %s)." % (svnconf,))

    (options, args) = parser.parse_args(args)

    if len(args) != 2:
        print("Please specify exactly one input and one output dump file.")
        return 1

    configfile = options.configfile
    if configfile is None:
        configfile = svnconf.path()

    aa = ApplyAutoprops(args[0], args[1], configfile)
    return aa.apply()

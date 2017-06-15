#!/usr/bin/env python
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
from os import mkdir, system, listdir, remove, rmdir
from os.path import isdir, isfile, abspath
import time  # for svn cp bug
import zlib

import svndump
from svndump.node import SvnDumpNode
from svndump.file import SvnDumpFile
from svndump.diff import svndump_diff_cmdline
from svndump.eolfix import svndump_eol_fix_cmdline


def run(cmd):
    print("cmd <%s>" % cmd)
    rc = system(cmd)
    print("rc: %d" % rc)
    return rc


def kill_dir(dir):
    """'rm -rf dir' in python ;-)"""
    if isdir(dir):
        for d in listdir(dir):
            d = dir + "/" + d
            if isdir(d):
                kill_dir(d)
            else:
                remove(d)
        rmdir(dir)


def create_text(type, fileid, revnr):
    """Create some test text."""

    lines = "line A\nline B\nline C\nline D\nline E\n"
    filerevtxt = "file %s rev %d\n" % (fileid, revnr)
    text = lines * 3 + filerevtxt + lines * 3
    if type == "binary":
        text = zlib.compress(text)
    elif type == "broken-eol":
        text = text.replace("B\n", "B\r\n")
        text = text.replace("D\n", "D\r")
    return text


def svn_create_dump_file(filename, fileid, data, reposdir, wcdir):
    """Creates a svn dump file using the svn commandline."""

    print("")
    print("=" * 80)
    print("=== Initialize")
    print("")

    # cleanup first
    kill_dir(reposdir)
    kill_dir(wcdir)

    # create repos
    run("svnadmin create '%s'" % reposdir)

    # create wc
    run("svn co 'file://%s' '%s'" % (reposdir, wcdir))

    # now do the work
    nrev = len(data)
    irev = 1
    revnr = 0
    while irev < nrev:
        rev = data[irev]
        irev = irev + 1
        revnr = revnr + 1
        print("")
        print("=" * 80)
        print("=== Revision %d" % revnr)
        print("")
        if rev.has_key("author"):
            author = rev["author"]
        else:
            author = "t%d" % revnr
        if rev.has_key("log"):
            log = rev["log"]
        else:
            log = 'log for file "%s" rev %d' % (fileid, revnr)
        nodes = rev["nodes"]
        nnode = len(nodes)
        inode = 0
        while inode < nnode:
            nodedata = nodes[inode]
            inode = inode + 1
            action = nodedata["action"]
            kind = nodedata["kind"]
            path = nodedata["path"]
            nodefile = "%s/%s" % (wcdir, path)
            if action == "delete":
                run("svn rm '%s'" % nodefile)
            elif kind == "dir" and action == "replace":
                # replace = rm and add
                run("svn rm '%s'" % nodefile)
                run("svn add --no-auto-props '%s'" % nodefile)
            elif kind == "dir" and action == "add":
                if isdir(nodefile):
                    # allready there, probably copied with parent dir
                    pass
                elif nodedata.has_key("copyfrom"):
                    # copy from repos
                    copyfrom = nodedata["copyfrom"]
                    fromurl = "file://%s/%s" % (reposdir, copyfrom[0])
                    fromrev = copyfrom[1]
                    run("svn cp -r %d '%s' '%s'" %
                        (fromrev, fromurl, nodefile))
                else:
                    run("svn mkdir '%s/%s'" % (wcdir, path))
            elif kind == "file":
                add = False
                if action == "replace":
                    # replace = delete & add
                    add = True
                    run("svn rm '%s'" % nodefile)
                if action == "add" and not isfile(nodefile):
                    # action 'add' and file doesn't exist
                    if nodedata.has_key("copyfrom"):
                        # copy from repos
                        copyfrom = nodedata["copyfrom"]
                        fromurl = "file://%s/%s" % (reposdir, copyfrom[0])
                        fromrev = copyfrom[1]
                        run("svn cp -r %d '%s' '%s'" %
                            (fromrev, fromurl, nodefile))
                        # bug in my svn client ?!?
                        # run( "svn up '%s'" % nodefile )
                        # Philip Martin suggested sleep(1), thanks :)
                        time.sleep(1)
                    else:
                        # it's a normal add
                        add = True
                if nodedata.has_key("text"):
                    # set/modify text
                    print("write text to '%s'" % path)
                    text = create_text(nodedata["text"], fileid, revnr)
                    fileobj = open(nodefile, "wb")
                    fileobj.write(text)
                    fileobj.close()
                if add:
                    run("svn add --no-auto-props '%s'" % nodefile)
            if nodedata.has_key("props"):
                # for each property do a propset or propdel
                props = nodedata["props"]
                for name, value in props.items():
                    if value is None:
                        run("svn pd '%s' '%s'" % (name, nodefile))
                    else:
                        run("svn ps '%s' '%s' '%s'" % \
                            (name, value, nodefile))
        # commit revision
        run("svn ci --username '%s' -m '%s' '%s'" % (author, log, wcdir))
        # update wc
        run("svn up '%s'" % wcdir)

    print("")
    print("=" * 80)
    print("=== Dump")
    print("")

    # dump the repos
    run("svnadmin dump '%s' > '%s'" % (reposdir, filename))

    print("")
    print("=== Done")
    print("=" * 80)
    print("")


def py_create_dump_file(filename, fileid, data, tmpdir):
    """Creates a svn dump file using the python classes."""

    lines = "line A\nline B\nline C\nline D\nline E\n"

    dump = SvnDumpFile()

    rev = data[0]
    revnr = rev["nr"]
    if revnr == 0:
        dump.create_with_rev_0(filename, rev["uuid"], rev["date"])
    else:
        dump.create_with_rev_n(filename, rev["uuid"], revnr)
        revnr = revnr - 1
    nodeprops = {}
    nrev = len(data)
    irev = 1
    while irev < nrev:
        rev = data[irev]
        irev = irev + 1
        revnr = revnr + 1
        print("  rev %d" % revnr)
        revprops = {}
        revprops["svn:date"] = rev["date"]
        if rev.has_key("author"):
            revprops["svn:author"] = rev["author"]
        else:
            revprops["svn:author"] = "t%d" % revnr
        if rev.has_key("log"):
            revprops["svn:log"] = rev["log"]
        else:
            revprops["svn:log"] = 'log for file "%s" rev %d' % \
                                  (fileid, revnr)
        dump.add_rev(revprops)
        nodes = rev["nodes"]
        nnode = len(nodes)
        inode = 0
        while inode < nnode:
            nodedata = nodes[inode]
            inode = inode + 1
            action = nodedata["action"]
            kind = nodedata["kind"]
            path = nodedata["path"]
            print("    %s %s '%s'" % (action, kind, path))
            node = SvnDumpNode(path, action, kind)
            if nodedata.has_key("copyfrom"):
                copyfrom = nodedata["copyfrom"]
                node.set_copy_from(copyfrom[0], copyfrom[1])
            if nodedata.has_key("text"):
                textfile = "%s/text-%d" % (tmpdir, inode)
                filerevtxt = "file %s rev %d\n" % (fileid, revnr)
                text = lines * 3 + filerevtxt + lines * 3
                if nodedata["text"] == "binary":
                    print("gzip !?!?!")
                    text = zlib.compress(text)
                elif nodedata["text"] == "broken-eol":
                    text = text.replace("B\n", "B\r\n")
                    text = text.replace("D\n", "D\r")
                fileobj = open(textfile, "wb")
                fileobj.write(text)
                fileobj.close()
                node.set_text_file(textfile)
            if action == "delete":
                del nodeprops[path]
            elif action == "add" or action == "replace":
                if nodedata.has_key("props"):
                    props = nodedata["props"].copy()
                else:
                    props = {}
                node.set_properties(props)
                nodeprops[path] = props
            elif nodedata.has_key("props"):
                for name, value in nodedata["props"].items():
                    if value is None:
                        del nodeprops[path][name]
                    else:
                        nodeprops[path][name] = value
                node.set_properties(nodeprops[path])
            dump.add_node(node)
    dump.close()


#
# WARNING
#
# svn adds a trailing LF for the property svn:ignore !
# 
data_test1 = [
    {
        "nr": 0,
        "uuid": "11111111-1111-1111-1111-111111111111",
        "date": "2004-01-01T10:00:00.000000Z"
    },
    {
        "date": "2004-01-01T12:00:00.000000Z",
        "nodes": [
            # create a few dirs
            {
                "path": "testdir1",
                "kind": "dir",
                "action": "add",
                "props": {
                    "svn:ignore": "*.tmp\n"
                }
            },
            {
                "path": "testdir2",
                "kind": "dir",
                "action": "add",
                "props": {
                    "svn:ignore": "*.tmp\n",
                    "broken": "false"
                }
            },
            {
                "path": "testdir4",
                "kind": "dir",
                "action": "add"
            },
            {
                "path": "testdir3",
                "kind": "dir",
                "action": "add"
            },
            # add some files to testdir1
            {
                "path": "testdir1/ok1.txt",
                "kind": "file",
                "action": "add",
                "text": "text",
                "props": {
                    "broken": "false",
                    "ok": "true",
                    "test": "true"
                }
            },
            {
                "path": "testdir1/ok2.txt",
                "kind": "file",
                "action": "add",
                "text": "text"
            },
            {
                "path": "testdir1/ok3.txt",
                "kind": "file",
                "action": "add",
                "text": "text",
                "props": {
                    "broken": "false",
                    "ok": "true",
                    "test": "true"
                }
            },
            {
                "path": "testdir1/broken1.txt",
                "kind": "file",
                "action": "add",
                "text": "broken-eol"
            },
            {
                "path": "testdir1/broken2.txt",
                "kind": "file",
                "action": "add",
                "text": "broken-eol",
                "props": {
                    "broken": "true",
                    "test": "true"
                }
            }
        ]
    },
    {
        "date": "2004-01-02T12:00:00.000000Z",
        "nodes": [
            # change text
            {
                "path": "testdir1/ok1.txt",
                "kind": "file",
                "action": "change",
                "text": "text"
            }
        ]
    },
    {
        "date": "2004-01-03T12:00:00.000000Z",
        "nodes": [
            # add property
            {
                "path": "testdir1/ok2.txt",
                "kind": "file",
                "action": "change",
                "props": {
                    "broken": "false"
                }
            }
        ]
    },
    {
        "date": "2004-01-04T12:00:00.000000Z",
        "nodes": [
            # change text
            {
                "path": "testdir1/broken1.txt",
                "kind": "file",
                "action": "change",
                "text": "broken-eol"
            }
        ]
    },
    {
        "date": "2004-01-05T12:00:00.000000Z",
        "nodes": [
            # remove property
            {
                "path": "testdir1/ok3.txt",
                "kind": "file",
                "action": "change",
                "props": {
                    "broken": None
                }
            },
            {
                "path": "testdir1/broken2.txt",
                "kind": "file",
                "action": "change",
                "props": {
                    "broken": None
                }
            }
        ]
    },
    {
        "date": "2004-01-06T12:00:00.000000Z",
        "nodes": [
            # replace a file
            {
                "path": "testdir1/ok3.txt",
                "kind": "file",
                "action": "replace",
                "text": "text",
                "props": {
                    "broken": "false"
                }
            }
        ]
    },
    {
        "date": "2004-01-07T12:00:00.000000Z",
        "nodes": [
            # copy a file
            {
                "path": "testdir2/ok1.txt",
                "kind": "file",
                "action": "add",
                "copyfrom": ["testdir1/ok1.txt", 2]
            }
        ]
    },
    {
        "date": "2004-01-08T12:00:00.000000Z",
        "nodes": [
            # copy and modify a file
            {
                "path": "testdir3/ok1.txt",
                "kind": "file",
                "action": "add",
                "text": "text",
                "copyfrom": ["testdir1/ok1.txt", 3]
            }
        ]
    },
    {
        "date": "2004-01-09T12:00:00.000000Z",
        "nodes": [
            # copy a dir
            {
                "path": "testdir2/subdir1",
                "kind": "dir",
                "action": "add",
                "copyfrom": ["testdir1", 8]
            }
        ]
    }
]


def write_test_file(tmpdir):
    """Just testing py_create_dump_file."""
    filename = tmpdir + "/test.svndmp"
    py_create_dump_file(filename, data, tmpdir)


def test_init():
    """Initialize tests."""

    params = {}

    # setup a few path variables
    tempdir = abspath("testtmp")
    params["tempdir"] = tempdir
    tempfiles = tempdir + "/files"
    params["tempfiles"] = tempfiles
    temprepos = tempdir + "/repos"
    params["temprepos"] = temprepos
    tempwc = tempdir + "/wc"
    params["tempwc"] = tempwc

    # create needed directories
    if not isdir(tempdir):
        mkdir(tempdir)
    if not isdir(tempfiles):
        mkdir(tempfiles)

    # add list for test results
    params["testresult"] = []

    return params


def add_test_result(params, funcname, descr, result):
    """add the result of a test to the testlist in params"""
    params["testresult"].append((funcname, descr, result))


def show_test_results(params):
    """show test results"""

    print("")
    print("=" * 80)
    print("")
    print("Test Results:")
    for t in params["testresult"]:
        funcname = t[0]
        descr = t[1]
        result = t[2]
        if result == 0:
            restxt = "OK    "
        else:
            restxt = "FAILED"
        name = "%s: %s" % (funcname, descr)
        if len(name) < 40:
            name += " " * (40 - len(name))
        print("  %s %s (%d)" % (name, restxt, result))
    print("")


def test_dumps(params):
    """Test 1: Test creating dumps."""

    # get params
    tempdir = params["tempdir"]
    tempfiles = params["tempfiles"]
    temprepos = params["temprepos"]
    tempwc = params["tempwc"]

    # test1: create a dump with commandline and python classes then compare
    svndmp = tempdir + "/test_dumps_svn"
    pydmp = tempdir + "/test_dumps_py1"
    pydmp2 = tempdir + "/test_dumps_py2"

    # create with cmdline
    svn_create_dump_file(svndmp, "test1", data_test1, temprepos, tempwc)
    # create with python
    py_create_dump_file(pydmp, "test1", data_test1, tempfiles)
    # copy the one created with cmdline
    svndump.copy_dump_file(svndmp, pydmp2)
    # compare svndmp and pydmp2
    rc = run("diff -u '%s' '%s'" % (svndmp, pydmp2))
    add_test_result(params, "test_dumps", "gnu diff svndmp pydmp2", rc)
    if rc != 0:
        print("diffs found :(")
        return 1
    rc = svndump_diff_cmdline("svndumptest.py",
                              [svndmp, pydmp2])
    add_test_result(params, "test_dumps", "diff svndmp pydmp2", rc)
    if rc != 0:
        print("diffs found :(")
        return 1
    # compare svndmp and pydmp
    rc = svndump_diff_cmdline("svndumptest.py",
                              ["-IUUID", "-IRevDate", "-IRevDateStr",
                               "--ignore-revprop=svn:date", svndmp, pydmp])
    add_test_result(params, "test_dumps", "diff svndmp pydmp", rc)
    if rc != 0:
        print("diffs found :(")
        return 1

    # done.
    return 0


def test_eolfix(params):
    """Test 1: Test creating dumps."""

    # get params
    tempdir = params["tempdir"]
    tempfiles = params["tempfiles"]
    temprepos = params["temprepos"]
    tempwc = params["tempwc"]

    # broken and fixed dumps
    broken = tempdir + "/test_eolfix_1"
    fixed = tempdir + "/test_eolfix_2"
    fixed2 = tempdir + "/test_eolfix_2b"

    # create dump
    py_create_dump_file(broken, "eolfix", data_test1, tempfiles)
    # eolfix
    svndump_eol_fix_cmdline("svndumptest.py",
                            ["-mregexp", "-r", "\\.txt$", broken, fixed])
    # compare broken and fixed
    rc = svndump_diff_cmdline("svndumptest.py",
                              ["-e", "-IEOL", "-ITextLen", "-ITextMD5",
                               broken, fixed])
    add_test_result(params, "test_eolfix", "diff broken fixed", rc)
    if rc != 0:
        print("diffs found :(")
        return 1
    # eolfix and add eol-style
    svndump_eol_fix_cmdline("svndumptest.py",
                            ["-mregexp", "-r", "\\.txt$", "-Enative",
                             broken, fixed2])
    # compare broken and fixed
    rc = svndump_diff_cmdline("svndumptest.py",
                              ["-e", "-IEOL", "-ITextLen", "-ITextMD5",
                               "--ignore-property=svn:eol-style",
                               broken, fixed2])
    add_test_result(params, "test_eolfix", "diff broken fixed2", rc)
    if rc != 0:
        print("diffs found :(")
        return 1

    # done.
    return 0


if __name__ == '__main__':

    tests = 255
    if len(sys.argv) > 1:
        tests = int(sys.argv[1])

    params = test_init()
    rc = 0
    if rc == 0 and tests & 1 != 0:
        rc = test_dumps(params)
    if rc == 0 and tests & 2 != 0:
        rc = test_eolfix(params)
    show_test_results(params)

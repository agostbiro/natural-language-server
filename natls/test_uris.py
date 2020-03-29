"""
Original file: https://github.com/palantir/python-language-server/blob/79f3ffe3687785f9ed66e062f1b4a13c01312444/test/test_uris.py

Original license:

The MIT License (MIT)

Copyright 2017 Palantir Technologies, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from unittest import TestCase, skipIf
import platform

from . import uris


class TestUris(TestCase):
    is_windows = platform.system() == 'Windows'
    unix_only = skipIf(is_windows, 'Unix only test')
    windows_only = skipIf(not is_windows, 'Windows only test')

    @unix_only
    def test_to_fs_path(self):
        testees = [
            ('file:///foo/bar#frag', '/foo/bar'),
            ('file:/foo/bar#frag', '/foo/bar'),
            ('file:/foo/space%20%3Fbar#frag', '/foo/space ?bar'),
        ]
        for uri, path in testees:
            self.assertEqual(uris.to_fs_path(uri), path)

    @windows_only
    def test_win_to_fs_path(self):
        testees = [
            ('file:///c:/far/boo', 'c:\\far\\boo'),
            ('file:///C:/far/boo', 'c:\\far\\boo'),
            ('file:///C:/far/space%20%3Fboo', 'c:\\far\\space ?boo'),
        ]
        for uri, path in testees:
            self.assertEqual(uris.to_fs_path(uri), path)

    @unix_only
    def test_from_fs_path(self):
        testees = [
            ('/foo/bar', 'file:///foo/bar'),
            ('/foo/space ?bar', 'file:///foo/space%20%3Fbar')
        ]
        for path, uri in testees:
            self.assertEqual(uris.from_fs_path(path), uri)

    @windows_only
    def test_win_from_fs_path(self):
        testees = [
            ('c:\\far\\boo', 'file:///c:/far/boo'),
            ('C:\\far\\space ?boo', 'file:///c:/far/space%20%3Fboo')
        ]
        for path, uri in testees:
            self.assertEqual(uris.from_fs_path(path), uri)

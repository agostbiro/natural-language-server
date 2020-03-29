"""
Original file: https://github.com/palantir/python-language-server/blob/79f3ffe3687785f9ed66e062f1b4a13c01312444/test/test_utils.py

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

import tempfile
import os
from pathlib import Path
from unittest import TestCase

from . import utils


class TestUtils(TestCase):
    def test_find_parents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rootdir = Path(tmpdir)
            subsubdir = rootdir / 'subdir' / 'subsubdir'
            subsubdir.mkdir(parents=True)
            path = subsubdir / 'path.py'
            path.touch()
            test_cfg = rootdir / 'test.cfg'
            test_cfg.touch()

            res = utils.find_parents(str(rootdir), str(path), ['test.cfg'])
            self.assertListEqual(res, [str(test_cfg)])

    def test_is_process_alive(self):
        self.assertTrue(utils.is_process_alive(os.getpid()))
        # Invalid process id
        self.assertFalse(utils.is_process_alive(-1000))


"""
Original file: https://github.com/palantir/python-language-server/blob/79f3ffe3687785f9ed66e062f1b4a13c01312444/pyls/_utils.py  # noqa 501

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

import logging
import os

log = logging.getLogger(__name__)


def find_parents(root, path, names):
    """Find files matching the given names relative to the given path.

    Args:
        path (str): The file path to start searching up from.
        names (List[str]): The file/directory names to look for.
        root (str): The directory at which to stop recursing upwards.

    Note:
        The path MUST be within the root.
    """
    if not root:
        return []

    if not os.path.commonprefix((root, path)):
        log.warning("Path %s not in %s", path, root)
        return []

    # Split the relative by directory, generate all the parent directories,
    # then check each of them. This avoids running a loop that has different
    # base-cases for unix/windows e.g.
    # /a/b and /a/b/c/d/e.py -> ['/a/b', 'c', 'd']
    reldirs = os.path.relpath(os.path.dirname(path), root).split(os.path.sep)
    dirs = [root] + reldirs

    # Search each of /a/b/c, /a/b, /a
    while dirs:
        search_dir = os.path.join(*dirs)
        existing = list(filter(os.path.exists,
                               [os.path.join(search_dir, n) for n in names]))
        if existing:
            return existing
        dirs.pop()

    # Otherwise nothing
    return []


def is_process_alive(pid):
    """Check whether the process with the given pid is still alive.

    Args:
        pid (int): process ID

    Returns: False if the process is not alive or don't have permission
        to check, True otherwise.
    """
    try:
        os.kill(pid, 0)
    except OSError:
        # no such process or process is already dead
        return False
    else:
        return True

"""A collection of URI utilities with logic built on the VSCode URI library.

https://github.com/Microsoft/vscode-uri/blob/e59cab84f5df6265aed18ae5f43552d3eef13bb9/lib/index.ts

Original file: https://github.com/palantir/python-language-server/blob/79f3ffe3687785f9ed66e062f1b4a13c01312444/pyls/uris.py

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

import os
import re
from urllib import parse


RE_DRIVE_LETTER_PATH = re.compile(r'^\/[a-zA-Z]:')
IS_WIN = os.name == 'nt'


def urlparse(uri):
    """Parse and decode the parts of a URI."""
    scheme, netloc, path, params, query, fragment = parse.urlparse(uri)
    return (
        parse.unquote(scheme),
        parse.unquote(netloc),
        parse.unquote(path),
        parse.unquote(params),
        parse.unquote(query),
        parse.unquote(fragment)
    )


def urlunparse(parts):
    """Unparse and encode parts of a URI."""
    scheme, netloc, path, params, query, fragment = parts

    # Avoid encoding the windows drive letter colon
    if RE_DRIVE_LETTER_PATH.match(path):
        quoted_path = path[:3] + parse.quote(path[3:])
    else:
        quoted_path = parse.quote(path)

    return parse.urlunparse((
        parse.quote(scheme),
        parse.quote(netloc),
        quoted_path,
        parse.quote(params),
        parse.quote(query),
        parse.quote(fragment)
    ))


def to_fs_path(uri):
    """Returns the filesystem path of the given URI.

    Will handle UNC paths and normalize windows drive letters to lower-case. Also
    uses the platform specific path separator. Will *not* validate the path for
    invalid characters and semantics. Will *not* look at the scheme of this URI.
    """
    # scheme://netloc/path;parameters?query#fragment
    scheme, netloc, path, _params, _query, _fragment = urlparse(uri)

    if netloc and path and scheme == 'file':
        # unc path: file://shares/c$/far/boo
        value = "//{}{}".format(netloc, path)

    elif RE_DRIVE_LETTER_PATH.match(path):
        # windows drive letter: file:///C:/far/boo
        value = path[1].lower() + path[2:]

    else:
        # Other path
        value = path

    if IS_WIN:
        value = value.replace('/', '\\')

    return value


def from_fs_path(path):
    """Returns a URI for the given filesystem path."""
    scheme = 'file'
    params, query, fragment = '', '', ''
    path, netloc = _normalize_win_path(path)
    return urlunparse((scheme, netloc, path, params, query, fragment))


def _normalize_win_path(path):
    netloc = ''

    # normalize to fwd-slashes on windows,
    # on other systems bwd-slaches are valid
    # filename character, eg /f\oo/ba\r.txt
    if IS_WIN:
        path = path.replace('\\', '/')

    # check for authority as used in UNC shares
    # or use the path as given
    if path[:2] == '//':
        idx = path.index('/', 2)
        if idx == -1:
            netloc = path[2:]
        else:
            netloc = path[2:idx]
            path = path[idx:]
    else:
        path = path

    # Ensure that path starts with a slash
    # or that it is at least a slash
    if not path.startswith('/'):
        path = '/' + path

    # Normalize drive paths to lower case
    if RE_DRIVE_LETTER_PATH.match(path):
        path = path[0] + path[1].lower() + path[2:]

    return path, netloc

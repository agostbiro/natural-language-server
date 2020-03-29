"""
Original files:
- https://github.com/palantir/python-language-server/blob/79f3ffe3687785f9ed66e062f1b4a13c01312444/test/test_workspace.py
- https://github.com/palantir/python-language-server/blob/79f3ffe3687785f9ed66e062f1b4a13c01312444/test/test_document.py

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

import inspect
import os
import tempfile
import uuid
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

from . import uris
from .workspace import Document, Workspace


class CommonSetup:
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.dir_path = Path(cls.tmpdir.name)

        cls.workspace = Workspace(uris.from_fs_path(str(cls.dir_path)),
                                  MagicMock())

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def setUp(self):
        p = self.dir_path / str(uuid.uuid4())
        p.touch()
        self.doc_uri = uris.from_fs_path(str(p))

        # important added space after last line otherwise cleandoc would remove
        # the last line
        source = """import sys
        
        def main():
            print sys.stdin.read()
         """
        # Strip leading white space up to first char.
        self.doc_source = inspect.cleandoc(source)


class TestDocument(CommonSetup, TestCase):
    def test_document_props(self):
        source = 'foo\nbar\n'
        doc = Document(self.doc_uri, source)
        self.assertEqual(doc.uri, self.doc_uri)
        self.assertEqual(doc.source, source)
        self.assertEqual(len(doc.lines), 2)
        self.assertEqual(doc.lines[1], 'bar\n')

    def test_document_source_unicode(self):
        document_mem = Document(self.doc_uri, u'my source')
        document_disk = Document(self.doc_uri)
        self.assertIsInstance(document_mem.source,
                              type(document_disk.source))

    def test_offset_at_position(self):
        doc = Document(self.doc_uri, self.doc_source)

        self.assertEqual(
            doc.offset_at_position({'line': 0, 'character': 8}), 8)
        self.assertEqual(
            doc.offset_at_position({'line': 1, 'character': 5}), 16)
        self.assertEqual(
            doc.offset_at_position({'line': 2, 'character': 0}), 12)
        self.assertEqual(
            doc.offset_at_position({'line': 2, 'character': 4}), 16)
        # Past end of file
        self.assertEqual(
            doc.offset_at_position({'line': 4, 'character': 0}), 51)

    def test_word_at_position(self):
        # Return the position under the cursor or last in line if past the end
        doc = Document(self.doc_uri, self.doc_source)
        # import sys
        self.assertEqual(doc.word_at_position({'line': 0, 'character': 8}),
                         'sys')
        # Past end of import sys
        self.assertEqual(doc.word_at_position({'line': 0, 'character': 1000}),
                         'sys')
        # Empty line
        self.assertEqual(doc.word_at_position({'line': 1, 'character': 5}),
                         '')
        # def main():
        self.assertEqual(doc.word_at_position({'line': 2, 'character': 0}),
                         'def')
        # Past end of file
        self.assertEqual(doc.word_at_position({'line': 4, 'character': 0}),
                         '')

    def test_document_empty_edit(self):
        doc = Document('file:///uri', u'')
        doc.apply_change({
            'range': {
                'start': {'line': 0, 'character': 0},
                'end': {'line': 0, 'character': 0}
            },
            'text': u'f'
        })
        self.assertEqual(doc.source, u'f')

    def test_document_line_edit(self):
        doc = Document('file:///uri', u'itshelloworld')
        doc.apply_change({
            'text': u'goodbye',
            'range': {
                'start': {'line': 0, 'character': 3},
                'end': {'line': 0, 'character': 8}
            }
        })
        self.assertEqual(doc.source, u'itsgoodbyeworld')

    def test_document_multiline_edit(self):
        old = [
            "def hello(a, b):\n",
            "    print a\n",
            "    print b\n"
        ]
        doc = Document('file:///uri', u''.join(old))
        doc.apply_change({'text': u'print a, b', 'range': {
            'start': {'line': 1, 'character': 4},
            'end': {'line': 2, 'character': 11}
        }})
        self.assertListEqual(doc.lines, [
            "def hello(a, b):\n",
            "    print a, b\n"
        ])

    def test_document_end_of_file_edit(self):
        old = [
            "print 'a'\n",
            "print 'b'\n"
        ]
        doc = Document('file:///uri', u''.join(old))
        doc.apply_change({'text': u'o', 'range': {
            'start': {'line': 2, 'character': 0},
            'end': {'line': 2, 'character': 0}
        }})
        self.assertListEqual(doc.lines, [
            "print 'a'\n",
            "print 'b'\n",
            "o"
        ])


class TestWorkspace(CommonSetup, TestCase):
    def test_local(self):
        # The workspace is a temporary directory
        self.assertTrue(self.workspace.is_local())

    def test_put_document(self):
        self.workspace.put_document(self.doc_uri, 'content')
        assert self.doc_uri in self.workspace._docs

    def test_get_document(self):
        self.workspace.put_document(self.doc_uri, 'TEXT')
        self.assertEqual(
            self.workspace.get_document(self.doc_uri).source,
            'TEXT')

    def test_get_missing_document(self):
        source = 'TEXT'
        doc_path = self.dir_path / 'test_document.py'
        doc_path.write_text(source)
        doc_uri = uris.from_fs_path(str(doc_path))
        self.assertEqual(self.workspace.get_document(doc_uri).source, 'TEXT')

    def test_rm_document(self):
        source = 'TEXT'
        self.workspace.put_document(self.doc_uri, source)
        self.assertEqual(self.workspace.get_document(self.doc_uri)._source,
                         source)
        self.workspace.rm_document(self.doc_uri)
        self.assertEqual(self.workspace.get_document(self.doc_uri)._source,
                         None)

    def test_non_root_project(self):
        repo_root = os.path.join(self.workspace.root_path, 'repo-root')
        os.mkdir(repo_root)
        project_root = os.path.join(repo_root, 'project-root')
        os.mkdir(project_root)

        with open(os.path.join(project_root, 'setup.py'), 'w+') as f:
            f.write('# setup.py')

        test_uri = uris.from_fs_path(os.path.join(project_root,
                                                  'hello/test.py'))
        self.workspace.put_document(test_uri, 'assert True')
        test_doc = self.workspace.get_document(test_uri)
        self.assertIn(project_root, test_doc._extra_sys_path)



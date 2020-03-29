import json
import os
import tempfile
from unittest import TestCase
from threading import Thread, Timer

from .lang_server import start_io_lang_server, start_tcp_lang_server, \
    LanguageServer

from jsonrpc.streams import JsonRpcStreamWriter, JsonRpcStreamReader


class TestLangServer(TestCase):
    timeout_sec = 3

    @classmethod
    def setUpClass(cls):
        server_read, client_write = os.pipe()
        client_read, server_write = os.pipe()
        cls.sreadf = os.fdopen(server_read, 'rb')
        cls.swritef = os.fdopen(server_write, 'wb')
        cls.server = LanguageServer(cls.sreadf, cls.swritef)
        cls.server_thread = Thread(target=lambda s: s.start(),
                                   args=(cls.server,))
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # Send jsonrpc requests to server for testing purposes
        cls.cwritef = os.fdopen(client_write, 'wb')
        cls.writer = JsonRpcStreamWriter(cls.cwritef, indent=2,
                                         sort_keys=True)
        cls.tmpdir = tempfile.TemporaryDirectory()

        # Read jsonrpc requests to server for testing purposes
        cls.creadf = os.fdopen(client_read, 'rb')
        cls.reader = JsonRpcStreamReader(cls.creadf)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.writer.close()
            cls.server.m_shutdown()
            cls.server.m_exit()
        finally:
            # In case exit didn't close them.
            cls.sreadf.close()
            cls.swritef.close()
            cls.creadf.close()
            cls.cwritef.close()
            cls.tmpdir.cleanup()

    def _read_response(self):
        raw_msg = self.reader._read_message()
        return json.loads(raw_msg.decode('utf-8'))

    def test_m_initialize(self):
        message = {
            'jsonrpc': '2.0',
            'method': 'initialize',
            'id': 'test_m_initialize_id',
            'params': {
                'processId': os.getpid(),
                'rootUri': self.tmpdir.name
            }
        }
        self.writer.write(message)
        result = self._read_response()['result']
        self.assertIn('completionProvider', result['capabilities'])

    def test_m_text_document__completion(self):
        message = {
            'jsonrpc': '2.0',
            'method': 'textDocument/completion',
            'id': 'test_m_text_document__completion',
            'params': {
                'textDocument': {
                    'uri': 'placeholder'
                }
            }
        }
        self.writer.write(message)
        result = self._read_response()['result']
        self.assertEqual(len(result['items']), 1)
        item = result['items'][0]
        # Text kind
        self.assertEqual(item['kind'], 1)
        self.assertIsInstance(item['label'], str)


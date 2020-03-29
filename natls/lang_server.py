"""
Original file: https://github.com/palantir/python-language-server/blob/79f3ffe3687785f9ed66e062f1b4a13c01312444/pyls/python_ls.py  # noqa 501

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
import socketserver
import threading
from functools import partial

from jsonrpc.dispatchers import MethodDispatcher
from jsonrpc.endpoint import Endpoint
from jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import constants, lang_model, uris, utils
from .workspace import Workspace

log = logging.getLogger(__name__)


LINT_DEBOUNCE_S = 0.5  # 500 ms
PARENT_PROCESS_WATCH_INTERVAL = 10  # 10 s
MAX_WORKERS = 16


class _StreamHandlerWrapper(socketserver.StreamRequestHandler):
    """A wrapper class that is used to construct a custom handler class."""

    delegate = None

    def setup(self):
        super(_StreamHandlerWrapper, self).setup()
        # pylint: disable=no-member
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)

    def handle(self):
        self.delegate.start()


def start_tcp_lang_server(bind_addr, port, handler_class):
    if not issubclass(handler_class, LanguageServer):
        raise TypeError('Handler class must be a subclass of '
                        'LanguageServer')

    # Construct a custom wrapper class around the user's handler_class
    wrapper_class = type(
        handler_class.__name__ + 'Handler',
        (_StreamHandlerWrapper,),
        {'DELEGATE_CLASS': handler_class}
    )

    server = socketserver.TCPServer((bind_addr, port), wrapper_class)
    try:
        log.info('Serving {} at {}:{}'.format(handler_class.__name__,
                                              bind_addr, port))
        server.serve_forever()
    finally:
        log.info('Shutting down')
        server.server_close()


def start_io_lang_server(rfile, wfile, check_parent_process, handler_class):
    if not issubclass(handler_class, LanguageServer):
        raise TypeError('Handler class must be a subclass of '
                        'LanguageServer')

    log.info('Starting %s in IO mode', handler_class.__name__)
    server = handler_class(rfile, wfile, check_parent_process)
    server.start()


class LanguageServer(MethodDispatcher):
    """Implementation of the Language Server Protocol 2.x for natural language.

    https://github.com/Microsoft/language-server-protocol/blob/master/versions/protocol-2-x.md  # noqa 501
    """

    def __init__(self, rx, tx, check_parent_process=False):
        self.workspace = None

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._check_parent_process = check_parent_process
        self._endpoint = Endpoint(self, self._jsonrpc_stream_writer.write,
                                  max_workers=MAX_WORKERS)
        self._dispatchers = []
        self._shutdown = False

    def start(self):
        """Blocking entry point for the server."""
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def __getitem__(self, item):
        """Override getitem to check for shutdown."""
        if self._shutdown and item != 'exit':
            # exit is the only allowed method during shutdown
            log.debug("Ignoring non-exit method during shutdown: %s", item)
            raise KeyError

        # MethodDispatcher super will find methods prefixed with "m_"
        return super(LanguageServer, self).__getitem__(item)

    def m_shutdown(self, **_kwargs):
        self._shutdown = True
        return None

    def m_exit(self, **_kwargs):
        self._endpoint.shutdown()
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()

    def m_initialize(self, processId=None, rootUri=None, rootPath=None,
                     initializationOptions=None, **_kwargs):
        log.debug('Language server initialized with %s %s %s %s', processId,
                  rootUri, rootPath, initializationOptions)
        if rootUri is None:
            if rootPath is not None:
                rootUri = uris.from_fs_path(rootPath)
            else:
                rootUri = ''

        self.workspace = Workspace(rootUri, self._endpoint)

        lang_model.initialize()

        if self._check_parent_process and processId is not None:
            def watch_parent_process(pid):
                # exist when the given pid is not alive
                if not utils.is_process_alive(pid):
                    log.info("parent process %s is not alive", pid)
                    self.m_exit()
                log.debug("parent process %s is still alive", pid)
                threading.Timer(PARENT_PROCESS_WATCH_INTERVAL,
                                watch_parent_process, args=[pid]).start()

            watching_thread = threading.Thread(target=watch_parent_process,
                                               args=(processId,))
            watching_thread.daemon = True
            watching_thread.start()

        # Get our capabilities
        return {'capabilities': self.capabilities()}

    def m_initialized(self, **_kwargs):
        pass

    def m_text_document__did_close(self, textDocument=None, **_kwargs):
        self.workspace.rm_document(textDocument['uri'])

    def m_text_document__did_open(self, textDocument=None, **_kwargs):
        self.workspace.put_document(textDocument['uri'], textDocument['text'], version=textDocument.get('version'))

    def m_text_document__did_change(self, contentChanges=None, textDocument=None, **_kwargs):
        for change in contentChanges:
            self.workspace.update_document(
                textDocument['uri'],
                change,
                version=textDocument.get('version')
            )

    def m_text_document__did_save(self, textDocument=None, **_kwargs):
        # TODO
        pass

    def m_text_document__completion(self, textDocument=None, position=None,
                                    **_kwargs):
        # If JSONRPC method handler returns a function, it will be invoked
        # asynchronously in a thread pool, which is desirable here to avoid
        # blocking other requests.
        # Workspace and Document are not thread-safe, so access to them must
        # happen outside of the handler function.
        doc = self.workspace.get_document(textDocument['uri'])
        # TODO magic number
        text = doc.read_before(position, 1024)
        last_word = doc.word_at_position(position)
        return partial(self.completions, text, last_word)

    def capabilities(self):
        server_capabilities = {
            'completionProvider': {
                'resolveProvider': False,
                'triggerCharacters': []
            },
            'textDocumentSync': constants.TextDocumentSyncKind.INCREMENTAL
        }
        log.info('Server capabilities: %s', server_capabilities)
        return server_capabilities

    @staticmethod
    def completions(text, last_word):
        complete_text = last_word + ' ' + lang_model.generate(text)
        completions = [{
            'label': complete_text,
            'kind': constants.CompletionItemKind.Text
        }]
        return {
            'isIncomplete': False,
            'items': completions
        }

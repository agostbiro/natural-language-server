"""
Original file: https://github.com/xiaoda99/pytorch-openai-transformer-lm/blob/d515b8ff3b957f788ad9a1690002fc259653cd70/generate.py

Original license:

MIT License

Copyright (c) 2018 OpenAI

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

import random
import logging
import time
from threading import Lock

import numpy as np
import torch

from . import config
from .gpt_lang_model import LMModel, load_openai_pretrained_model
from .text_encoder import TextEncoder


_lock = Lock()
_device = None
_text_encoder = None
_lm_model = None


def _append_batch(X, next_idx):
    next_pos = X[:, -1:, 1] + 1
    next_x = torch.cat((next_idx, next_pos), -1).unsqueeze(1)
    return torch.cat((X, next_x), 1)


def _get_device():
    global _device

    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    return _device


def _get_lang_model():
    global _lm_model

    if _lm_model is None:
        # TODO don't use global logger
        random.seed(config.seed)
        np.random.seed(config.seed)
        torch.manual_seed(config.seed)
        torch.cuda.manual_seed_all(config.seed)

        text_encoder = _get_text_encoder()
        n_ctx = config.n_ctx

        vocab = text_encoder.n_vocab + n_ctx

        _lm_model = LMModel(config, vocab, n_ctx, return_probs=True)
        # n_special is useless for language modelling task
        load_openai_pretrained_model(_lm_model.transformer, n_ctx=n_ctx,
                                     n_special=0)
        _lm_model.to(_get_device())
        _lm_model.eval()

    return _lm_model


def _get_text_encoder():
    global _text_encoder

    if _text_encoder is None:
        _text_encoder = TextEncoder(config.encoder_path, config.bpe_path)

    return _text_encoder


def _make_batch(X, n_vocab, device):
    X = np.array(X)
    assert X.ndim in [1, 2]
    if X.ndim == 1:
        X = np.expand_dims(X, axis=0)
    pos_enc = np.arange(n_vocab, n_vocab + X.shape[-1])
    pos_enc = np.expand_dims(pos_enc, axis=0)
    batch = np.stack([X, pos_enc], axis=-1)
    batch = torch.tensor(batch, dtype=torch.long).to(device)
    return batch


def generate(text):
    log = logging.getLogger(__name__)

    # Multiple threads might access this function and CUDA isn't thread-safe.
    # TODO switch to a LIFO queue
    with _lock:
        text_encoder = _get_text_encoder()
        lm_model = _get_lang_model()

        t0 = time.perf_counter()
        X = text_encoder.encode([text,])
        XMB = _make_batch(X, text_encoder.n_vocab, _get_device())

        tokens = []
        for _ in range(config.gen_len):
            lm_probs = lm_model(XMB)
            next_idx = torch.multinomial(lm_probs[:, -1, :], 1)
            next_token = text_encoder.decoder[next_idx.item()]
            clean_token = next_token.replace('</w>', '')
            tokens.append(clean_token)
            XMB = _append_batch(XMB, next_idx)

        log.info('prediction took {:.2f}'.format(time.perf_counter() - t0))
        return ' '.join(tokens)


def initialize():
    """Initialize the model.

    Meant to be used by external modules to avoid performance penalty on first
    execution.
    """
    with _lock:
        _get_device()
        _get_text_encoder()
        _get_lang_model()

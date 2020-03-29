# From: https://github.com/huggingface/pytorch-openai-transformer-lm/blob/eafc28abdfadfa0732f03a0fc65805c5bfb2ffe7/train.py  # noqa 501

seed = 42
n_iter = 3
n_batch = 8
max_grad_norm = 1
lr = 6.25e-5
lr_warmup = 0.002
n_ctx = 512
n_embd = 768
n_head = 12
n_layer = 12
embd_pdrop = 0.1
attn_pdrop = 0.1
resid_pdrop = 0.1
clf_pdrop = 0.1
l2 = 0.01
vector_l2 = False
opt = 'adam'
afn = 'gelu'
lr_schedule = 'warmup_linear'
# TODO
encoder_path = '/home/abiro/repos/natural-language-server/model/encoder_bpe_40000.json'
bpe_path = '/home/abiro/repos/natural-language-server/model/vocab_40000.bpe'
n_transfer = 12
lm_coef = 0.5
b1 = 0.9
b2 = 0.999
e = 1e-8
n_valid = 374
gen_len = 20
topk = 10

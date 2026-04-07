"""Unit tests for backend-agnostic classification utility paths."""

import numpy as np
import torch

from services.classification_utils import run_chunk_inference, tokenize_message


class _FakeEncoding:
    def __init__(self, ids):
        self.ids = ids


class _FakeTokenizersTokenizer:
    def encode(self, _message, add_special_tokens=False):
        _ = add_special_tokens
        return _FakeEncoding([1, 2, 3])


class _FakeTransformersTokenizer:
    def encode(self, _message, add_special_tokens=False):
        _ = add_special_tokens
        return [4, 5, 6]


class _FakeOnnxSession:
    def run(self, _unused, inputs):
        assert "input_ids" in inputs
        assert "attention_mask" in inputs
        return [np.zeros((1, 7), dtype=np.float32), np.zeros((1, 4), dtype=np.float32)]


class _FakeTorchModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(4, 4)

    def forward(self, input_ids, attention_mask):
        _ = input_ids
        _ = attention_mask
        return torch.zeros((1, 7)), torch.zeros((1, 4))


def test_tokenize_message_supports_tokenizers_encoding():
    ids = tokenize_message(_FakeTokenizersTokenizer(), "hello")
    assert ids == [1, 2, 3]


def test_tokenize_message_supports_transformers_list():
    ids = tokenize_message(_FakeTransformersTokenizer(), "hello")
    assert ids == [4, 5, 6]


def test_run_chunk_inference_onnx_path():
    input_ids = np.array([[101, 1, 2, 102]], dtype=np.int64)
    attention_mask = np.array([[1, 1, 1, 1]], dtype=np.int64)

    cat, sev = run_chunk_inference(_FakeOnnxSession(), input_ids, attention_mask)
    assert cat.shape == (1, 7)
    assert sev.shape == (1, 4)


def test_run_chunk_inference_pytorch_path():
    input_ids = np.array([[101, 1, 2, 102]], dtype=np.int64)
    attention_mask = np.array([[1, 1, 1, 1]], dtype=np.int64)

    model = _FakeTorchModel()
    cat, sev = run_chunk_inference(model, input_ids, attention_mask)
    assert isinstance(cat, np.ndarray)
    assert isinstance(sev, np.ndarray)
    assert cat.shape == (1, 7)
    assert sev.shape == (1, 4)

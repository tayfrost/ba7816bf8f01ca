"""Tests for inference backend selection and startup guards."""

import sys
from pathlib import Path

import pytest
import torch


filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir))

from inference import server as server_module


class _FakeOnnxSession:
    def run(self, *_args, **_kwargs):
        return []


class _FakeTokenizersTokenizer:
    def token_to_id(self, token: str) -> int:
        mapping = {"[CLS]": 101, "[SEP]": 102, "[PAD]": 0}
        return mapping[token]


class _FakeTransformersTokenizer:
    cls_token_id = 101
    sep_token_id = 102
    pad_token_id = 0

    def encode(self, _message, add_special_tokens=False):
        _ = add_special_tokens
        return [200, 201, 202]


class _FakeTorchModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(4, 4)

    def forward(self, input_ids, attention_mask):
        _ = input_ids
        _ = attention_mask
        return torch.zeros((1, 7)), torch.zeros((1, 4))


def test_server_initialises_onnx_backend(monkeypatch):
    monkeypatch.setenv("INFERENCE_BACKEND", "onnx")
    monkeypatch.setenv("ONNX_VARIANT", "dynamic_int8")

    def _fake_load_onnx_model_and_tokenizer(*_args, **kwargs):
        assert kwargs.get("onnx_variant") == "dynamic_int8"
        return _FakeOnnxSession(), _FakeTokenizersTokenizer()

    monkeypatch.setattr(server_module, "load_onnx_model_and_tokenizer", _fake_load_onnx_model_and_tokenizer)

    servicer = server_module.FilterServiceServicer()
    assert servicer.inference_backend == "onnx"
    assert servicer.cls_token_id == 101
    assert servicer.sep_token_id == 102
    assert servicer.pad_token_id == 0


def test_server_initialises_pytorch_backend(monkeypatch):
    monkeypatch.setenv("INFERENCE_BACKEND", "pytorch")

    monkeypatch.setattr(server_module, "load_production_model", lambda: _FakeTorchModel())
    monkeypatch.setattr(
        server_module.AutoTokenizer,
        "from_pretrained",
        lambda *_args, **_kwargs: _FakeTransformersTokenizer(),
    )

    servicer = server_module.FilterServiceServicer()
    assert servicer.inference_backend == "pytorch"
    assert servicer.cls_token_id == 101
    assert servicer.sep_token_id == 102
    assert servicer.pad_token_id == 0


def test_server_raises_when_model_missing(monkeypatch):
    monkeypatch.setenv("INFERENCE_BACKEND", "onnx")
    monkeypatch.setattr(
        server_module,
        "load_onnx_model_and_tokenizer",
        lambda *_args, **_kwargs: (None, _FakeTokenizersTokenizer()),
    )

    with pytest.raises(RuntimeError, match="Inference model failed to load"):
        server_module.FilterServiceServicer()


def test_server_raises_when_tokenizer_missing(monkeypatch):
    monkeypatch.setenv("INFERENCE_BACKEND", "onnx")
    monkeypatch.setattr(
        server_module,
        "load_onnx_model_and_tokenizer",
        lambda *_args, **_kwargs: (_FakeOnnxSession(), None),
    )

    with pytest.raises(RuntimeError, match="Tokenizer failed to load"):
        server_module.FilterServiceServicer()

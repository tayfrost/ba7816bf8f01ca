"""
Classification utilities for message inference.

Helper functions for tokenization, chunking, and inference processing.
"""

import numpy as np
from typing import List, Tuple, Dict


def tokenize_message(tokenizer, message: str) -> List[int]:
    """
    Tokenize message into token IDs.
    
    Args:
        tokenizer: Tokenizer instance
        message: Input text
        
    Returns:
        List of token IDs
    """
    encoding = tokenizer.encode(message, add_special_tokens=False)

    # tokenizers.Tokenizer -> Encoding(ids=...)
    if hasattr(encoding, "ids"):
        return encoding.ids

    # transformers tokenizer -> list[int]
    if isinstance(encoding, list):
        return encoding

    raise TypeError("Unsupported tokenizer encode() return type")


def create_chunks(tokens: List[int], max_length: int, overlap: int) -> List[List[int]]:
    """
    Split tokens into overlapping chunks.
    
    Args:
        tokens: List of token IDs
        max_length: Maximum chunk length (including special tokens)
        overlap: Number of overlapping tokens between chunks
        
    Returns:
        List of token chunks
    """
    chunks = []
    start = 0
    # Reserve space for [CLS] and [SEP] tokens
    chunk_size = max_length - 2

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk = tokens[start:end]
        chunks.append(chunk)

        if end >= len(tokens):
            break
        start += (chunk_size - overlap)

    return chunks


def prepare_chunk_inputs(
    chunk: List[int],
    cls_token_id: int,
    sep_token_id: int,
    pad_token_id: int,
    max_length: int
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Add special tokens and padding to chunk.
    
    Args:
        chunk: Token IDs for chunk
        cls_token_id: [CLS] token ID
        sep_token_id: [SEP] token ID
        pad_token_id: [PAD] token ID
        max_length: Target sequence length
        
    Returns:
        Tuple of (input_ids, attention_mask) as numpy arrays
    """
    # Add special tokens
    input_ids = [cls_token_id] + chunk + [sep_token_id]
    attention_mask = [1] * len(input_ids)

    # Pad to max_length
    padding_length = max_length - len(input_ids)
    input_ids += [pad_token_id] * padding_length
    attention_mask += [0] * padding_length

    # Convert to numpy arrays
    input_ids_array = np.array([input_ids], dtype=np.int64)
    attention_mask_array = np.array([attention_mask], dtype=np.int64)

    return input_ids_array, attention_mask_array


def run_chunk_inference(
    session,
    input_ids: np.ndarray,
    attention_mask: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Run ONNX inference on a single chunk.
    
    Args:
        session: ONNX InferenceSession
        input_ids: Input token IDs
        attention_mask: Attention mask
        
    Returns:
        Tuple of (category_logits, severity_logits)
    """
    # ONNX Runtime path
    if hasattr(session, "run"):
        outputs = session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask
            }
        )
        return outputs[0], outputs[1]

    # PyTorch path
    import torch  # pylint: disable=import-outside-toplevel

    device = next(session.parameters()).device
    input_ids_t = torch.from_numpy(input_ids).to(device)
    attention_mask_t = torch.from_numpy(attention_mask).to(device)

    session.eval()
    with torch.no_grad():
        category_logits, severity_logits = session(input_ids_t, attention_mask_t)

    return category_logits.cpu().numpy(), severity_logits.cpu().numpy()


def softmax(x: np.ndarray) -> np.ndarray:
    """Compute softmax probabilities."""
    exp_x = np.exp(x - np.max(x))
    return exp_x / exp_x.sum()


def process_chunk_predictions(
    category_logits: np.ndarray,
    severity_logits: np.ndarray,
    category_labels: Dict[int, str],
    severity_labels: Dict[int, str],
    risk_categories: set
) -> Dict:
    """
    Convert logits to predictions.
    
    Args:
        category_logits: Category prediction logits
        severity_logits: Severity prediction logits
        category_labels: Mapping of indices to category names
        severity_labels: Mapping of indices to severity names
        risk_categories: Set of category names considered as risks
        
    Returns:
        Dict with keys: category, category_conf, severity, severity_conf, risk_score
    """
    # Get predictions
    category_probs = softmax(category_logits[0])
    severity_probs = softmax(severity_logits[0])

    category_idx = int(np.argmax(category_probs))
    category_conf = float(category_probs[category_idx])
    category_name = category_labels[category_idx]

    severity_idx = int(np.argmax(severity_probs))
    severity_conf = float(severity_probs[severity_idx])
    severity_name = severity_labels[severity_idx]

    # Calculate risk score
    is_risk_category = category_name in risk_categories
    risk_score = category_conf if is_risk_category else 0.0

    return {
        "category": category_name,
        "category_conf": category_conf,
        "severity": severity_name,
        "severity_conf": severity_conf,
        "risk_score": risk_score
    }


def aggregate_chunk_results(
    results: List[Dict],
    threshold: float
) -> Dict:
    """
    Aggregate predictions from multiple chunks.
    
    Args:
        results: List of prediction dicts from each chunk
        threshold: Risk score threshold
        
    Returns:
        Dict with final aggregated predictions
    """
    # Find chunk with highest risk score
    max_result = max(results, key=lambda r: (r["risk_score"], r["category_conf"]))

    # Determine final risk status
    is_risk = max_result["risk_score"] > threshold

    # Build response text
    all_responses = []
    for i, result in enumerate(results):
        response_str = (
            f"[Chunk {i+1}] Category: {result['category']}({result['category_conf']:.3f}), "
            f"Severity: {result['severity']}({result['severity_conf']:.3f}), "
            f"Risk: {result['risk_score']:.3f}"
        )
        all_responses.append(response_str)

    return {
        "category": max_result["category"],
        "category_confidence": max_result["category_conf"],
        "severity": max_result["severity"],
        "severity_confidence": max_result["severity_conf"],
        "is_risk": is_risk,
        "all_responses": " | ".join(all_responses)
    }

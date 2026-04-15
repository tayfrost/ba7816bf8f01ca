"""
Quantize ONNX model to production precision variants.

Creates FP16 and dynamic INT8 quantized versions of the base model.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config

try:
    import onnx
    from onnxruntime.quantization import (
        quantize_dynamic,
        QuantType,
    )
    from onnxconverter_common import float16
except ImportError as e:
    print("Error: Missing required packages. Install with:")
    print("pip install onnx onnxruntime onnxconverter-common")
    raise e


def quantize_to_fp16(
    input_model_path: Path,
    output_model_path: Path
) -> None:
    """
    Quantize model to FP16.

    Args:
        input_model_path: Path to base ONNX model
        output_model_path: Path for FP16 quantized model
    """
    print("\n[FP16] Quantizing to FP16...")
    print(f"[FP16] Input: {input_model_path}")
    print(f"[FP16] Output: {output_model_path}")

    # Load and quantize
    model = onnx.load(str(input_model_path))
    model_fp16 = float16.convert_float_to_float16(model, keep_io_types=True)

    # Save with external data to keep file size small
    onnx.save(
        model_fp16,
        str(output_model_path),
        save_as_external_data=True,
        all_tensors_to_one_file=True,
        location=output_model_path.name + ".data",
        size_threshold=1024,
    )

    # Report size
    original_size = input_model_path.stat().st_size / (1024**2)
    quantized_size = output_model_path.stat().st_size / (1024**2)
    ratio = (quantized_size / original_size) * 100

    print("[FP16] ✓ Complete")
    print(f"[FP16] Original: {original_size:.2f} MB → FP16: {quantized_size:.2f} MB ({ratio:.1f}%)")


def quantize_to_dynamic_int8(
    input_model_path: Path,
    output_model_path: Path
) -> None:
    """
    Quantize model to dynamic INT8.
    
    Dynamic quantization quantizes weights statically and activations dynamically at runtime.
    No calibration data needed.

    Args:
        input_model_path: Path to base ONNX model
        output_model_path: Path for dynamic INT8 quantized model
    """
    print("\n[DYNAMIC INT8] Quantizing to dynamic INT8...")
    print(f"[DYNAMIC INT8] Input: {input_model_path}")
    print(f"[DYNAMIC INT8] Output: {output_model_path}")

    # Load model with external data if present
    model = onnx.load(str(input_model_path), load_external_data=True)

    # Run shape inference to fix any inconsistencies
    print("[DYNAMIC INT8] Running shape inference...")
    model = onnx.shape_inference.infer_shapes(model)

    # Save to temp file without external data for quantization
    temp_path = input_model_path.parent / "temp_inline.onnx"
    onnx.save(model, str(temp_path))

    try:
        quantize_dynamic(
            model_input=str(temp_path),
            model_output=str(output_model_path),
            weight_type=QuantType.QInt8,
        )
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()

    # Report size
    original_size = input_model_path.stat().st_size / (1024**2)
    quantized_size = output_model_path.stat().st_size / (1024**2)
    ratio = (quantized_size / original_size) * 100

    print("[DYNAMIC INT8] ✓ Complete")
    print(f"[DYNAMIC INT8] Original: {original_size:.2f} MB → Dynamic INT8: {quantized_size:.2f} MB ({ratio:.1f}%)")


def main() -> None:
    """Main quantization pipeline."""
    print("="*80)
    print("SentinelAI ONNX Model Quantization")
    print("="*80)

    # Paths
    models_dir = config.MODELS_DIR
    base_model_path = models_dir / config.ONNX_MODEL_FILENAME

    # Check if base model exists
    if not base_model_path.exists():
        print(f"\n[ERROR] Base model not found: {base_model_path}")
        print("[ERROR] Please run export_onnx.py first or specify correct path")
        return

    print(f"\n[INFO] Base model: {base_model_path}")
    print(f"[INFO] Base model size: {base_model_path.stat().st_size / (1024**2):.2f} MB")

    # Output paths
    fp16_path = models_dir / config.ONNX_FP16_MODEL_FILENAME
    dynamic_int8_path = models_dir / config.ONNX_DYNAMIC_INT8_MODEL_FILENAME

    # 1. FP16 Quantization
    try:
        quantize_to_fp16(base_model_path, fp16_path)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"[FP16] ✗ Failed: {e}")

    # 2. Dynamic INT8 Quantization
    try:
        quantize_to_dynamic_int8(base_model_path, dynamic_int8_path)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"[DYNAMIC INT8] ✗ Failed: {e}")

    # Summary
    print("\n" + "="*80)
    print("Quantization Summary")
    print("="*80)

    models = [
        ("Base (FP32)", base_model_path),
        ("FP16", fp16_path),
        ("Dynamic INT8", dynamic_int8_path),
    ]

    for name, path in models:
        if path.exists():
            size_mb = path.stat().st_size / (1024**2)
            print(f"✓ {name:20s} {size_mb:8.2f} MB  {path.name}")
        else:
            print(f"✗ {name:20s} {'N/A':>8s}     {path.name}")

    print("\n[INFO] Quantized models ready for upload to HuggingFace")


if __name__ == "__main__":
    main()

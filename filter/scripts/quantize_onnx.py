"""
Quantize ONNX model to multiple precision formats.

Creates FP16, dynamic INT8, and static INT8 quantized versions of the base model.
Static quantization uses stratified validation data for calibration.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from services.dataset_loader import load_dataset, get_dataset_path

try:
    import onnx
    from onnxruntime.quantization import (
        quantize_dynamic,
        quantize_static,
        QuantType,
        CalibrationDataReader,
    )
    from onnxconverter_common import float16
except ImportError as e:
    print("Error: Missing required packages. Install with:")
    print("pip install onnx onnxruntime onnxconverter-common")
    raise e


class CalibrationDataReaderImpl(CalibrationDataReader):
    """
    Data reader for static quantization calibration.
    
    Provides representative data from validation set to calibrate
    quantization parameters for optimal accuracy.
    """

    def __init__(self, val_loader, max_samples=100):
        """
        Args:
            val_loader: Validation DataLoader
            max_samples: Number of samples to use for calibration
        """
        self.val_loader = val_loader
        self.max_samples = max_samples
        self.data = []

        print(f"[CALIBRATION] Preparing {max_samples} samples from validation set...")

        # Collect calibration data
        sample_count = 0
        for batch in val_loader:
            input_ids = batch["input_ids"].numpy().astype(np.int64)
            attention_mask = batch["attention_mask"].numpy().astype(np.int64)

            # Add each sample individually
            for i in range(input_ids.shape[0]):
                if sample_count >= max_samples:
                    break

                self.data.append({
                    "input_ids": input_ids[i:i+1],
                    "attention_mask": attention_mask[i:i+1]
                })
                sample_count += 1

            if sample_count >= max_samples:
                break

        print(f"[CALIBRATION] Collected {len(self.data)} calibration samples")
        self.iter_index = 0

    def get_next(self):
        """Get next calibration sample."""
        if self.iter_index >= len(self.data):
            return None

        sample = self.data[self.iter_index]
        self.iter_index += 1
        return sample

    def rewind(self):
        """Reset iterator."""
        self.iter_index = 0


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


def quantize_to_static_int8(
    input_model_path: Path,
    output_model_path: Path,
    calibration_reader: CalibrationDataReader
) -> None:
    """
    Quantize model to static INT8.

    Static quantization quantizes both weights and activations using calibration data.
    Provides best performance but requires representative data.

    Args:
        input_model_path: Path to base ONNX model
        output_model_path: Path for static INT8 quantized model
        calibration_reader: Data reader for calibration
    """
    print("\n[STATIC INT8] Quantizing to static INT8...")
    print(f"[STATIC INT8] Input: {input_model_path}")
    print(f"[STATIC INT8] Output: {output_model_path}")
    print("[STATIC INT8] Running quantization with calibration...")

    quantize_static(
        model_input=str(input_model_path),
        model_output=str(output_model_path),
        calibration_data_reader=calibration_reader,
        weight_type=QuantType.QInt8,
    )

    # Report size
    original_size = input_model_path.stat().st_size / (1024**2)
    quantized_size = output_model_path.stat().st_size / (1024**2)
    ratio = (quantized_size / original_size) * 100

    print("[STATIC INT8] ✓ Complete")
    print(f"[STATIC INT8] Original: {original_size:.2f} MB → Static INT8: {quantized_size:.2f} MB ({ratio:.1f}%)")


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
    static_int8_path = models_dir / config.ONNX_STATIC_INT8_MODEL_FILENAME

    # Load validation data for static quantization calibration
    print("\n[DATA] Loading validation dataset for calibration...")
    dataset_path = str(get_dataset_path("sentinelai_dataset_v0.3.json"))

    try:
        _, val_loader, _, _ = load_dataset(
            dataset_path=dataset_path,
            train_split=0.8,
            val_split=0.1,
            max_length=config.MAX_LENGTH,
            seed=config.SEED,
            mix_datasets=False,
        )
        print("[DATA] ✓ Validation data loaded")
    except FileNotFoundError:
        print(f"[ERROR] Dataset not found: {dataset_path}")
        print("[ERROR] Please ensure dataset exists")
        return

    # Create calibration data reader
    calibration_reader = CalibrationDataReaderImpl(val_loader, max_samples=100)

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

    # 3. Static INT8 Quantization
    try:
        quantize_to_static_int8(base_model_path, static_int8_path, calibration_reader)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"[STATIC INT8] ✗ Failed: {e}")

    # Summary
    print("\n" + "="*80)
    print("Quantization Summary")
    print("="*80)

    models = [
        ("Base (FP32)", base_model_path),
        ("FP16", fp16_path),
        ("Dynamic INT8", dynamic_int8_path),
        ("Static INT8", static_int8_path),
    ]

    for name, path in models:
        if path.exists():
            size_mb = path.stat().st_size / (1024**2)
            print(f"✓ {name:20s} {size_mb:8.2f} MB  {path.name}")
        else:
            print(f"✗ {name:20s} {'N/A':>8s}     {path.name}")

    print("\n[INFO] All quantized models ready for upload to HuggingFace")


if __name__ == "__main__":
    main()

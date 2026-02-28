"""
Compile proto files to Python code for gRPC.

Generates filter_pb2.py and filter_pb2_grpc.py in filter/generated directory.
"""

import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROTOS_DIR = PROJECT_ROOT / "protos"
FILTER_DIR = PROJECT_ROOT / "filter"
OUTPUT_DIR = FILTER_DIR / "generated"

# Proto file
PROTO_FILE = PROTOS_DIR / "filter" / "v1" / "filter.proto"


def compile_protos():
    """Compile proto files using grpc_tools.protoc."""
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py files for package structure
    (OUTPUT_DIR / "__init__.py").touch()
    (OUTPUT_DIR / "filter").mkdir(exist_ok=True)
    (OUTPUT_DIR / "filter" / "__init__.py").touch()
    (OUTPUT_DIR / "filter" / "v1").mkdir(exist_ok=True)
    (OUTPUT_DIR / "filter" / "v1" / "__init__.py").touch()
    
    # Compile command
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{PROTOS_DIR}",
        f"--python_out={OUTPUT_DIR}",
        f"--pyi_out={OUTPUT_DIR}",
        f"--grpc_python_out={OUTPUT_DIR}",
        str(PROTO_FILE)
    ]
    
    print(f"Compiling {PROTO_FILE}...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Proto files compiled successfully")
        print(f"  Output: {OUTPUT_DIR}")
        print(f"  Files: filter_pb2.py, filter_pb2_grpc.py")
    else:
        print(f"✗ Compilation failed")
        print(f"Error: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    compile_protos()

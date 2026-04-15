"""Generate gRPC files from proto definitions."""

import subprocess
import sys
from pathlib import Path

def generate_protos():
    """Generate Python gRPC files from proto definitions."""
    project_root = Path(__file__).parent.parent.parent
    webhooks_root = Path(__file__).parent.parent
    protos_dir = project_root / "protos"
    output_dir = webhooks_root / "app"
    
    if not protos_dir.exists():
        print(f"Error: {protos_dir} does not exist")
        sys.exit(1)
    
    cmd = [
        sys.executable,
        "-m", "grpc_tools.protoc",
        f"-I{protos_dir}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        str(protos_dir / "filter" / "v1" / "filter.proto"),
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error generating protos:\n{result.stderr}")
        sys.exit(1)
    
    print("✓ Proto files generated successfully")
    print(f"  Output: {output_dir}")

if __name__ == "__main__":
    generate_protos()
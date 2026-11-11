"""Generate Python and Go contracts without Windows cmd AutoRun corrupting plugin stdout."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

root = Path(__file__).resolve().parents[1]
python_out = root / "voice_ai_service/src/voice_ai_service/app/genproto"
source = "ai_service/v1/ai_service.proto"
with tempfile.TemporaryDirectory() as temp:
    descriptor = Path(temp) / "contract.pb"
    subprocess.run([sys.executable, "-m", "grpc_tools.protoc", f"-I{root / 'proto'}",
        f"--descriptor_set_out={descriptor}", "--include_imports",
        f"--python_out={python_out}", f"--pyi_out={python_out}", f"--grpc_python_out={python_out}", source], check=True)
    files = descriptor_pb2.FileDescriptorSet.FromString(descriptor.read_bytes())
    for name in ("go", "go-grpc"):
        executable = shutil.which(f"protoc-gen-{name}") or str(root / f"tmp/tools/protoc-gen-{name}.exe")
        request = plugin_pb2.CodeGeneratorRequest(file_to_generate=[source], proto_file=files.file,
            parameter="module=maharych-api/src/internal/genproto/aiservicepb")
        result = subprocess.run([executable], input=request.SerializeToString(), capture_output=True, check=True)
        response = plugin_pb2.CodeGeneratorResponse.FromString(result.stdout)
        if response.error:
            raise RuntimeError(response.error)
        for file in response.file:
            (root / "backend/src/internal/genproto/aiservicepb" / file.name).write_text(file.content, encoding="utf-8")
grpc_file = python_out / "ai_service/v1/ai_service_pb2_grpc.py"
grpc_file.write_text(grpc_file.read_text(encoding="utf-8").replace(
    "from ai_service.v1 import", "from voice_ai_service.app.genproto.ai_service.v1 import"), encoding="utf-8")
print("Generated Go and Python interview contracts")

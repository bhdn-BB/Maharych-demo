.PHONY: proto proto-clean

PROTO_DIR := ../proto
PROTO_OUT := src/voice_ai_service/app/genproto

proto:
	@mkdir -p $(PROTO_OUT)/ai_service/v1
	python3.11 -m grpc_tools.protoc \
		--proto_path=$(PROTO_DIR) \
		--python_out=$(PROTO_OUT) \
		--pyi_out=$(PROTO_OUT) \
		--grpc_python_out=$(PROTO_OUT) \
		ai_service/v1/ai_service.proto
	@# Fix relative imports in generated gRPC stub
	@python3.11 -c "from pathlib import Path; p = Path('$(PROTO_OUT)/ai_service/v1/ai_service_pb2_grpc.py'); text = p.read_text(); p.write_text(text.replace('from ai_service.v1 import ai_service_pb2', 'from voice_ai_service.app.genproto.ai_service.v1 import ai_service_pb2'))"
	@# Create __init__.py files for package hierarchy
	@touch $(PROTO_OUT)/__init__.py
	@touch $(PROTO_OUT)/ai_service/__init__.py
	@touch $(PROTO_OUT)/ai_service/v1/__init__.py

proto-clean:
	rm -rf $(PROTO_OUT)

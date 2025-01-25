FROM python:3.13.0-bookworm

RUN apt update
RUN apt install -y protobuf-compiler
RUN python -m pip install mypy-protobuf

ENTRYPOINT ["protoc"]

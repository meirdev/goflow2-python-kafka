# How to compile the `flow.proto` file to use it in python with mypy support

Build the docker image:

```bash
docker build -t protobuf-compiler .
```

Run the docker image from this directory:

```bash
docker run --rm -v $PWD:/app -w /app protobuf-compiler --python_out=. --mypy_out=. ./flow.proto
```

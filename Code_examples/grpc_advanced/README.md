# Advanced permanent async gRPC example

This project demonstrates all four gRPC communication styles:

- Unary: `GetUser`
- Server streaming: `WatchUsers`
- Client streaming: `UploadUsers`
- Bidirectional streaming: `SyncUsers`

The schema uses:
- enum
- nested message (`Address`)
- optional field (`email`)
- repeated field (`roles`)

## 1. Install

With uv:

```bash
uv sync
```

Or with a normal venv:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## 2. Generate protobuf/gRPC Python code

From the project root:

```bash
python -m grpc_tools.protoc       -Iprotos       --python_out=src       --pyi_out=src       --grpc_python_out=src       protos/demo/users/v1/users.proto
```

It will create:

```text
src/demo/users/v1/users_pb2.py
src/demo/users/v1/users_pb2.pyi
src/demo/users/v1/users_pb2_grpc.py
```

## 3. Run

With uv:

```bash
uv run grpc-server
```

In a second terminal:

```bash
uv run grpc-client
```

Or, after `pip install -e .`:

```bash
grpc-server
```

and:

```bash
grpc-client
```

The client intentionally runs forever until Ctrl+C.

## Important client-streaming nuance

`UploadUsers` is `stream request -> one response`.

The server can return that one response only after the client finishes
its request stream. Therefore an *infinite* request iterator would mean
the summary response never arrives.

To keep client-streaming communication permanent, this example repeatedly
opens finite upload batches. True permanently-open two-way communication
is demonstrated by `SyncUsers`.

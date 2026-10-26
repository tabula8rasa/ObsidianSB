import asyncio
import logging
from collections.abc import AsyncIterator

import grpc

from demo.users.v1 import users_pb2
from demo.users.v1 import users_pb2_grpc


TARGET = "localhost:50051"


def build_user(
    user_id: int,
    *,
    source: str,
) -> users_pb2.User:
    return users_pb2.User(
        id=user_id,
        name=f"User {user_id}",
        email=f"user{user_id}@example.com",
        status=users_pb2.USER_STATUS_ACTIVE,
        address=users_pb2.Address(
            country="Georgia",
            city="Tbilisi",
        ),
        roles=[source, "reader"],
    )


async def unary_forever(
    stub: users_pb2_grpc.UserServiceStub,
) -> None:
    while True:
        try:
            response = await stub.GetUser(
                users_pb2.GetUserRequest(user_id=1),
                timeout=3,
            )

            print(
                "[UNARY]",
                response.user.id,
                response.user.name,
                list(response.user.roles),
            )

        except grpc.aio.AioRpcError as error:
            print(
                "[UNARY ERROR]",
                error.code(),
                error.details(),
            )

        await asyncio.sleep(4)


async def watch_users_forever(
    stub: users_pb2_grpc.UserServiceStub,
) -> None:
    while True:
        try:
            call = stub.WatchUsers(
                users_pb2.WatchUsersRequest(
                    include_existing=True
                )
            )

            async for event in call:
                user_id = (
                    event.user.id
                    if event.HasField("user")
                    else "-"
                )

                print(
                    "[SERVER STREAM]",
                    "seq=",
                    event.sequence,
                    "type=",
                    users_pb2.UserEventType.Name(event.type),
                    "user=",
                    user_id,
                    "message=",
                    event.message,
                )

        except grpc.aio.AioRpcError as error:
            print(
                "[SERVER STREAM ERROR]",
                error.code(),
                error.details(),
            )

            await asyncio.sleep(1)


async def one_upload_batch(
    start_id: int,
) -> AsyncIterator[users_pb2.User]:
    for offset in range(3):
        await asyncio.sleep(0.6)

        user = build_user(
            start_id + offset,
            source="client-stream",
        )

        print("[CLIENT STREAM ->]", user.id)
        yield user


async def upload_batches_forever(
    stub: users_pb2_grpc.UserServiceStub,
) -> None:
    next_id = 100

    while True:
        try:
            # A client-streaming RPC returns ONE response.
            # Therefore this request iterator must eventually finish.
            response = await stub.UploadUsers(
                one_upload_batch(next_id)
            )

            print(
                "[CLIENT STREAM <-]",
                "accepted=",
                response.accepted,
                "ids=",
                list(response.user_ids),
            )

            next_id += 3

        except grpc.aio.AioRpcError as error:
            print(
                "[CLIENT STREAM ERROR]",
                error.code(),
                error.details(),
            )

        await asyncio.sleep(5)


async def bidi_commands() -> AsyncIterator[users_pb2.UserCommand]:
    user_id = 1000

    while True:
        await asyncio.sleep(2)

        user = build_user(
            user_id,
            source="bidi",
        )

        command = users_pb2.UserCommand(
            client_id="permanent-client-1",
            user=user,
            note="periodic sync",
        )

        print("[BIDI ->]", user.id)
        yield command

        user_id += 1


async def bidi_forever(
    stub: users_pb2_grpc.UserServiceStub,
) -> None:
    while True:
        try:
            call = stub.SyncUsers(
                bidi_commands()
            )

            async for event in call:
                user_id = (
                    event.user.id
                    if event.HasField("user")
                    else "-"
                )

                print(
                    "[BIDI <-]",
                    "seq=",
                    event.sequence,
                    "type=",
                    users_pb2.UserEventType.Name(event.type),
                    "user=",
                    user_id,
                    "message=",
                    event.message,
                )

        except grpc.aio.AioRpcError as error:
            print(
                "[BIDI ERROR]",
                error.code(),
                error.details(),
            )

            await asyncio.sleep(1)


async def run() -> None:
    async with grpc.aio.insecure_channel(
        TARGET
    ) as channel:
        stub = users_pb2_grpc.UserServiceStub(channel)

        # Four independent application tasks share one gRPC channel.
        # HTTP/2 can multiplex their RPC streams over the connection.
        await asyncio.gather(
            #unary_forever(stub),
            watch_users_forever(stub),
            #upload_batches_forever(stub),
            #bidi_forever(stub),
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nClient stopped")


if __name__ == "__main__":
    main()

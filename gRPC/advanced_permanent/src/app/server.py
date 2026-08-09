import asyncio
import itertools
import logging
from collections.abc import AsyncIterator

import grpc

from demo.users.v1 import users_pb2
from demo.users.v1 import users_pb2_grpc


def clone_user(user: users_pb2.User) -> users_pb2.User:
    copy = users_pb2.User()
    copy.CopyFrom(user)
    return copy


class UserService(users_pb2_grpc.UserServiceServicer):
    def __init__(self) -> None:
        self._users: dict[int, users_pb2.User] = {
            1: users_pb2.User(
                id=1,
                name="Alice",
                email="alice@example.com",
                status=users_pb2.USER_STATUS_ACTIVE,
                address=users_pb2.Address(
                    country="Georgia",
                    city="Tbilisi",
                ),
                roles=["admin", "reader"],
            )
        }

        self._lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[users_pb2.UserEvent]] = set()
        self._sequence = itertools.count(1)

    def _make_event(
        self,
        *,
        event_type: int,
        user: users_pb2.User | None = None,
        message: str = "",
    ) -> users_pb2.UserEvent:
        event = users_pb2.UserEvent(
            sequence=next(self._sequence),
            type=event_type,
            message=message,
        )

        if user is not None:
            event.user.CopyFrom(user)

        return event

    async def _publish(
        self,
        event: users_pb2.UserEvent,
    ) -> None:
        # Queue.put() is awaitable. With an unbounded queue it normally
        # completes immediately, but keeping it async makes the backpressure
        # point explicit if a maxsize is added later.
        for queue in tuple(self._subscribers):
            await queue.put(event)

    async def GetUser(
        self,
        request: users_pb2.GetUserRequest,
        context: grpc.aio.ServicerContext,
    ) -> users_pb2.GetUserResponse:
        async with self._lock:
            user = self._users.get(request.user_id)

            if user is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"user {request.user_id} not found",
                )


        return users_pb2.GetUserResponse(
            user=user
        )

    async def WatchUsers(
        self,
        request: users_pb2.WatchUsersRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[users_pb2.UserEvent]:
        queue: asyncio.Queue[users_pb2.UserEvent] = asyncio.Queue()
        self._subscribers.add(queue)

        logging.info(
            "Watcher connected. watchers=%d",
            len(self._subscribers),
        )

        try:
            if request.include_existing:
                async with self._lock:
                    snapshot = [
                        clone_user(user)
                        for user in self._users.values()
                    ]

                for user in snapshot:
                    yield self._make_event(
                        event_type=users_pb2.USER_EVENT_TYPE_SNAPSHOT,
                        user=user,
                        message="existing user",
                    )

            while True:
                # This suspends only THIS RPC task.
                # Other clients continue to run on the same event loop.
                event = await queue.get()
                yield event

        finally:
            self._subscribers.discard(queue)

            logging.info(
                "Watcher disconnected. watchers=%d",
                len(self._subscribers),
            )

    async def UploadUsers(
        self,
        request_iterator: AsyncIterator[users_pb2.User],
        context: grpc.aio.ServicerContext,
    ) -> users_pb2.UploadUsersResponse:
        accepted_ids: list[int] = []

        async for incoming_user in request_iterator:
            user = clone_user(incoming_user)

            async with self._lock:
                self._users[user.id] = user

            accepted_ids.append(user.id)

            event = self._make_event(
                event_type=users_pb2.USER_EVENT_TYPE_CREATED_OR_UPDATED,
                user=user,
                message="uploaded through client-streaming RPC",
            )

            await self._publish(event)

        # This response is sent only after the client closes the request stream.
        return users_pb2.UploadUsersResponse(
            accepted=len(accepted_ids),
            user_ids=accepted_ids,
        )

    async def SyncUsers(
        self,
        request_iterator: AsyncIterator[users_pb2.UserCommand],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[users_pb2.UserEvent]:
        outgoing: asyncio.Queue[users_pb2.UserEvent] = asyncio.Queue()
        request_stream_finished = asyncio.Event()

        async def read_client_stream() -> None:
            try:
                async for command in request_iterator:
                    user = clone_user(command.user)

                    async with self._lock:
                        self._users[user.id] = user

                    event = self._make_event(
                        event_type=users_pb2.USER_EVENT_TYPE_CREATED_OR_UPDATED,
                        user=user,
                        message=(
                            f"accepted from {command.client_id}: "
                            f"{command.note}"
                        ),
                    )

                    # Send an acknowledgement to this bidi client.
                    await outgoing.put(event)

                    # Also notify all WatchUsers subscribers.
                    await self._publish(event)

            finally:
                request_stream_finished.set()

        async def produce_heartbeats() -> None:
            while not request_stream_finished.is_set():
                await asyncio.sleep(5)

                if request_stream_finished.is_set():
                    break

                await outgoing.put(
                    self._make_event(
                        event_type=users_pb2.USER_EVENT_TYPE_HEARTBEAT,
                        message="server heartbeat",
                    )
                )

        reader_task = asyncio.create_task(
            read_client_stream(),
            name="bidi-reader",
        )

        heartbeat_task = asyncio.create_task(
            produce_heartbeats(),
            name="bidi-heartbeat",
        )

        try:
            while True:
                if request_stream_finished.is_set() and outgoing.empty():
                    break

                # Responses are produced independently from request reading.
                event = await outgoing.get()
                yield event

        finally:
            reader_task.cancel()
            heartbeat_task.cancel()

            await asyncio.gather(
                reader_task,
                heartbeat_task,
                return_exceptions=True,
            )


async def serve() -> None:
    server = grpc.aio.server()

    users_pb2_grpc.add_UserServiceServicer_to_server(
        UserService(),
        server,
    )

    address = "[::]:50051"
    server.add_insecure_port(address)

    logging.info("gRPC server listening on %s", address)

    await server.start()
    await server.wait_for_termination()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    asyncio.run(serve())


if __name__ == "__main__":
    main()

from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UserStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    USER_STATUS_UNSPECIFIED: _ClassVar[UserStatus]
    USER_STATUS_ACTIVE: _ClassVar[UserStatus]
    USER_STATUS_BLOCKED: _ClassVar[UserStatus]

class UserEventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    USER_EVENT_TYPE_UNSPECIFIED: _ClassVar[UserEventType]
    USER_EVENT_TYPE_SNAPSHOT: _ClassVar[UserEventType]
    USER_EVENT_TYPE_CREATED_OR_UPDATED: _ClassVar[UserEventType]
    USER_EVENT_TYPE_HEARTBEAT: _ClassVar[UserEventType]
USER_STATUS_UNSPECIFIED: UserStatus
USER_STATUS_ACTIVE: UserStatus
USER_STATUS_BLOCKED: UserStatus
USER_EVENT_TYPE_UNSPECIFIED: UserEventType
USER_EVENT_TYPE_SNAPSHOT: UserEventType
USER_EVENT_TYPE_CREATED_OR_UPDATED: UserEventType
USER_EVENT_TYPE_HEARTBEAT: UserEventType

class Address(_message.Message):
    __slots__ = ("country", "city")
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    country: str
    city: str
    def __init__(self, country: _Optional[str] = ..., city: _Optional[str] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ("id", "name", "email", "status", "address", "roles")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    email: str
    status: UserStatus
    address: Address
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., email: _Optional[str] = ..., status: _Optional[_Union[UserStatus, str]] = ..., address: _Optional[_Union[Address, _Mapping]] = ..., roles: _Optional[_Iterable[str]] = ...) -> None: ...

class GetUserRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: int
    def __init__(self, user_id: _Optional[int] = ...) -> None: ...

class GetUserResponse(_message.Message):
    __slots__ = ("user",)
    USER_FIELD_NUMBER: _ClassVar[int]
    user: User
    def __init__(self, user: _Optional[_Union[User, _Mapping]] = ...) -> None: ...

class WatchUsersRequest(_message.Message):
    __slots__ = ("include_existing",)
    INCLUDE_EXISTING_FIELD_NUMBER: _ClassVar[int]
    include_existing: bool
    def __init__(self, include_existing: _Optional[bool] = ...) -> None: ...

class UserEvent(_message.Message):
    __slots__ = ("sequence", "type", "user", "message")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    type: UserEventType
    user: User
    message: str
    def __init__(self, sequence: _Optional[int] = ..., type: _Optional[_Union[UserEventType, str]] = ..., user: _Optional[_Union[User, _Mapping]] = ..., message: _Optional[str] = ...) -> None: ...

class UploadUsersResponse(_message.Message):
    __slots__ = ("accepted", "user_ids")
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    USER_IDS_FIELD_NUMBER: _ClassVar[int]
    accepted: int
    user_ids: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, accepted: _Optional[int] = ..., user_ids: _Optional[_Iterable[int]] = ...) -> None: ...

class UserCommand(_message.Message):
    __slots__ = ("client_id", "user", "note")
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    NOTE_FIELD_NUMBER: _ClassVar[int]
    client_id: str
    user: User
    note: str
    def __init__(self, client_id: _Optional[str] = ..., user: _Optional[_Union[User, _Mapping]] = ..., note: _Optional[str] = ...) -> None: ...

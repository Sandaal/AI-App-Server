from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class InvokeRequest(_message.Message):
    __slots__ = ("invocation_id", "route", "handler", "method", "headers", "body", "session_id", "principal", "deadline_unix_ms", "query", "traceparent")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    INVOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    ROUTE_FIELD_NUMBER: _ClassVar[int]
    HANDLER_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    TRACEPARENT_FIELD_NUMBER: _ClassVar[int]
    invocation_id: str
    route: str
    handler: str
    method: str
    headers: _containers.ScalarMap[str, str]
    body: bytes
    session_id: str
    principal: Principal
    deadline_unix_ms: int
    query: str
    traceparent: str
    def __init__(self, invocation_id: _Optional[str] = ..., route: _Optional[str] = ..., handler: _Optional[str] = ..., method: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., body: _Optional[bytes] = ..., session_id: _Optional[str] = ..., principal: _Optional[_Union[Principal, _Mapping]] = ..., deadline_unix_ms: _Optional[int] = ..., query: _Optional[str] = ..., traceparent: _Optional[str] = ...) -> None: ...

class Principal(_message.Message):
    __slots__ = ("subject", "roles", "claims")
    class ClaimsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SUBJECT_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    CLAIMS_FIELD_NUMBER: _ClassVar[int]
    subject: str
    roles: _containers.RepeatedScalarFieldContainer[str]
    claims: _containers.ScalarMap[str, str]
    def __init__(self, subject: _Optional[str] = ..., roles: _Optional[_Iterable[str]] = ..., claims: _Optional[_Mapping[str, str]] = ...) -> None: ...

class InvokeChunk(_message.Message):
    __slots__ = ("start", "data", "end", "error")
    START_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    start: ResponseStart
    data: bytes
    end: ResponseEnd
    error: Error
    def __init__(self, start: _Optional[_Union[ResponseStart, _Mapping]] = ..., data: _Optional[bytes] = ..., end: _Optional[_Union[ResponseEnd, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class ResponseStart(_message.Message):
    __slots__ = ("status", "headers", "streaming")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    STATUS_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    STREAMING_FIELD_NUMBER: _ClassVar[int]
    status: int
    headers: _containers.ScalarMap[str, str]
    streaming: bool
    def __init__(self, status: _Optional[int] = ..., headers: _Optional[_Mapping[str, str]] = ..., streaming: _Optional[bool] = ...) -> None: ...

class ResponseEnd(_message.Message):
    __slots__ = ("metadata",)
    METADATA_FIELD_NUMBER: _ClassVar[int]
    metadata: _struct_pb2.Struct
    def __init__(self, metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("code", "message", "retryable")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RETRYABLE_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    retryable: bool
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., retryable: _Optional[bool] = ...) -> None: ...

class HealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthResponse(_message.Message):
    __slots__ = ("ready", "in_flight")
    READY_FIELD_NUMBER: _ClassVar[int]
    IN_FLIGHT_FIELD_NUMBER: _ClassVar[int]
    ready: bool
    in_flight: int
    def __init__(self, ready: _Optional[bool] = ..., in_flight: _Optional[int] = ...) -> None: ...

class DrainRequest(_message.Message):
    __slots__ = ("grace_seconds",)
    GRACE_SECONDS_FIELD_NUMBER: _ClassVar[int]
    grace_seconds: int
    def __init__(self, grace_seconds: _Optional[int] = ...) -> None: ...

class DrainResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class RegisterRequest(_message.Message):
    __slots__ = ("app", "app_version", "worker_id", "runtime", "sdk_version")
    APP_FIELD_NUMBER: _ClassVar[int]
    APP_VERSION_FIELD_NUMBER: _ClassVar[int]
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    RUNTIME_FIELD_NUMBER: _ClassVar[int]
    SDK_VERSION_FIELD_NUMBER: _ClassVar[int]
    app: str
    app_version: str
    worker_id: str
    runtime: str
    sdk_version: str
    def __init__(self, app: _Optional[str] = ..., app_version: _Optional[str] = ..., worker_id: _Optional[str] = ..., runtime: _Optional[str] = ..., sdk_version: _Optional[str] = ...) -> None: ...

class RegisterResponse(_message.Message):
    __slots__ = ("session_token",)
    SESSION_TOKEN_FIELD_NUMBER: _ClassVar[int]
    session_token: str
    def __init__(self, session_token: _Optional[str] = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("role", "content", "name", "tool_calls", "tool_call_id", "images")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALLS_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    name: str
    tool_calls: _containers.RepeatedCompositeFieldContainer[ToolCallMsg]
    tool_call_id: str
    images: _containers.RepeatedCompositeFieldContainer[ImagePart]
    def __init__(self, role: _Optional[str] = ..., content: _Optional[str] = ..., name: _Optional[str] = ..., tool_calls: _Optional[_Iterable[_Union[ToolCallMsg, _Mapping]]] = ..., tool_call_id: _Optional[str] = ..., images: _Optional[_Iterable[_Union[ImagePart, _Mapping]]] = ...) -> None: ...

class ImagePart(_message.Message):
    __slots__ = ("mime_type", "data")
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    mime_type: str
    data: bytes
    def __init__(self, mime_type: _Optional[str] = ..., data: _Optional[bytes] = ...) -> None: ...

class ToolCallMsg(_message.Message):
    __slots__ = ("id", "name", "arguments_json")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_JSON_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    arguments_json: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., arguments_json: _Optional[str] = ...) -> None: ...

class ToolDef(_message.Message):
    __slots__ = ("name", "description", "parameters_json")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_JSON_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    parameters_json: str
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., parameters_json: _Optional[str] = ...) -> None: ...

class ChatRequest(_message.Message):
    __slots__ = ("invocation_id", "model", "messages", "options", "tools")
    INVOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    invocation_id: str
    model: str
    messages: _containers.RepeatedCompositeFieldContainer[ChatMessage]
    options: _struct_pb2.Struct
    tools: _containers.RepeatedCompositeFieldContainer[ToolDef]
    def __init__(self, invocation_id: _Optional[str] = ..., model: _Optional[str] = ..., messages: _Optional[_Iterable[_Union[ChatMessage, _Mapping]]] = ..., options: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., tools: _Optional[_Iterable[_Union[ToolDef, _Mapping]]] = ...) -> None: ...

class ChatChunk(_message.Message):
    __slots__ = ("delta", "tool_call", "usage", "error")
    DELTA_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    delta: str
    tool_call: ToolCallMsg
    usage: Usage
    error: Error
    def __init__(self, delta: _Optional[str] = ..., tool_call: _Optional[_Union[ToolCallMsg, _Mapping]] = ..., usage: _Optional[_Union[Usage, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class Usage(_message.Message):
    __slots__ = ("input_tokens", "output_tokens", "provider", "resolved_model", "cost_usd")
    INPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    RESOLVED_MODEL_FIELD_NUMBER: _ClassVar[int]
    COST_USD_FIELD_NUMBER: _ClassVar[int]
    input_tokens: int
    output_tokens: int
    provider: str
    resolved_model: str
    cost_usd: float
    def __init__(self, input_tokens: _Optional[int] = ..., output_tokens: _Optional[int] = ..., provider: _Optional[str] = ..., resolved_model: _Optional[str] = ..., cost_usd: _Optional[float] = ...) -> None: ...

class EmbedRequest(_message.Message):
    __slots__ = ("invocation_id", "model", "inputs")
    INVOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    invocation_id: str
    model: str
    inputs: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, invocation_id: _Optional[str] = ..., model: _Optional[str] = ..., inputs: _Optional[_Iterable[str]] = ...) -> None: ...

class EmbedResponse(_message.Message):
    __slots__ = ("vectors", "usage")
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    vectors: _containers.RepeatedCompositeFieldContainer[Vector]
    usage: Usage
    def __init__(self, vectors: _Optional[_Iterable[_Union[Vector, _Mapping]]] = ..., usage: _Optional[_Union[Usage, _Mapping]] = ...) -> None: ...

class Vector(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class TranscribeRequest(_message.Message):
    __slots__ = ("invocation_id", "model", "audio", "filename", "mime_type", "language", "prompt")
    INVOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    invocation_id: str
    model: str
    audio: bytes
    filename: str
    mime_type: str
    language: str
    prompt: str
    def __init__(self, invocation_id: _Optional[str] = ..., model: _Optional[str] = ..., audio: _Optional[bytes] = ..., filename: _Optional[str] = ..., mime_type: _Optional[str] = ..., language: _Optional[str] = ..., prompt: _Optional[str] = ...) -> None: ...

class TranscribeSegment(_message.Message):
    __slots__ = ("start", "end", "text")
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    start: float
    end: float
    text: str
    def __init__(self, start: _Optional[float] = ..., end: _Optional[float] = ..., text: _Optional[str] = ...) -> None: ...

class TranscribeResponse(_message.Message):
    __slots__ = ("text", "language", "duration_seconds", "segments", "usage")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    text: str
    language: str
    duration_seconds: float
    segments: _containers.RepeatedCompositeFieldContainer[TranscribeSegment]
    usage: Usage
    def __init__(self, text: _Optional[str] = ..., language: _Optional[str] = ..., duration_seconds: _Optional[float] = ..., segments: _Optional[_Iterable[_Union[TranscribeSegment, _Mapping]]] = ..., usage: _Optional[_Union[Usage, _Mapping]] = ...) -> None: ...

class KVGetRequest(_message.Message):
    __slots__ = ("namespace", "key")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    key: str
    def __init__(self, namespace: _Optional[str] = ..., key: _Optional[str] = ...) -> None: ...

class KVGetResponse(_message.Message):
    __slots__ = ("found", "value")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    found: bool
    value: bytes
    def __init__(self, found: _Optional[bool] = ..., value: _Optional[bytes] = ...) -> None: ...

class KVPutRequest(_message.Message):
    __slots__ = ("namespace", "key", "value", "ttl_seconds")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    key: str
    value: bytes
    ttl_seconds: int
    def __init__(self, namespace: _Optional[str] = ..., key: _Optional[str] = ..., value: _Optional[bytes] = ..., ttl_seconds: _Optional[int] = ...) -> None: ...

class KVPutResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class KVDeleteRequest(_message.Message):
    __slots__ = ("namespace", "key")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    key: str
    def __init__(self, namespace: _Optional[str] = ..., key: _Optional[str] = ...) -> None: ...

class KVDeleteResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class KVOpRequest(_message.Message):
    __slots__ = ("namespace", "key", "op", "fields", "values", "scores", "value", "expected", "expect_absent", "delete_value", "start", "stop", "count", "offset", "min", "max", "delta", "reverse", "ttl_ms", "owner", "token")
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    SCORES_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_FIELD_NUMBER: _ClassVar[int]
    EXPECT_ABSENT_FIELD_NUMBER: _ClassVar[int]
    DELETE_VALUE_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    STOP_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    MIN_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    DELTA_FIELD_NUMBER: _ClassVar[int]
    REVERSE_FIELD_NUMBER: _ClassVar[int]
    TTL_MS_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    namespace: str
    key: str
    op: str
    fields: _containers.RepeatedScalarFieldContainer[str]
    values: _containers.RepeatedScalarFieldContainer[bytes]
    scores: _containers.RepeatedScalarFieldContainer[float]
    value: bytes
    expected: bytes
    expect_absent: bool
    delete_value: bool
    start: int
    stop: int
    count: int
    offset: int
    min: float
    max: float
    delta: float
    reverse: bool
    ttl_ms: int
    owner: str
    token: int
    def __init__(self, namespace: _Optional[str] = ..., key: _Optional[str] = ..., op: _Optional[str] = ..., fields: _Optional[_Iterable[str]] = ..., values: _Optional[_Iterable[bytes]] = ..., scores: _Optional[_Iterable[float]] = ..., value: _Optional[bytes] = ..., expected: _Optional[bytes] = ..., expect_absent: _Optional[bool] = ..., delete_value: _Optional[bool] = ..., start: _Optional[int] = ..., stop: _Optional[int] = ..., count: _Optional[int] = ..., offset: _Optional[int] = ..., min: _Optional[float] = ..., max: _Optional[float] = ..., delta: _Optional[float] = ..., reverse: _Optional[bool] = ..., ttl_ms: _Optional[int] = ..., owner: _Optional[str] = ..., token: _Optional[int] = ...) -> None: ...

class KVOpResponse(_message.Message):
    __slots__ = ("ok", "n", "score", "value", "fields", "values", "scores", "text")
    OK_FIELD_NUMBER: _ClassVar[int]
    N_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    SCORES_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    ok: bool
    n: int
    score: float
    value: bytes
    fields: _containers.RepeatedScalarFieldContainer[str]
    values: _containers.RepeatedScalarFieldContainer[bytes]
    scores: _containers.RepeatedScalarFieldContainer[float]
    text: str
    def __init__(self, ok: _Optional[bool] = ..., n: _Optional[int] = ..., score: _Optional[float] = ..., value: _Optional[bytes] = ..., fields: _Optional[_Iterable[str]] = ..., values: _Optional[_Iterable[bytes]] = ..., scores: _Optional[_Iterable[float]] = ..., text: _Optional[str] = ...) -> None: ...

class SQLRequest(_message.Message):
    __slots__ = ("database", "query", "schema")
    DATABASE_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_FIELD_NUMBER: _ClassVar[int]
    database: str
    query: str
    schema: bool
    def __init__(self, database: _Optional[str] = ..., query: _Optional[str] = ..., schema: _Optional[bool] = ...) -> None: ...

class SQLResponse(_message.Message):
    __slots__ = ("columns", "rows_json", "truncated", "schema_json")
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    ROWS_JSON_FIELD_NUMBER: _ClassVar[int]
    TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_JSON_FIELD_NUMBER: _ClassVar[int]
    columns: _containers.RepeatedScalarFieldContainer[str]
    rows_json: str
    truncated: bool
    schema_json: str
    def __init__(self, columns: _Optional[_Iterable[str]] = ..., rows_json: _Optional[str] = ..., truncated: _Optional[bool] = ..., schema_json: _Optional[str] = ...) -> None: ...

class EventRecord(_message.Message):
    __slots__ = ("offset", "time_unix_ms", "key", "headers", "value")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    TIME_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    offset: int
    time_unix_ms: int
    key: str
    headers: _containers.ScalarMap[str, str]
    value: bytes
    def __init__(self, offset: _Optional[int] = ..., time_unix_ms: _Optional[int] = ..., key: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., value: _Optional[bytes] = ...) -> None: ...

class EventPublishRequest(_message.Message):
    __slots__ = ("topic", "records")
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    RECORDS_FIELD_NUMBER: _ClassVar[int]
    topic: str
    records: _containers.RepeatedCompositeFieldContainer[EventRecord]
    def __init__(self, topic: _Optional[str] = ..., records: _Optional[_Iterable[_Union[EventRecord, _Mapping]]] = ...) -> None: ...

class EventPublishResponse(_message.Message):
    __slots__ = ("first_offset", "count")
    FIRST_OFFSET_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    first_offset: int
    count: int
    def __init__(self, first_offset: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class EventReadRequest(_message.Message):
    __slots__ = ("topic", "from_offset", "from_time_unix_ms", "consumer", "limit", "wait_ms", "from_end", "member", "partition")
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    FROM_OFFSET_FIELD_NUMBER: _ClassVar[int]
    FROM_TIME_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    CONSUMER_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    WAIT_MS_FIELD_NUMBER: _ClassVar[int]
    FROM_END_FIELD_NUMBER: _ClassVar[int]
    MEMBER_FIELD_NUMBER: _ClassVar[int]
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    topic: str
    from_offset: int
    from_time_unix_ms: int
    consumer: str
    limit: int
    wait_ms: int
    from_end: bool
    member: str
    partition: int
    def __init__(self, topic: _Optional[str] = ..., from_offset: _Optional[int] = ..., from_time_unix_ms: _Optional[int] = ..., consumer: _Optional[str] = ..., limit: _Optional[int] = ..., wait_ms: _Optional[int] = ..., from_end: _Optional[bool] = ..., member: _Optional[str] = ..., partition: _Optional[int] = ...) -> None: ...

class EventReadResponse(_message.Message):
    __slots__ = ("records", "next_offset", "partition", "assigned")
    RECORDS_FIELD_NUMBER: _ClassVar[int]
    NEXT_OFFSET_FIELD_NUMBER: _ClassVar[int]
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    ASSIGNED_FIELD_NUMBER: _ClassVar[int]
    records: _containers.RepeatedCompositeFieldContainer[EventRecord]
    next_offset: int
    partition: int
    assigned: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, records: _Optional[_Iterable[_Union[EventRecord, _Mapping]]] = ..., next_offset: _Optional[int] = ..., partition: _Optional[int] = ..., assigned: _Optional[_Iterable[int]] = ...) -> None: ...

class EventCommitRequest(_message.Message):
    __slots__ = ("topic", "consumer", "next_offset", "partition")
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    CONSUMER_FIELD_NUMBER: _ClassVar[int]
    NEXT_OFFSET_FIELD_NUMBER: _ClassVar[int]
    PARTITION_FIELD_NUMBER: _ClassVar[int]
    topic: str
    consumer: str
    next_offset: int
    partition: int
    def __init__(self, topic: _Optional[str] = ..., consumer: _Optional[str] = ..., next_offset: _Optional[int] = ..., partition: _Optional[int] = ...) -> None: ...

class EventCommitResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VectorSearchRequest(_message.Message):
    __slots__ = ("collection", "query_text", "query_vector", "k", "filter", "mode")
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    QUERY_TEXT_FIELD_NUMBER: _ClassVar[int]
    QUERY_VECTOR_FIELD_NUMBER: _ClassVar[int]
    K_FIELD_NUMBER: _ClassVar[int]
    FILTER_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    collection: str
    query_text: str
    query_vector: Vector
    k: int
    filter: _struct_pb2.Struct
    mode: str
    def __init__(self, collection: _Optional[str] = ..., query_text: _Optional[str] = ..., query_vector: _Optional[_Union[Vector, _Mapping]] = ..., k: _Optional[int] = ..., filter: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., mode: _Optional[str] = ...) -> None: ...

class VectorSearchResponse(_message.Message):
    __slots__ = ("hits",)
    HITS_FIELD_NUMBER: _ClassVar[int]
    hits: _containers.RepeatedCompositeFieldContainer[VectorHit]
    def __init__(self, hits: _Optional[_Iterable[_Union[VectorHit, _Mapping]]] = ...) -> None: ...

class VectorHit(_message.Message):
    __slots__ = ("id", "score", "text", "metadata", "similarity", "keyword")
    ID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    SIMILARITY_FIELD_NUMBER: _ClassVar[int]
    KEYWORD_FIELD_NUMBER: _ClassVar[int]
    id: str
    score: float
    text: str
    metadata: _struct_pb2.Struct
    similarity: float
    keyword: float
    def __init__(self, id: _Optional[str] = ..., score: _Optional[float] = ..., text: _Optional[str] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., similarity: _Optional[float] = ..., keyword: _Optional[float] = ...) -> None: ...

class VectorUpsertRequest(_message.Message):
    __slots__ = ("collection", "records")
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    RECORDS_FIELD_NUMBER: _ClassVar[int]
    collection: str
    records: _containers.RepeatedCompositeFieldContainer[VectorRecord]
    def __init__(self, collection: _Optional[str] = ..., records: _Optional[_Iterable[_Union[VectorRecord, _Mapping]]] = ...) -> None: ...

class VectorRecord(_message.Message):
    __slots__ = ("id", "text", "vector", "metadata")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: str
    text: str
    vector: Vector
    metadata: _struct_pb2.Struct
    def __init__(self, id: _Optional[str] = ..., text: _Optional[str] = ..., vector: _Optional[_Union[Vector, _Mapping]] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class VectorUpsertResponse(_message.Message):
    __slots__ = ("upserted",)
    UPSERTED_FIELD_NUMBER: _ClassVar[int]
    upserted: int
    def __init__(self, upserted: _Optional[int] = ...) -> None: ...

class JobEnqueueRequest(_message.Message):
    __slots__ = ("name", "payload", "delay_ms", "key")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    DELAY_MS_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    name: str
    payload: bytes
    delay_ms: int
    key: str
    def __init__(self, name: _Optional[str] = ..., payload: _Optional[bytes] = ..., delay_ms: _Optional[int] = ..., key: _Optional[str] = ...) -> None: ...

class JobGetRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class JobInfo(_message.Message):
    __slots__ = ("id", "name", "state", "attempts", "max_attempts", "last_error", "result", "created_unix_ms", "run_at_unix_ms")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    MAX_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    LAST_ERROR_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    CREATED_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    RUN_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    state: str
    attempts: int
    max_attempts: int
    last_error: str
    result: bytes
    created_unix_ms: int
    run_at_unix_ms: int
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., state: _Optional[str] = ..., attempts: _Optional[int] = ..., max_attempts: _Optional[int] = ..., last_error: _Optional[str] = ..., result: _Optional[bytes] = ..., created_unix_ms: _Optional[int] = ..., run_at_unix_ms: _Optional[int] = ...) -> None: ...

class ToolListRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ToolListResponse(_message.Message):
    __slots__ = ("tools", "errors")
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    tools: _containers.RepeatedCompositeFieldContainer[ToolDef]
    errors: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, tools: _Optional[_Iterable[_Union[ToolDef, _Mapping]]] = ..., errors: _Optional[_Iterable[str]] = ...) -> None: ...

class ToolCallRequest(_message.Message):
    __slots__ = ("invocation_id", "name", "arguments_json")
    INVOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_JSON_FIELD_NUMBER: _ClassVar[int]
    invocation_id: str
    name: str
    arguments_json: str
    def __init__(self, invocation_id: _Optional[str] = ..., name: _Optional[str] = ..., arguments_json: _Optional[str] = ...) -> None: ...

class ToolCallResponse(_message.Message):
    __slots__ = ("content", "is_error")
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    IS_ERROR_FIELD_NUMBER: _ClassVar[int]
    content: str
    is_error: bool
    def __init__(self, content: _Optional[str] = ..., is_error: _Optional[bool] = ...) -> None: ...

class ApprovalRequestMsg(_message.Message):
    __slots__ = ("job_id", "key", "title", "details_json", "timeout_s")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_JSON_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_S_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    key: str
    title: str
    details_json: str
    timeout_s: int
    def __init__(self, job_id: _Optional[str] = ..., key: _Optional[str] = ..., title: _Optional[str] = ..., details_json: _Optional[str] = ..., timeout_s: _Optional[int] = ...) -> None: ...

class ApprovalInfo(_message.Message):
    __slots__ = ("id", "state", "by", "comment", "expires_unix_ms")
    ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    BY_FIELD_NUMBER: _ClassVar[int]
    COMMENT_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    id: str
    state: str
    by: str
    comment: str
    expires_unix_ms: int
    def __init__(self, id: _Optional[str] = ..., state: _Optional[str] = ..., by: _Optional[str] = ..., comment: _Optional[str] = ..., expires_unix_ms: _Optional[int] = ...) -> None: ...

class LogRequest(_message.Message):
    __slots__ = ("invocation_id", "level", "message", "fields")
    INVOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    invocation_id: str
    level: str
    message: str
    fields: _struct_pb2.Struct
    def __init__(self, invocation_id: _Optional[str] = ..., level: _Optional[str] = ..., message: _Optional[str] = ..., fields: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class LogResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SpanRecord(_message.Message):
    __slots__ = ("trace_id", "span_id", "parent_span_id", "name", "start_unix_nano", "end_unix_nano", "attributes", "error")
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    SPAN_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_SPAN_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    START_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    END_UNIX_NANO_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    trace_id: str
    span_id: str
    parent_span_id: str
    name: str
    start_unix_nano: int
    end_unix_nano: int
    attributes: _struct_pb2.Struct
    error: str
    def __init__(self, trace_id: _Optional[str] = ..., span_id: _Optional[str] = ..., parent_span_id: _Optional[str] = ..., name: _Optional[str] = ..., start_unix_nano: _Optional[int] = ..., end_unix_nano: _Optional[int] = ..., attributes: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class RecordSpansRequest(_message.Message):
    __slots__ = ("invocation_id", "spans")
    INVOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    SPANS_FIELD_NUMBER: _ClassVar[int]
    invocation_id: str
    spans: _containers.RepeatedCompositeFieldContainer[SpanRecord]
    def __init__(self, invocation_id: _Optional[str] = ..., spans: _Optional[_Iterable[_Union[SpanRecord, _Mapping]]] = ...) -> None: ...

class RecordSpansResponse(_message.Message):
    __slots__ = ("recorded",)
    RECORDED_FIELD_NUMBER: _ClassVar[int]
    recorded: int
    def __init__(self, recorded: _Optional[int] = ...) -> None: ...

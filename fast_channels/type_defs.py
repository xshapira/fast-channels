"""Type definitions for fast-channels framework.

This module contains all the type aliases, protocols, and TypedDict classes
used throughout the fast-channels framework for type safety and documentation.
"""

from collections.abc import Awaitable, Callable, Iterable, Mapping, MutableMapping
from re import Pattern
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Protocol,
    TypeAlias,
    TypedDict,
)

if TYPE_CHECKING:
    from .consumer.base import AsyncConsumer  # noqa

# Core channel types
ChannelScope = MutableMapping[str, Any]
"""ASGI scope dictionary containing connection and request metadata."""

ChannelMessage = Mapping[str, Any]
"""Message dictionary passed between channel layers and consumers."""

ChannelHeaders = Iterable[tuple[bytes, bytes]]
"""ASGI-style headers as an iterable of byte string tuples."""


# Channel capacity types
ChannelCapacityPattern: TypeAlias = str | Pattern[str]
"""Pattern used to match channel names for capacity limits. Can be a string or regex pattern."""

ChannelCapacityDict: TypeAlias = dict[ChannelCapacityPattern, int]
"""Dictionary mapping channel patterns to their capacity limits."""

CompiledChannelCapacity: TypeAlias = tuple[Pattern[str], int]
"""Compiled channel capacity entry with regex pattern and limit."""

CompiledChannelCapacities: TypeAlias = list[CompiledChannelCapacity]
"""List of compiled channel capacity entries."""

# ASGI callable types
ASGIReceiveCallable = Callable[[], Awaitable[ChannelMessage]]
"""ASGI receive callable that returns a message from the client."""

ASGISendCallable = Callable[[ChannelMessage], Awaitable[None]]
"""ASGI send callable that sends a message to the client."""


# WebSocket event types
class WebSocketConnectEvent(TypedDict):
    """WebSocket connection initiation event."""

    type: Literal["websocket.connect"]


class WebSocketAcceptEvent(TypedDict):
    """WebSocket connection acceptance event."""

    type: Literal["websocket.accept"]
    subprotocol: str | None
    headers: ChannelHeaders


class WebSocketReceiveEvent(TypedDict):
    """WebSocket message received from client event."""

    type: Literal["websocket.receive"]
    bytes: bytes | None
    text: str | None


class WebSocketCloseEvent(TypedDict):
    """WebSocket close event initiated by server."""

    type: Literal["websocket.close"]
    code: int
    reason: str | None


class WebSocketDisconnectEvent(TypedDict):
    """WebSocket disconnection event from client."""

    type: Literal["websocket.disconnect"]
    code: int
    reason: str | None


# HTTP event types
class HttpRequestEvent(TypedDict, total=False):
    """HTTP request event from client."""

    type: Literal["http.request"]
    body: bytes
    more_body: bool


class HttpResponseStartEvent(TypedDict):
    """HTTP response start event with status and headers."""

    type: Literal["http.response.start"]
    status: int
    headers: list[tuple[bytes, bytes]]


class HttpResponseBodyEvent(TypedDict):
    """HTTP response body event."""

    type: Literal["http.response.body"]
    body: bytes
    more_body: bool


class HttpDisconnectEvent(TypedDict):
    """HTTP disconnection event from client."""

    type: Literal["http.disconnect"]


# ASGI application types
ASGI3Application = Callable[
    [
        ChannelScope,
        ASGIReceiveCallable,
        ASGISendCallable,
    ],
    Awaitable[None],
]
"""ASGI 3.0 application callable signature."""

ASGIApplication = ASGI3Application
"""Alias for ASGI application callable."""


class ASGIApplicationProtocol(Protocol):
    """Protocol for ASGI application wrappers that use consumers."""

    consumer_class: "AsyncConsumer | None"
    """The consumer class to instantiate for handling connections."""

    # Accepts any initialization kwargs passed to the consumer class.
    # Typed as `Any` to allow flexibility in subclass-specific arguments.
    consumer_initkwargs: Any
    """Keyword arguments passed to consumer class initialization."""

    def __call__(
        self, scope: ChannelScope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> Awaitable[None]:
        """Handle an ASGI connection using the consumer class."""
        ...


class MiddlewareProtocol(Protocol):
    """Protocol for ASGI middleware components."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the middleware with any arguments."""
        ...

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        """Process an ASGI connection through the middleware."""
        ...


ChannelApplication: TypeAlias = MiddlewareProtocol | ASGIApplication
"""Type alias for any valid channel application (middleware or ASGI app)."""

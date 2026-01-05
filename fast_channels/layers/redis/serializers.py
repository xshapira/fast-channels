"""Message serialization and encryption for Redis channel layers.

This module provides serializers for encoding/decoding messages sent through
Redis channel layers, with optional symmetric encryption support.
"""

import abc
import base64
import hashlib
import json
import random
from typing import Any

from cryptography.fernet import Fernet, MultiFernet

from .type_defs import SymmetricEncryptionKeys


class SerializerDoesNotExist(KeyError):
    """The requested serializer was not found."""


class BaseMessageSerializer(abc.ABC):
    """Abstract base class for message serializers with optional encryption.

    Provides symmetric encryption capabilities using the Fernet symmetric encryption
    from the cryptography library, along with optional random prefix generation.
    """

    def __init__(
        self,
        symmetric_encryption_keys: SymmetricEncryptionKeys | None = None,
        random_prefix_length: int = 0,
        expiry: int | None = None,
    ):
        """Initialize the serializer with encryption and serialization settings.

        Args:
            symmetric_encryption_keys: List of encryption keys for message encryption.
                If provided, enables encryption/decryption of messages.
            random_prefix_length: Length of random prefix to add to messages.
            expiry: Message expiry time in seconds. If None, messages don't expire.
        """
        self.crypter: MultiFernet | None = None

        self.random_prefix_length = random_prefix_length
        self.expiry = expiry
        # Set up any encryption objects
        self._setup_encryption(symmetric_encryption_keys)

    def _setup_encryption(
        self, symmetric_encryption_keys: SymmetricEncryptionKeys | None
    ) -> None:
        """Initialize encryption with the provided symmetric keys.

        Args:
            symmetric_encryption_keys: List of encryption keys. If None,
                encryption is disabled.

        Raises:
            ValueError: If symmetric_encryption_keys is not a list when provided.
        """
        # See if we can do encryption if they asked
        if symmetric_encryption_keys:
            if isinstance(symmetric_encryption_keys, str | bytes):
                raise ValueError(
                    "symmetric_encryption_keys must be a list of possible keys"
                )
            sub_fernets: list[Fernet] = [
                self.make_fernet(key) for key in symmetric_encryption_keys
            ]
            self.crypter = MultiFernet(sub_fernets)
        else:
            self.crypter = None

    def make_fernet(self, key: str | bytes) -> Fernet:
        """
        Given a single encryption key, returns a Fernet instance using it.
        """
        if isinstance(key, str):
            key = key.encode("utf-8")
        formatted_key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        return Fernet(formatted_key)

    @abc.abstractmethod
    def as_bytes(self, message: Any, *args: Any, **kwargs: Any) -> bytes:
        """Convert a message to bytes.

        Args:
            message: The message to convert.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The message as bytes.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def from_bytes(self, message: bytes, *args: Any, **kwargs: Any) -> Any:
        """Convert bytes back to a message.

        Args:
            message: The bytes to convert.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The decoded message.
        """
        raise NotImplementedError

    def serialize(self, raw_message: Any) -> bytes:
        """
        Serializes message to a byte string.
        """
        message = self.as_bytes(raw_message)
        if self.crypter:
            message = self.crypter.encrypt(message)

        if self.random_prefix_length > 0:
            # provide random prefix
            message = (
                random.getrandbits(8 * self.random_prefix_length).to_bytes(
                    self.random_prefix_length, "big"
                )
                + message
            )
        return message

    def deserialize(self, message: bytes) -> Any:
        """
        Deserializes from a byte string.
        """
        if self.random_prefix_length > 0:
            # Removes the random prefix
            message = message[self.random_prefix_length :]  # noqa: E203

        if self.crypter:
            ttl = self.expiry if self.expiry is None else self.expiry + 10
            message = self.crypter.decrypt(message, ttl)
        return self.from_bytes(message)


class MissingSerializer(BaseMessageSerializer):
    """Placeholder serializer that raises an exception when instantiated.

    Used to indicate that a required serializer dependency is missing.
    """

    exception: Exception | None = None

    def __init__(self, *args: Any, **kwargs: Any):
        """Raise the stored exception to indicate missing dependency."""
        if self.exception:
            raise self.exception

        raise ImportError(
            f"Cannot initialize '{self.__class__.__name__}' because a required "
            "dependency is not installed."
        )

    def as_bytes(self, message: Any, *args: Any, **kwargs: Any) -> bytes:
        """
        Placeholder implementation to satisfy the abstract base class.

        'as_bytes' method is unreachable because __init__ always raises an exception.
        """
        raise NotImplementedError

    def from_bytes(self, message: bytes, *args: Any, **kwargs: Any) -> Any:
        """
        Placeholder implementation to satisfy the abstract base class.

        'from_bytes' method is unreachable because __init__ always raises an exception.
        """
        raise NotImplementedError


class JSONSerializer(BaseMessageSerializer):
    """JSON message serializer using the standard json module.

    Uses UTF-8 encoding for interoperability as recommended by the JSON specification.
    """

    # json module by default always produces str while loads accepts bytes
    # thus we must force bytes conversion
    # we use UTF-8 since it is the recommended encoding for interoperability
    # see https://docs.python.org/3/library/json.html#character-encodings
    def as_bytes(self, raw_message: Any, *args: Any, **kwargs: Any) -> bytes:  # type: ignore[override]
        """Convert message to JSON bytes using UTF-8 encoding.

        Args:
            raw_message: The message to serialize.
            *args: Additional arguments for json.dumps.
            **kwargs: Additional keyword arguments for json.dumps.

        Returns:
            JSON message as UTF-8 encoded bytes.
        """
        message = json.dumps(raw_message, *args, **kwargs)
        return message.encode("utf-8")

    from_bytes = staticmethod(json.loads)  # type: ignore[assignment]


# code ready for a future in which msgpack may become an optional dependency
try:
    import msgpack  # type: ignore[import-untyped]
except ImportError as exc:

    class MsgPackSerializer(MissingSerializer):
        """MessagePack serializer that raises an exception when msgpack is not available."""

        exception = exc

else:

    class MsgPackSerializer(BaseMessageSerializer):  # type: ignore
        """MessagePack serializer using the msgpack library."""

        def as_bytes(self, message: Any, *args: Any, **kwargs: Any) -> bytes:
            """Convert message to bytes using msgpack."""
            return msgpack.packb(message, *args, **kwargs)  # type: ignore

        def from_bytes(self, message: bytes, *args: Any, **kwargs: Any) -> Any:
            """Convert bytes back to message using msgpack."""
            return msgpack.unpackb(message, *args, **kwargs)  # type: ignore


class SerializersRegistry:
    """
    Serializers registry inspired by that of ``django.core.serializers``.
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseMessageSerializer]] = {}

    def register_serializer(
        self, format: str, serializer_class: type[BaseMessageSerializer]
    ) -> None:
        """
        Register a new serializer for given format
        """
        assert isinstance(serializer_class, type) and (
            issubclass(serializer_class, BaseMessageSerializer)
            or (
                hasattr(serializer_class, "serialize")
                and hasattr(serializer_class, "deserialize")
            )
        ), """
            `serializer_class` should be a class which implements `serialize` and `deserialize` method
            or a subclass of `channels_redis.serializers.BaseMessageSerializer`
        """

        self._registry[format] = serializer_class

    def get_serializer(
        self, format: str, *args: Any, **kwargs: Any
    ) -> BaseMessageSerializer:
        """Get a serializer instance for the specified format.

        Args:
            format: The serialization format name.
            *args: Arguments to pass to the serializer constructor.
            **kwargs: Keyword arguments to pass to the serializer constructor.

        Returns:
            An instance of the requested serializer.

        Raises:
            SerializerDoesNotExist: If the format is not registered.
        """
        try:
            serializer_class = self._registry[format]
        except KeyError:
            raise SerializerDoesNotExist(format) from None

        return serializer_class(*args, **kwargs)


registry = SerializersRegistry()
registry.register_serializer("json", JSONSerializer)
registry.register_serializer("msgpack", MsgPackSerializer)  # type: ignore[type-abstract]

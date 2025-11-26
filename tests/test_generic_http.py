from typing import Any

import pytest
from fast_channels.consumer.http import AsyncHttpConsumer
from fast_channels.testing import HttpCommunicator


@pytest.mark.asyncio
async def test_async_http_consumer_basic():
    """
    Tests that AsyncHttpConsumer handles basic HTTP requests correctly.
    """
    results: dict[str, Any] = {}

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            results["body"] = body
            await self.send_response(
                200, b"Hello, World!", headers=[(b"content-type", b"text/plain")]
            )

        async def disconnect(self) -> None:
            results["disconnected"] = True

    app = TestConsumer.as_asgi()

    # Test a normal HTTP request
    communicator = HttpCommunicator(
        app, "/test/", method="GET", body=b"request data"
    )
    await communicator.send_request()
    response = await communicator.get_response()

    assert response["status"] == 200
    assert response["body"] == b"Hello, World!"
    assert (b"content-type", b"text/plain") in response["headers"]
    assert results["body"] == b"request data"
    assert results["disconnected"] is True


@pytest.mark.asyncio
async def test_async_http_consumer_streaming_response():
    """
    Tests that AsyncHttpConsumer can send streaming responses with more_body.
    """

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            await self.send_headers(status=200)
            await self.send_body(b"Part 1", more_body=True)
            await self.send_body(b"Part 2", more_body=True)
            await self.send_body(b"Part 3", more_body=False)

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/")
    await communicator.send_request()
    response = await communicator.get_response()

    assert response["status"] == 200
    assert response["body"] == b"Part 1Part 2Part 3"


@pytest.mark.asyncio
async def test_async_http_consumer_empty_body():
    """
    Tests that AsyncHttpConsumer handles requests with empty body.
    """
    results: dict[str, Any] = {}

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            results["body"] = body
            await self.send_response(204, b"")

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/", method="GET")
    await communicator.send_request()
    response = await communicator.get_response()

    assert response["status"] == 204
    assert results["body"] == b""


@pytest.mark.asyncio
async def test_async_http_consumer_chunked_request():
    """
    Tests that AsyncHttpConsumer accumulates body from multiple chunks.
    """
    results: dict[str, Any] = {}

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            results["body"] = body
            await self.send_response(200, b"OK")

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/", body=b"chunk1")
    # Send first chunk with more_body=True
    await communicator.send_input(
        {"type": "http.request", "body": b"chunk1", "more_body": True}
    )
    # Send second chunk with more_body=True
    await communicator.send_input(
        {"type": "http.request", "body": b"chunk2", "more_body": True}
    )
    # Send final chunk with more_body=False
    await communicator.send_input(
        {"type": "http.request", "body": b"chunk3", "more_body": False}
    )

    response = await communicator.get_response()

    assert response["status"] == 200
    assert results["body"] == b"chunk1chunk2chunk3"


@pytest.mark.asyncio
async def test_async_http_consumer_post_method():
    """
    Tests that AsyncHttpConsumer works with POST requests.
    """
    results: dict[str, Any] = {}

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            results["body"] = body
            results["method"] = self.scope["method"]
            await self.send_response(201, b"Created")

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(
        app, "/test/", method="POST", body=b'{"name": "test"}'
    )
    await communicator.send_request()
    response = await communicator.get_response()

    assert response["status"] == 201
    assert results["method"] == "POST"
    assert results["body"] == b'{"name": "test"}'


@pytest.mark.asyncio
async def test_async_http_consumer_handle_not_implemented():
    """
    Tests that AsyncHttpConsumer raises NotImplementedError if handle() is not overridden.
    """

    class TestConsumer(AsyncHttpConsumer):
        pass

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/")
    await communicator.send_request()

    with pytest.raises(NotImplementedError, match="must provide a handle\\(\\) method"):
        await communicator.get_response()


@pytest.mark.asyncio
async def test_async_http_consumer_disconnect_event():
    """
    Tests that AsyncHttpConsumer handles disconnect events properly.
    """
    results: dict[str, Any] = {}

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            results["handle_called"] = True
            await self.send_response(200, b"OK")

        async def disconnect(self) -> None:
            results["disconnect_called"] = True

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/")
    # Send disconnect event instead of request
    await communicator.send_input({"type": "http.disconnect"})
    await communicator.wait()

    assert "handle_called" not in results
    assert results["disconnect_called"] is True


@pytest.mark.asyncio
async def test_async_http_consumer_custom_headers():
    """
    Tests that AsyncHttpConsumer can send custom headers.
    """

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            headers = [
                (b"content-type", b"application/json"),
                (b"x-custom-header", b"custom-value"),
            ]
            await self.send_response(200, b'{"status": "ok"}', headers=headers)

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/")
    await communicator.send_request()
    response = await communicator.get_response()

    assert response["status"] == 200
    assert (b"content-type", b"application/json") in response["headers"]
    assert (b"x-custom-header", b"custom-value") in response["headers"]


@pytest.mark.asyncio
async def test_async_http_consumer_error_handling():
    """
    Tests that errors in handle() are properly propagated.
    """

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            raise ValueError("Test error")

        async def disconnect(self) -> None:
            pass

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/")
    await communicator.send_request()

    with pytest.raises(ValueError, match="Test error"):
        await communicator.get_response()


@pytest.mark.asyncio
async def test_async_http_consumer_send_body_validation():
    """
    Tests that send_body validates that body is bytes.
    """

    class TestConsumer(AsyncHttpConsumer):
        async def handle(self, body: bytes) -> None:
            await self.send_headers(status=200)
            await self.send_body("not bytes")  # type: ignore

    app = TestConsumer.as_asgi()

    communicator = HttpCommunicator(app, "/test/")
    await communicator.send_request()

    with pytest.raises(AssertionError, match="Body is not bytes"):
        await communicator.get_response()

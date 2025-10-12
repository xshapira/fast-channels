Fast Channels
=============

.. image:: https://img.shields.io/pypi/v/fast-channels
   :target: https://pypi.org/project/fast-channels/
   :alt: PyPI

.. image:: https://codecov.io/github/huynguyengl99/fast-channels/graph/badge.svg
   :target: https://codecov.io/github/huynguyengl99/fast-channels
   :alt: Code Coverage

.. image:: https://github.com/huynguyengl99/fast-channels/actions/workflows/test.yml/badge.svg?branch=main
   :target: https://github.com/huynguyengl99/fast-channels/actions/workflows/test.yml
   :alt: Test

.. image:: https://www.mypy-lang.org/static/mypy_badge.svg
   :target: https://mypy-lang.org/
   :alt: Checked with mypy

.. image:: https://microsoft.github.io/pyright/img/pyright_badge.svg
   :target: https://microsoft.github.io/pyright/
   :alt: Checked with pyright

.. image:: https://fast-channels.readthedocs.io/en/latest/_static/interrogate_badge.svg
   :target: https://github.com/huynguyengl99/fast-channels
   :alt: Docstring

Fast Channels brings Django Channels–style consumers and channel layers to FastAPI, Starlette, and any ASGI-compatible framework for real-time apps.

**What are Channel Layers?**

Channel layers enhance WebSocket functionality by enabling advanced messaging patterns beyond simple request-response:

- **Group Messaging**: Send messages to multiple WebSocket connections simultaneously
- **Cross-Instance Communication**: Send messages from HTTP endpoints, background workers, or other processes
- **Task Distribution**: Use as a basic task queue for offloading work to worker processes
- **Distributed Applications**: Build scalable real-time apps without routing everything through a database

As the `Django Channels documentation <https://channels.readthedocs.io/en/latest/topics/channel_layers.html>`_ explains: *"Channel layers allow you to talk between different instances of an application. They're a useful part of making a distributed realtime application if you don't want to have to shuttle all of your messages or events through a database."*

Fast Channels ports this proven architecture from Django Channels, which has been battle-tested in production environments for years. By leveraging Redis for high-performance, reliable message delivery while maintaining the familiar consumer-based programming model, Fast Channels brings Django's mature WebSocket patterns to the entire ASGI ecosystem.

Features
--------

- **Django Channels-Style Consumers**: Familiar WebSocket consumer patterns with connect, receive, and disconnect methods
- **Channel Layers**: Support for Redis-backed channel layers with group messaging
- **Redis Integration**: Full Redis support with Redis Sentinel for high availability
- **Async/Await Support**: Built from the ground up for modern Python async programming
- **ASGI Compatible**: Seamless integration with FastAPI, Starlette, and any ASGI-compatible framework
- **Testing Framework**: Comprehensive testing utilities for WebSocket consumers
- **Full Type Safety**: Complete type hints with mypy and pyright support
- **Multiple Channel Layer Backends**: In-memory for development, Redis for production

Installation
------------

.. code-block:: bash

    # Basic installation
    pip install fast-channels

    # Recommended: Install with Redis support for production use
    pip install fast-channels[redis]

**Optional Dependencies:**

.. code-block:: bash

    # For Redis channel layer support (recommended for production)
    pip install fast-channels[redis]

**Note:** Additional channel layer backends (such as Kafka) may be supported in future releases.

**Core Dependencies:** Python 3.11+, compatible with any ASGI framework (FastAPI, Starlette, Quart, etc.)

Quick Start
-----------

1. **Set Up Channel Layers**

Create a ``layers.py`` file to configure channel layers:

.. code-block:: python

    # layers.py
    import os
    from fast_channels.layers import (
        InMemoryChannelLayer,
        has_layers,
        register_channel_layer,
    )
    from fast_channels.layers.redis import RedisChannelLayer

    def setup_channel_layers():
        """Set up and register channel layers for the application."""
        # Prevent duplicate registration
        if has_layers():
            return

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Register the default channel layer
        register_channel_layer(
            "default",
            RedisChannelLayer(hosts=[redis_url])
        )

        # Optional: Register additional layers for specific purposes
        # register_channel_layer("memory", InMemoryChannelLayer())

**For detailed setup options and advanced configurations, see the** `Channel Layer Setup Guide <https://fast-channels.readthedocs.io/en/latest/guides/channel-layer-setup.html>`_.

2. **Create WebSocket Consumer**

.. code-block:: python

    # consumer.py
    from fast_channels.consumer.websocket import AsyncWebsocketConsumer

    class ChatConsumer(AsyncWebsocketConsumer):
        groups = ["chat_room"]
        channel_layer_alias = "default"  # Use registered layer

        async def connect(self):
            await self.accept()
            await self.channel_layer.group_send(
                "chat_room",
                {"type": "chat_message", "message": "Someone joined the chat"}
            )

        async def disconnect(self, close_code):
            await self.channel_layer.group_send(
                "chat_room",
                {"type": "chat_message", "message": "Someone left the chat"}
            )

        async def receive(self, text_data=None, bytes_data=None, **kwargs):
            await self.channel_layer.group_send(
                "chat_room",
                {"type": "chat_message", "message": f"Message: {text_data}"}
            )

        async def chat_message(self, event):
            # Send message to WebSocket
            await self.send(event["message"])

3. **Integrate with FastAPI**

.. code-block:: python

    # main.py
    from fastapi import FastAPI
    from .layers import setup_channel_layers
    from .consumer import ChatConsumer

    # Setup layers BEFORE creating the app
    setup_channel_layers()

    app = FastAPI()

    # Create WebSocket sub-app for better organization
    ws_app = FastAPI()
    ws_app.add_websocket_route("/chat", ChatConsumer.as_asgi())

    # Mount WebSocket routes
    app.mount("/ws", ws_app)

That's it! Your real-time WebSocket application with channel layers is ready to use.

Channel Layer Backends
----------------------

**In-Memory (Testing Only)**
   - Fast and simple for unit tests
   - Single-process only - **cannot send messages from workers or HTTP endpoints**
   - No persistence
   - **Use only for testing group chat functionality or running test suites**

**Redis Queue Layer (Production - Reliable)**
   - Message persistence and guaranteed delivery
   - Scalable across multiple processes
   - Configurable expiry and capacity
   - Best for critical messaging

**Redis Pub/Sub Layer (Production - Real-time)**
   - Ultra-low latency messaging
   - Real-time broadcasting
   - No message persistence
   - Best for live chat and notifications

**Configuration Examples:**

.. code-block:: python

    # layers.py
    import os
    from fast_channels.layers import (
        InMemoryChannelLayer,
        has_layers,
        register_channel_layer,
    )
    from fast_channels.layers.redis import (
        RedisChannelLayer,
        RedisPubSubChannelLayer,
    )

    def setup_channel_layers():
        """Set up and register channel layers for the application."""
        if has_layers():
            return

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # In-memory for development/testing
        register_channel_layer("memory", InMemoryChannelLayer())

        # Redis Queue Layer for reliable messaging
        register_channel_layer("reliable", RedisChannelLayer(
            hosts=[redis_url],
            prefix="app_queue",
            capacity=1500,
            expiry=3600,  # 1 hour
        ))

        # Redis Pub/Sub for real-time chat
        register_channel_layer("chat", RedisPubSubChannelLayer(
            hosts=[redis_url],
            prefix="app_chat",
        ))

        # Redis Sentinel for high availability
        register_channel_layer("ha_queue", RedisChannelLayer(
            sentinels=[("localhost", 26379)],
            service_name="mymaster",
            sentinel_kwargs={"password": "sentinel_password"},
            connection_kwargs={"password": "redis_password"},
        ))

**See the** `Channel Layer Setup Guide <https://fast-channels.readthedocs.io/en/latest/guides/channel-layer-setup.html>`_ **for detailed configuration options and best practices.**

Testing
-------

Fast Channels includes comprehensive testing utilities out of the box:

.. code-block:: python

    from fast_channels.testing import WebsocketCommunicator
    import pytest

    @pytest.mark.asyncio
    async def test_chat_consumer():
        communicator = WebsocketCommunicator(ChatConsumer, "/ws/chat/")
        connected, subprotocol = await communicator.connect()
        assert connected

        # Test sending a message
        await communicator.send_json_to({
            "message": "hello world"
        })
        response = await communicator.receive_json_from()
        assert response == {"message": "hello world"}

        await communicator.disconnect()

Documentation
-------------

Please visit `Fast Channels docs <https://fast-channels.readthedocs.io/>`_ for complete documentation, including:

- Detailed consumer patterns
- Advanced channel layer configuration
- Production deployment guides
- Testing best practices
- Migration guides from Django Channels

Comparison with Alternatives
----------------------------

**Fast Channels vs. Native FastAPI/Starlette WebSockets**

Native FastAPI WebSocket support provides basic connection handling but lacks advanced messaging capabilities:

.. code-block:: python

    # Native FastAPI - Limited to direct connections
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        # Can only send/receive to this specific connection
        # No group messaging or cross-process communication

**Fast Channels vs. Broadcaster**

`Broadcaster <https://github.com/encode/broadcaster>`_ is a lightweight pub/sub library, but Fast Channels provides more comprehensive functionality:

+-------------------------+----------------+-------------------+----------------------+
| Feature                 | Native WS      | Broadcaster       | Fast Channels        |
+=========================+================+===================+======================+
| Basic WebSocket         | ✅             | ✅                | ✅                   |
+-------------------------+----------------+-------------------+----------------------+
| Simple Pub/Sub          | ❌             | ✅                | ✅                   |
+-------------------------+----------------+-------------------+----------------------+
| Group Messaging         | ❌             | ✅                | ✅                   |
+-------------------------+----------------+-------------------+----------------------+
| Consumer Pattern        | ❌             | ❌                | ✅                   |
+-------------------------+----------------+-------------------+----------------------+
| Message Persistence     | ❌             | ❌                | ✅ (Redis Queue)     |
+-------------------------+----------------+-------------------+----------------------+
| Testing Framework       | ❌             | ❌                | ✅                   |
+-------------------------+----------------+-------------------+----------------------+
| Connection Management   | Manual         | Manual            | Automatic            |
+-------------------------+----------------+-------------------+----------------------+
| Type Safety             | Manual         | Basic             | Full                 |
+-------------------------+----------------+-------------------+----------------------+
| Background Worker Msgs  | ❌             | ❌                | ✅                   |
+-------------------------+----------------+-------------------+----------------------+
| Structured Event System | ❌             | ❌                | ✅                   |
+-------------------------+----------------+-------------------+----------------------+

Contributing
------------

Contributions are welcome! Please see our `CONTRIBUTING.md <https://github.com/huynguyengl99/fast-channels/blob/main/CONTRIBUTING.md>`_ for detailed development setup and guidelines.

License
-------

This project is licensed under the MIT License - see the LICENSE file for details.

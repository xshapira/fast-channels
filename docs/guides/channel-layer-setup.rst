Channel Layer Setup Guide
==========================

This guide covers setting up and configuring channel layers in Fast Channels for cross-process communication,
group messaging, and scalable real-time applications.

Understanding Channel Layer Types
----------------------------------

Fast Channels provides three channel layer implementations:

In-Memory Channel Layer
~~~~~~~~~~~~~~~~~~~~~~~

**Best for:** Development, testing, single-process applications

**Import:**

.. code-block:: python

    from fast_channels.layers import InMemoryChannelLayer

    layer = InMemoryChannelLayer()

**Package required:** ``fast-channels``

**Key features:** Fast, no dependencies, single-process only, no persistence

Redis Queue Channel Layer
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Best for:** Production with reliable message delivery

**Import:**

.. code-block:: python

    from fast_channels.layers.redis import RedisChannelLayer

    layer = RedisChannelLayer(
        hosts=["redis://localhost:6379"],
        prefix="myapp",
        expiry=900,      # 15 minutes (default: 60)
        capacity=1000    # Max messages per channel (default: 100)
    )

**Package required:** ``fast-channels[redis]``

**Key features:** Message persistence, guaranteed delivery, multi-process support, configurable expiry/capacity

Redis Pub/Sub Channel Layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Best for:** Real-time applications prioritizing low latency

**Import:**

.. code-block:: python

    from fast_channels.layers.redis import RedisPubSubChannelLayer

    layer = RedisPubSubChannelLayer(
        hosts=["redis://localhost:6379"],
        prefix="chat"
    )

**Package required:** ``fast-channels[redis]``

**Key features:** Ultra-low latency, no persistence, fire-and-forget messaging

Registry Functions
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from fast_channels.layers import (
        register_channel_layer,    # Register a layer with an alias
        get_channel_layer,          # Retrieve a registered layer
        unregister_channel_layer,   # Remove a layer from registry
        has_layers,                 # Check if any layers are registered
    )

Quick Setup
-----------

1. **Install**

.. code-block:: bash

    pip install "fast-channels[redis]"  # For production
    pip install fast-channels           # For testing only

2. **Start Redis** (if using Redis layers)

.. code-block:: bash

    docker run -d -p 6379:6379 redis:alpine

3. **Create layers.py**

.. code-block:: python

    # layers.py
    import os
    from fast_channels.layers import has_layers, register_channel_layer
    from fast_channels.layers.redis import RedisChannelLayer

    def setup_channel_layers():
        """Set up and register channel layers for the application."""
        if has_layers():
            return

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        register_channel_layer("default", RedisChannelLayer(hosts=[redis_url]))

4. **Initialize in main.py**

.. code-block:: python

    # main.py
    from fastapi import FastAPI
    from .layers import setup_channel_layers

    setup_channel_layers()  # Call BEFORE creating the app
    app = FastAPI()

5. **Use in consumers**

.. code-block:: python

    # consumer.py
    from fast_channels.consumer.websocket import AsyncWebsocketConsumer

    class ChatConsumer(AsyncWebsocketConsumer):
        channel_layer_alias = "default"
        groups = ["chat_room"]

        async def connect(self):
            await self.accept()
            await self.channel_layer.group_send(
                "chat_room",
                {"type": "chat.message", "message": "User joined"}
            )

        async def chat_message(self, event):
            await self.send(text_data=event["message"])

Advanced Configuration
----------------------

Multiple Layers for Different Purposes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # layers.py
    import os
    from fast_channels.layers import InMemoryChannelLayer, has_layers, register_channel_layer
    from fast_channels.layers.redis import RedisChannelLayer, RedisPubSubChannelLayer

    def setup_channel_layers():
        if has_layers():
            return

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Different layers for different use cases
        register_channel_layer("memory", InMemoryChannelLayer())
        register_channel_layer("chat", RedisPubSubChannelLayer(hosts=[redis_url], prefix="chat"))
        register_channel_layer("queue", RedisChannelLayer(hosts=[redis_url], prefix="queue", expiry=900))
        register_channel_layer("notifications", RedisPubSubChannelLayer(hosts=[redis_url], prefix="notify"))

Environment-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def setup_channel_layers():
        env = os.getenv("ENV", "development")

        if env == "production":
            register_channel_layer("default", RedisChannelLayer(hosts=[os.getenv("REDIS_URL")]))
        else:
            register_channel_layer("default", InMemoryChannelLayer())

High Availability with Redis Sentinel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from fast_channels.layers.redis import RedisChannelLayer

    register_channel_layer(
        "ha_layer",
        RedisChannelLayer(
            sentinels=[("sentinel-1.example.com", 26379), ("sentinel-2.example.com", 26379)],
            service_name="mymaster",
            sentinel_kwargs={"password": "sentinel_password"},
            connection_kwargs={"password": "redis_password"},
            prefix="prod",
            expiry=600,
            capacity=2000
        )
    )

Sending from Background Workers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # worker.py
    from fast_channels.layers import get_channel_layer

    async def process_job(job_id: str, channel_name: str):
        result = await do_heavy_processing(job_id)

        layer = get_channel_layer("jobs")
        await layer.send(channel_name, {
            "type": "job.completed",
            "job_id": job_id,
            "result": result
        })

Troubleshooting
---------------

**"Channel layer 'xyz' not registered"**
  Call ``setup_channel_layers()`` before consumer instantiation and verify alias names match.

**Redis connection errors**
  Verify Redis is running (``redis-cli ping``), check URL, and ensure firewall allows connections.

**Messages not reaching consumers**
  For Pub/Sub: ensure consumers connect before sending. For Queue: check expiry settings and group names.

Best Practices
--------------

- Use ``has_layers()`` to prevent duplicate registrations
- Configure via environment variables for different environments
- Use descriptive aliases: "chat", "notifications", "jobs"
- Separate layers by purpose (don't mix real-time chat with critical job queues)
- Set appropriate expiry to balance memory usage with persistence
- Use different prefixes for different environments sharing Redis

Next Steps
----------

- Learn about :doc:`../concepts` to understand consumers and groups
- Follow the :doc:`../tutorial/index` for hands-on examples
- Explore the :doc:`../reference/layers` for detailed API documentation
- See ``sandbox/layers.py`` for real-world configurations

"""`server_started`: sent once per server process, on the first request it serves.

Domain apps run long work - a collection, a findings run, a workbook build - on daemon threads,
and record it as a RUNNING row. A restart kills the thread and leaves the row RUNNING, so every
check asking "is something in progress?" either believed it for ever or guessed with an age
limit. An engagement runs ONE server process (DEPLOYMENT.md), so at the start of a new one
nothing recorded as running can be: each app subscribes to this and closes its own rows.

**Why the first request, not `AppConfig.ready()`.** `ready()` runs in every process that loads
Django - `migrate`, `shell`, any management command run beside the live server. Closing rows
there would mark the server's genuinely running work as failed while its thread carried on,
and `migrate` runs it before the tables exist. Only a server serves requests.

**Why only a real handler.** The test client sends `request_started` too, from its own
handler class. Answering it would make the outcome of a test depend on whether it happened to
make the process's first request.
"""

from __future__ import annotations

import logging
import threading

from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.wsgi import WSGIHandler
from django.core.signals import request_started
from django.dispatch import Signal, receiver

#: Receivers take `**kwargs` and close whatever their app left RUNNING. One raising is logged by
#: `send_robust` rather than failing the request that happened to be first.
server_started = Signal()

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_sent = False


@receiver(request_started)
def _first_server_request(sender, **kwargs):
    global _sent
    if _sent or not (isinstance(sender, type) and issubclass(sender, (WSGIHandler, ASGIHandler))):
        return
    with _lock:
        if _sent:
            return
        _sent = True
    for receiver_fn, response in server_started.send_robust(sender=None):
        if isinstance(response, Exception):
            logger.error(
                "server_started receiver %r failed", receiver_fn, exc_info=response)

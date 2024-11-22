
# LTK - Copyright 2024 - All Rights Reserved - chrislaffra.com - See LICENSE 

"""
Implements a publish-subscribe facility.

Note this is a standalone module, not importing anything from LTK.
This allows its use in Workers, which may not want to include any UIs.

 - A receiver registers for events using `subscribe`.
 - A sender broadcasts events using `publish`.
 - Communication between the main UI and workers is done using the `xworker.sync`.

See https://github.com/pyscript/polyscript/tree/main/docs#xworker
"""

import json
import logging

__all__ = [
    "TOPIC_CRITICAL", "TOPIC_INFO", "TOPIC_DEBUG", "TOPIC_ERROR", "TOPIC_WARNING", "TOPIC_CRITICAL",
    "TOPIC_REQUEST", "TOPIC_RESPONSE", "TOPIC_WORKER_RUN", "TOPIC_WORKER_RESULT",
    "publish", "subscribe", "register_worker"
]

TOPIC_INFO = "log.info"
TOPIC_DEBUG = "log.debug"
TOPIC_ERROR = "log.error"
TOPIC_WARNING = "log.warning"
TOPIC_CRITICAL = "log.critical"

TOPIC_REQUEST = "app.request"
TOPIC_RESPONSE = "app.response"
TOPIC_WORKER_RUN = "worker.run"
TOPIC_WORKER_RESULT = "worker.result"
TOPIC_WORKER_READY = "worker.ready"


_logger = logging.getLogger('root')
_log_topics = {
    "log.info": _logger.info,
    "log.debug": _logger.debug,
    "log.error": _logger.error,
    "log.warning": _logger.warning,
    "log.critical": _logger.critical,
}


class _PubSub():
    def __init__(self):
        self.subscribers = []
        self.workers = {}
   
    def publish(self, sender, receiver, topic, data):
        for subscriber, subscribed_topic, handler in self.subscribers:
            if topic == subscribed_topic:
                if isinstance(handler, str):
                    self.workers[handler].sync.handler(sender, topic, json.dumps(data))
                else:
                    handler(data)
            log = _log_topics.get(topic, _logger.info)
            log(f"[Pubsub] {json.dumps(['', sender, receiver, topic, str(data)[:32]])}")

    def subscribe(self, receiver, topic, handler):
        self.subscribers.append([receiver, topic, handler])

    def worker_publish(self, sender, receiver, topic, data):
        try:
            data = json.loads(data)
        except:
            pass
        self.publish(sender, receiver, topic, data)

    def register_worker(self, name, worker):
        self.workers[name] = worker
        worker.sync.subscribe = self.subscribe
        worker.sync.publish = self.worker_publish


_pubsub = _PubSub()

subscribe = _pubsub.subscribe
publish = _pubsub.publish
register_worker = _pubsub.register_worker
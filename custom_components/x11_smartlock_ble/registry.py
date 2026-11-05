"""The only registration point for models and protocol implementations."""

from .models.x11 import X11Model
from .protocols.tuya_ble.session import TuyaBLEProtocol

MODELS = {}
PROTOCOLS = {}


def register_protocol(cls):
    if cls.protocol_id in PROTOCOLS:
        raise ValueError("Protocol already registered")
    PROTOCOLS[cls.protocol_id] = cls


def register_model(cls):
    if cls.product_id in MODELS:
        raise ValueError("Product already registered")
    if cls.protocol_id not in PROTOCOLS:
        raise ValueError("Model protocol is not registered")
    MODELS[cls.product_id] = cls


def model_class(credentials):
    cls = MODELS.get(credentials.product_id)
    if cls is None or credentials.category != cls.category:
        raise ValueError("Unsupported lock product/category")
    return cls


def create_connection(credentials, provider, ble_device):
    model_type = model_class(credentials)
    protocol = PROTOCOLS[model_type.protocol_id](provider, ble_device)
    return protocol, model_type(protocol, credentials)


def discovery_services():
    return {
        service
        for protocol in PROTOCOLS.values()
        for service in protocol.discovery_services
    }


register_protocol(TuyaBLEProtocol)
register_model(X11Model)

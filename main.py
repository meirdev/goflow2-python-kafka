from ipaddress import ip_address
from io import BytesIO

import loguru
from confluent_kafka import Consumer
from google.protobuf import proto

from src.flow.flow_pb2 import FlowMessage


CONF = {
    "bootstrap.servers": "127.0.0.1:9092",
    "group.id": "python-script",
    "auto.offset.reset": "smallest",
}

logger = loguru.logger


def main():
    consumer = Consumer(CONF)

    consumer.subscribe(["flows"])

    while True:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            logger.debug("No message")
            continue

        if msg.error():
            logger.debug(msg.error())
            continue

        value = BytesIO(msg.value())

        try:
            flow_message = proto.parse_length_prefixed(FlowMessage, value)

            logger.debug(flow_message)
            logger.debug(
                "{src_addr}:{src_port} -> {dst_addr}:{dst_port} {proto} {bytes} {packets}",
                src_addr=ip_address(flow_message.src_addr),
                src_port=flow_message.src_port,
                dst_addr=ip_address(flow_message.dst_addr),
                dst_port=flow_message.dst_port,
                proto=flow_message.proto,
                packets=flow_message.packets,
                bytes=flow_message.bytes,
            )
        except Exception as e:
            logger.exception(e)


if __name__ == "__main__":
    main()

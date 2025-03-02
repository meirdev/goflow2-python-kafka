import logging
import random
import sys
from datetime import datetime, timezone
from ipaddress import ip_address, IPv4Network, IPv6Address
from io import BytesIO

from confluent_kafka import Consumer
from google.protobuf import proto
from pythonjsonlogger.json import JsonFormatter

from flow.flow_pb2 import FlowMessage

CONF = {
    "bootstrap.servers": "127.0.0.1:9092",
    "group.id": "python-script",
    "auto.offset.reset": "smallest",
}

logger = logging.getLogger("flows")
logger.setLevel(logging.INFO)

logger_handler = logging.StreamHandler()
logger_handler.setFormatter(JsonFormatter())
logger.addHandler(logger_handler)


def main():
    consumer = Consumer(CONF)

    consumer.subscribe(["flows"])

    while True:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            logger.info("No message")
            continue

        if msg.error():
            logger.info(msg.error())
            continue

        value = BytesIO(msg.value())

        try:
            flow_message = proto.parse_length_prefixed(FlowMessage, value)
        except Exception as e:
            logger.exception(e)

        src_addr = ip_address(flow_message.src_addr)
        dst_addr = ip_address(flow_message.dst_addr)
        sampler_address = ip_address(flow_message.sampler_address)

        time_flow_start = datetime.fromtimestamp(
            flow_message.time_flow_start_ns / 1e9, timezone.utc
        )
        time_flow_end = datetime.fromtimestamp(
            flow_message.time_flow_end_ns / 1e9, timezone.utc
        )
        time_received = datetime.fromtimestamp(
            flow_message.time_received_ns / 1e9, timezone.utc
        )

        bytes = flow_message.bytes * max(flow_message.sampling_rate, 1)
        packets = flow_message.packets * max(flow_message.sampling_rate, 1)

        log = {
            "src_addr": src_addr,
            "dst_addr": dst_addr,
            "src_port": flow_message.src_port,
            "dst_port": flow_message.dst_port,
            "proto": flow_message.proto,
            "tcp_flags": flow_message.tcp_flags,
            "bytes": flow_message.bytes,
            "packets": flow_message.packets,
            "forwarding_status": flow_message.forwarding_status,
            "time_flow_start": time_flow_start.isoformat(),
            "time_flow_end": time_flow_end.isoformat(),
            "time_received": time_received.isoformat(),
            "type": flow_message.type,
            "sampling_rate": flow_message.sampling_rate,
            "sampler_address": sampler_address,
        }

        logger.info(
            f"{time_received.isoformat()} {src_addr}:{flow_message.src_port} > {dst_addr}:{flow_message.dst_port} protocol: {flow_message.proto} flags: {flow_message.tcp_flags} packets: {flow_message.packets} size: {flow_message.bytes} bytes sample ratio: {flow_message.sampling_rate} agent: {sampler_address}",
            extra=log,
        )


if __name__ == "__main__":
    main()

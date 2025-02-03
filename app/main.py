import logging
import random
from datetime import datetime, timezone
from ipaddress import ip_address, IPv4Network, IPv6Address
from io import BytesIO

import pytricia
import requests
from confluent_kafka import Consumer
from google.protobuf import proto
from prometheus_client import start_http_server, Counter

from flow.flow_pb2 import FlowMessage

METRIC_PORT = 8090

CONF = {
    "bootstrap.servers": "127.0.0.1:9092",
    "group.id": "python-script",
    "auto.offset.reset": "smallest",
}

inbound_bytes_counter = Counter(
    "inbound_bytes", "Bytes sent to destination prefix", ["prefix"]
)
inbound_packets_counter = Counter(
    "inbound_packets", "Packets sent to destination prefix", ["prefix"]
)

logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)


def main():
    start_http_server(METRIC_PORT)

    consumer = Consumer(CONF)

    consumer.subscribe(["flows"])

    pyt = pytricia.PyTricia(128)
    pyt.insert(IPv4Network("10.0.0.0/8"), {"name": "internal"})
    pyt.insert(IPv4Network("20.0.0.0/8"), {"name": "external"})
    pyt.insert(IPv6Address("2001:db8::1"), {"name": "ipv6"})

    logs = []

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

        dst_prefix = pyt.get_key(dst_addr)

        if dst_prefix:
            inbound_bytes_counter.labels(prefix=dst_prefix).inc(bytes)
            inbound_packets_counter.labels(prefix=dst_prefix).inc(packets)

            print(f"Sent {bytes} bytes to {dst_prefix}")

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
            "dst_prefix": dst_prefix,
        }

        logs.append([str(flow_message.time_received_ns), f"flow: {random.random()}", {k: str(v) for k, v in log.items()}])

        if len(logs) == 10:
            requests.post("http://127.0.0.1:3100/loki/api/v1/push", json={"streams": [{"stream": {"job": "flow"}, "values": logs}]}, headers={"X-Scope-OrgID": "grafana"})
            logs = []


if __name__ == "__main__":
    main()

CREATE FUNCTION IF NOT EXISTS convertFixedStringIpToString AS (etype, addr) ->
(
    if(etype = 0x0800, IPv4NumToString(reinterpretAsUInt32(substring(reverse(addr), 13,4))), IPv6NumToString(addr))
);

CREATE TABLE IF NOT EXISTS flows
(
    type Int32,
    time_received_ns UInt64,
    sequence_num UInt32,
    sampling_rate UInt64,

    sampler_address FixedString(16),

    time_flow_start_ns UInt64,
    time_flow_end_ns UInt64,

    bytes UInt64,
    packets UInt64,

    src_addr FixedString(16),
    dst_addr FixedString(16),

    etype UInt32,

    proto UInt32,

    src_port UInt32,
    dst_port UInt32,

    forwarding_status UInt32,
    tcp_flags UInt32,
    icmp_type UInt32,
    icmp_code UInt32,

    fragment_id UInt32,
    fragment_offset UInt32,

    src_asn UInt32,
    dst_asn UInt32,

    src_country String,
    dst_country String,

    src_prefix String,
    dst_prefix String
)
ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'kafka:9094',
    kafka_topic_list = 'flows',
    kafka_group_name = 'clickhouse',
    kafka_format = 'Protobuf',
    kafka_schema = 'flow.proto:FlowMessage';

CREATE TABLE IF NOT EXISTS flows_raw
(
    date Date,

    type Int32,
    time_received DateTime64(9),
    sequence_num UInt32,
    sampling_rate UInt64,

    sampler_address String,

    time_flow_start DateTime64(9),
    time_flow_end DateTime64(9),

    bytes UInt64,
    packets UInt64,

    src_addr String,
    dst_addr String,

    etype UInt32,

    proto UInt32,

    src_port UInt32,
    dst_port UInt32,

    forwarding_status UInt32,
    tcp_flags UInt32,
    icmp_type UInt32,
    icmp_code UInt32,

    fragment_id UInt32,
    fragment_offset UInt32
)
ENGINE = MergeTree()
PARTITION BY date
ORDER BY time_received;

CREATE MATERIALIZED VIEW IF NOT EXISTS flows_raw_mv TO flows_raw AS
    SELECT
        toDate(time_received_ns / 1000000000) AS date,
        type,
        toDateTime64(time_received_ns / 1000000000, 9) AS time_received,
        sequence_num,
        sampling_rate,
        convertFixedStringIpToString(0x0800, sampler_address) AS sampler_address,
        toDateTime64(time_flow_start_ns / 1000000000, 9) AS time_flow_start,
        toDateTime64(time_flow_end_ns / 1000000000, 9) AS time_flow_end,
        bytes,
        packets,
        convertFixedStringIpToString(etype, src_addr) AS src_addr,
        convertFixedStringIpToString(etype, dst_addr) AS dst_addr,
        etype,
        proto,
        src_port,
        dst_port,
        forwarding_status,
        tcp_flags,
        icmp_type,
        icmp_code,
        fragment_id,
        fragment_offset
    FROM flows;

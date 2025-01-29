CREATE TABLE IF NOT EXISTS networks (
    prefix String,
    tenant String
)
ENGINE = MergeTree()
PRIMARY KEY prefix;

CREATE DICTIONARY IF NOT EXISTS networks_dict (
    key String,
    value String
)
PRIMARY KEY key
SOURCE(CLICKHOUSE(QUERY 'SELECT prefix AS key, prefix AS value FROM networks'))
LAYOUT(IP_TRIE)
LIFETIME(600);

CREATE FUNCTION IF NOT EXISTS getPrefix AS (etype, addr) ->
    multiIf(
        etype = 0x0800, dictGetOrDefault('networks_dict', 'value', toIPv4(addr), ''),
        etype = 0x86DD, dictGetOrDefault('networks_dict', 'value', IPv6StringToNum(addr), ''),
        ''
    );

CREATE TABLE IF NOT EXISTS inbound
(
    date Date,

    type Int32,
    time_received DateTime,
    sequence_num UInt32,
    sampling_rate UInt64,
    flow_direction UInt32,

    sampler_address String,

    time_flow_start DateTime,
    time_flow_end DateTime,

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
    fragment_offset UInt32,

    prefix String,
    tenant String
) ENGINE = MergeTree()
PARTITION BY date
ORDER BY (tenant, prefix, time_received)
TTL date + INTERVAL 30 DAY;

ALTER TABLE inbound ADD INDEX prefix_idx prefix TYPE set(100000) GRANULARITY 1;
ALTER TABLE inbound ADD INDEX tenant_idx tenant TYPE set(100000) GRANULARITY 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS inbound_mv TO inbound AS
    SELECT
        *,
        getPrefix(etype, src_addr) AS prefix,
        networks.tenant AS tenant
    FROM flows_raw
    INNER JOIN networks ON networks.prefix = prefix;

CREATE TABLE IF NOT EXISTS inbound_1m
(
    prefix String,
    minute DateTime,

    bytes UInt64,
    packets UInt64,
    flows UInt64
)
ENGINE = SummingMergeTree()
ORDER BY (prefix, minute)
TTL minute + INTERVAL 30 DAY;

ALTER TABLE inbound_1m ADD INDEX prefix_idx prefix TYPE set(100000) GRANULARITY 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS inbound_1m_mv TO inbound_1m AS
    SELECT
        prefix,
        toStartOfMinute(time_received) AS minute,
        sum(bytes * max2(sampling_rate, 2000)) AS bytes,
        sum(packets * max2(sampling_rate, 2000)) AS packets,
        count() AS flows
    FROM inbound
    GROUP BY prefix, minute;

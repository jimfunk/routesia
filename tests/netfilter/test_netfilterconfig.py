from routesia.netfilter.netfilterconfig import NetfilterConfig
from routesia.schema.v2 import netfilter_pb2


def test_input_policy(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True
    config.input.policy = netfilter_pb2.ACCEPT
    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"] == {
        "family": "inet",
        "handle": any_integer,
        "hook": "input",
        "name": "input",
        "policy": "accept",
        "prio": 0,
        "table": "filter",
        "type": "filter",
        "rules": [],
    }

    config.input.policy = netfilter_pb2.DROP
    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"] == {
        "family": "inet",
        "handle": any_integer,
        "hook": "input",
        "name": "input",
        "policy": "drop",
        "prio": 0,
        "table": "filter",
        "type": "filter",
        "rules": [],
    }


def test_forward_policy(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True
    config.forward.policy = netfilter_pb2.ACCEPT
    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["forward"] == {
        "family": "inet",
        "handle": any_integer,
        "hook": "forward",
        "name": "forward",
        "policy": "accept",
        "prio": 0,
        "table": "filter",
        "type": "filter",
        "rules": [],
    }

    config.forward.policy = netfilter_pb2.DROP
    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["forward"] == {
        "family": "inet",
        "handle": any_integer,
        "hook": "forward",
        "name": "forward",
        "policy": "drop",
        "prio": 0,
        "table": "filter",
        "type": "filter",
        "rules": [],
    }


def test_ip_protocol_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Protocol match"
    ip = rule.ip.add()
    ip.protocol.append("41")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Protocol match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "protocol",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": "ipv6",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]

def test_ip_multi_protocol_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-protocol match"
    ip = rule.ip.add()
    ip.protocol.append("6")
    ip.protocol.append("17")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-protocol match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "protocol",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "tcp",
                                "udp",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Source match"
    ip = rule.ip.add()
    ip.source.append("10.1.1.1")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": "10.1.1.1",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip_multi_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-source match"
    ip = rule.ip.add()
    ip.source.append("10.1.1.1")
    ip.source.append("10.2.2.2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "10.1.1.1",
                                "10.2.2.2",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Destination match"
    ip = rule.ip.add()
    ip.destination.append("10.1.1.1")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": "10.1.1.1",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip_multi_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-destination match"
    ip = rule.ip.add()
    ip.destination.append("10.1.1.1")
    ip.destination.append("10.2.2.2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "10.1.1.1",
                                "10.2.2.2",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    ip = rule.ip.add()
    ip.protocol.append("tcp")
    ip.source.append("10.1.1.1")
    ip.destination.append("10.2.2.2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "protocol",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": "tcp",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": "10.1.1.1",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "==",
                        "right": "10.2.2.2",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip_negated_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    ip = rule.ip.add()
    ip.negate = True
    ip.protocol.append("tcp")
    ip.source.append("10.1.1.1")
    ip.destination.append("10.2.2.2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "protocol",
                                "protocol": "ip",
                            },
                        },
                        "op": "!=",
                        "right": "tcp",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "!=",
                        "right": "10.1.1.1",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip",
                            },
                        },
                        "op": "!=",
                        "right": "10.2.2.2",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_protocol_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Protocol match"
    ip6 = rule.ip6.add()
    ip6.protocol.append("41")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Protocol match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "nexthdr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": "ipv6",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_multi_protocol_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-protocol match"
    ip6 = rule.ip6.add()
    ip6.protocol.append("6")
    ip6.protocol.append("17")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-protocol match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "nexthdr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "tcp",
                                "udp",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Source match"
    ip6 = rule.ip6.add()
    ip6.source.append("2001:db8:1::1")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": "2001:db8:1::1",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_multi_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-source match"
    ip6 = rule.ip6.add()
    ip6.source.append("2001:db8:1::1")
    ip6.source.append("2001:db8:2::2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "2001:db8:1::1",
                                "2001:db8:2::2",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Destination match"
    ip6 = rule.ip6.add()
    ip6.destination.append("2001:db8:1::1")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": "2001:db8:1::1",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_multi_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-destination match"
    ip6 = rule.ip6.add()
    ip6.destination.append("2001:db8:1::1")
    ip6.destination.append("2001:db8:2::2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "2001:db8:1::1",
                                "2001:db8:2::2",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    ip6 = rule.ip6.add()
    ip6.protocol.append("tcp")
    ip6.source.append("2001:db8:1::1")
    ip6.destination.append("2001:db8:2::2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "nexthdr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": "tcp",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": "2001:db8:1::1",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "==",
                        "right": "2001:db8:2::2",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ip6_negated_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    ip6 = rule.ip6.add()
    ip6.negate = True
    ip6.protocol.append("tcp")
    ip6.source.append("2001:db8:1::1")
    ip6.destination.append("2001:db8:2::2")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "nexthdr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "!=",
                        "right": "tcp",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "saddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "!=",
                        "right": "2001:db8:1::1",
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "daddr",
                                "protocol": "ip6",
                            },
                        },
                        "op": "!=",
                        "right": "2001:db8:2::2",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_tcp_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "TCP source match"
    tcp = rule.tcp.add()
    tcp.source.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "TCP source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "==",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_tcp_multi_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-source match"
    tcp = rule.tcp.add()
    tcp.source.append("80")
    tcp.source.append("443")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                80,
                                443,
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_tcp_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "TCP destination match"
    tcp = rule.tcp.add()
    tcp.destination.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "TCP destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "==",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_tcp_multi_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-destination match"
    tcp = rule.tcp.add()
    tcp.destination.append("80")
    tcp.destination.append("443")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                80,
                                443,
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_tcp_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    tcp = rule.tcp.add()
    tcp.source.append("81")
    tcp.destination.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "==",
                        "right": 81,
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "==",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_tcp_negated_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    tcp = rule.tcp.add()
    tcp.negate = True
    tcp.source.append("81")
    tcp.destination.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "!=",
                        "right": 81,
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "tcp",
                            },
                        },
                        "op": "!=",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_udp_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "UDP source match"
    udp = rule.udp.add()
    udp.source.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "UDP source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "udp",
                            },
                        },
                        "op": "==",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_udp_multi_source_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-source match"
    udp = rule.udp.add()
    udp.source.append("80")
    udp.source.append("443")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-source match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "udp",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                80,
                                443,
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_udp_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "TCP destination match"
    udp = rule.udp.add()
    udp.destination.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "TCP destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "udp",
                            },
                        },
                        "op": "==",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_udp_multi_destination_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-destination match"
    udp = rule.udp.add()
    udp.destination.append("80")
    udp.destination.append("443")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-destination match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "udp",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                80,
                                443,
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_udp_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    udp = rule.udp.add()
    udp.source.append("81")
    udp.destination.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "udp",
                            },
                        },
                        "op": "==",
                        "right": 81,
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "udp",
                            },
                        },
                        "op": "==",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_udp_negated_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    udp = rule.udp.add()
    udp.negate = True
    udp.source.append("81")
    udp.destination.append("80")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "sport",
                                "protocol": "udp",
                            },
                        },
                        "op": "!=",
                        "right": 81,
                    },
                },
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "dport",
                                "protocol": "udp",
                            },
                        },
                        "op": "!=",
                        "right": 80,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp_type_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "ICMP type match"
    icmp = rule.icmp.add()
    icmp.type.append("echo-request")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "ICMP type match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "type",
                                "protocol": "icmp",
                            },
                        },
                        "op": "==",
                        "right": "echo-request",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp_negated_type_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "ICMP negated type match"
    icmp = rule.icmp.add()
    icmp.type.append("echo-request")
    icmp.negate = True

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "ICMP negated type match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "type",
                                "protocol": "icmp",
                            },
                        },
                        "op": "!=",
                        "right": "echo-request",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp_multi_type_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-type match"
    icmp = rule.icmp.add()
    icmp.type.append("echo-request")
    icmp.type.append("echo-reply")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-type match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "type",
                                "protocol": "icmp",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "echo-reply",
                                "echo-request",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp_code_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "ICMP code match"
    icmp = rule.icmp.add()
    icmp.code.append(111)

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "ICMP code match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "code",
                                "protocol": "icmp",
                            },
                        },
                        "op": "==",
                        "right": 111,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp_multi_code_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-code match"
    icmp = rule.icmp.add()
    icmp.code.append(111)
    icmp.code.append(123)

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-code match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "code",
                                "protocol": "icmp",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                111,
                                123,
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp6_type_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "ICMP6 type match"
    icmp6 = rule.icmp6.add()
    icmp6.type.append("echo-request")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "ICMP6 type match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "type",
                                "protocol": "icmpv6",
                            },
                        },
                        "op": "==",
                        "right": "echo-request",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp6_negated_type_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "ICMP6 negated type match"
    icmp6 = rule.icmp6.add()
    icmp6.type.append("echo-request")
    icmp6.negate = True

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "ICMP6 negated type match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "type",
                                "protocol": "icmpv6",
                            },
                        },
                        "op": "!=",
                        "right": "echo-request",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp6_multi_type_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-type match"
    icmp6 = rule.icmp6.add()
    icmp6.type.append("echo-request")
    icmp6.type.append("echo-reply")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-type match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "type",
                                "protocol": "icmpv6",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "echo-request",
                                "echo-reply",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_icmp6_code_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "ICMP6 code match"
    icmp6 = rule.icmp6.add()
    icmp6.code.append(111)

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "ICMP6 code match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "payload": {
                                "field": "code",
                                "protocol": "icmpv6",
                            },
                        },
                        "op": "==",
                        "right": 111,
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ct_state_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "CT state match"
    ct = rule.ct.add()
    ct.state.append("established")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "CT state match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "ct": {
                                "key": "state",
                            },
                        },
                        "op": "in",
                        "right": "established",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ct_negated_state_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "CT negated state match"
    ct = rule.ct.add()
    ct.state.append("established")
    ct.negate = True

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "CT negated state match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "ct": {
                                "key": "state",
                            },
                        },
                        "op": "!=",
                        "right": "established",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_ct_multi_state_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-state match"
    ct = rule.ct.add()
    ct.state.append("established")
    ct.state.append("related")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-state match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "ct": {
                                "key": "state",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "established",
                                "related",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_protocol_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Protocol match"
    meta = rule.meta.add()
    meta.protocol.append("ip")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Protocol match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "protocol",
                            },
                        },
                        "op": "==",
                        "right": "ip",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_multi_protocol_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-protocol match"
    meta = rule.meta.add()
    meta.protocol.append("ip")
    meta.protocol.append("ip6")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-protocol match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "protocol",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "ip",
                                "ip6",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_input_interface_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Input interface match"
    meta = rule.meta.add()
    meta.input_interface.append("eth0")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Input interface match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "iifname",
                            },
                        },
                        "op": "==",
                        "right": "eth0",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_multi_input_interface_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-input_interface match"
    meta = rule.meta.add()
    meta.input_interface.append("eth0")
    meta.input_interface.append("eth1")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-input_interface match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "iifname",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "eth0",
                                "eth1",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_output_interface_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Input interface match"
    meta = rule.meta.add()
    meta.output_interface.append("eth0")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Input interface match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "oifname",
                            },
                        },
                        "op": "==",
                        "right": "eth0",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_multi_output_interface_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Multi-output_interface match"
    meta = rule.meta.add()
    meta.output_interface.append("eth0")
    meta.output_interface.append("eth1")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Multi-output_interface match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "oifname",
                            },
                        },
                        "op": "==",
                        "right": {
                            "set": [
                                "eth0",
                                "eth1",
                            ],
                        },
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    meta = rule.meta.add()
    meta.protocol.append("ip")
    meta.input_interface.append("eth0")
    meta.output_interface.append("eth1")

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "iifname",
                            },
                        },
                        "op": "==",
                        "right": "eth0",
                    },
                },
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "oifname",
                            },
                        },
                        "op": "==",
                        "right": "eth1",
                    },
                },
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "protocol",
                            },
                        },
                        "op": "==",
                        "right": "ip",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_meta_negated_compound_match(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    rule = config.input.rule.add()
    rule.description = "Compound match"
    meta = rule.meta.add()
    meta.protocol.append("ip")
    meta.input_interface.append("eth0")
    meta.output_interface.append("eth1")
    meta.negate = True

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["inet"]["filter"]["chains"]["input"]["rules"] == [
        {
            "chain": "input",
            "comment": "Compound match",
            "expr": [
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "iifname",
                            },
                        },
                        "op": "!=",
                        "right": "eth0",
                    },
                },
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "oifname",
                            },
                        },
                        "op": "!=",
                        "right": "eth1",
                    },
                },
                {
                    "match": {
                        "left": {
                            "meta": {
                                "key": "protocol",
                            },
                        },
                        "op": "!=",
                        "right": "ip",
                    },
                },
                {
                    "accept": None,
                }
            ],
            "family": "inet",
            "handle": any_integer,
            "table": "filter"
        }
    ]


def test_masquerade(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["ip"]["nat"] == {
        "family": "ip",
        "handle": 1,
        "name": "nat",
        "chains": {
            "postrouting": {
                "family": "ip",
                "table": "nat",
                "type": "nat",
                "handle": any_integer,
                "hook": "postrouting",
                "name": "postrouting",
                "policy": "accept",
                "prio": 100,
                "rules": [
                    {
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat",
                        "chain": "postrouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "oifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                }
                            },
                            {
                                "masquerade": None,
                            }
                        ],
                    },
                ],
            },
            "prerouting": {
                "family": "ip",
                "handle": any_integer,
                "hook": "prerouting",
                "name": "prerouting",
                "policy": "accept",
                "prio": 0,
                "table": "nat",
                "type": "nat",
                "rules": [],
            }
        },
    }


def test_masquerade_multiple_interfaces(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    masquerade = config.masquerade.add()
    masquerade.interface = "eth1"

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["ip"]["nat"] == {
        "family": "ip",
        "handle": 1,
        "name": "nat",
        "chains": {
            "postrouting": {
                "family": "ip",
                "table": "nat",
                "type": "nat",
                "handle": any_integer,
                "hook": "postrouting",
                "name": "postrouting",
                "policy": "accept",
                "prio": 100,
                "rules": [
                    {
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat",
                        "chain": "postrouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "oifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                }
                            },
                            {
                                "masquerade": None,
                            }
                        ],
                    },
                    {
                        "chain": "postrouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "oifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth1",
                                },
                            },
                            {
                                "masquerade": None,
                            }
                        ],
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat"
                    },
                ],
            },
            "prerouting": {
                "family": "ip",
                "handle": any_integer,
                "hook": "prerouting",
                "name": "prerouting",
                "policy": "accept",
                "prio": 0,
                "table": "nat",
                "type": "nat",
                "rules": [],
            }
        },
    }


def test_masquerade_with_ip_forward(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "10.1.1.2"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.TCP
    port_map.port = "8080"
    port_map.destination_port = "80"

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["ip"]["nat"] == {
        "family": "ip",
        "handle": any_integer,
        "name": "nat",
        "chains": {
            "postrouting": {
                "family": "ip",
                "table": "nat",
                "type": "nat",
                "handle": any_integer,
                "hook": "postrouting",
                "name": "postrouting",
                "policy": "accept",
                "prio": 100,
                "rules": [
                    {
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat",
                        "chain": "postrouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "oifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                }
                            },
                            {
                                "masquerade": None,
                            }
                        ],
                    },
                ],
            },
            "prerouting": {
                "family": "ip",
                "handle": any_integer,
                "hook": "prerouting",
                "name": "prerouting",
                "policy": "accept",
                "prio": 0,
                "table": "nat",
                "type": "nat",
                "rules": [
                    {
                        "chain": "prerouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "iifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                },
                            },
                            {
                                "dnat": {
                                    "addr": {
                                        "map": {
                                            "data": {
                                                "set": [
                                                    [
                                                        8080,
                                                        {
                                                            "concat": [
                                                                "10.1.1.2",
                                                                80,
                                                            ],
                                                        },
                                                    ],
                                                ],
                                            },
                                            "key": {
                                                "payload": {
                                                    "protocol": "tcp",
                                                    "field": "dport",
                                                },
                                            },
                                        },
                                    },
                                    "family": "ip",
                                },
                            }
                        ],
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat"
                    }
                ],
            }
        },
    }


def test_masquerade_with_multiple_port_maps(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "10.1.1.2"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.TCP
    port_map.port = "8080"
    port_map.destination_port = "80"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.TCP
    port_map.port = "8443"
    port_map.destination_port = "443"

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["ip"]["nat"] == {
        "family": "ip",
        "handle": 1,
        "name": "nat",
        "chains": {
            "postrouting": {
                "family": "ip",
                "table": "nat",
                "type": "nat",
                "handle": any_integer,
                "hook": "postrouting",
                "name": "postrouting",
                "policy": "accept",
                "prio": 100,
                "rules": [
                    {
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat",
                        "chain": "postrouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "oifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                }
                            },
                            {
                                "masquerade": None,
                            }
                        ],
                    },
                ],
            },
            "prerouting": {
                "family": "ip",
                "handle": any_integer,
                "hook": "prerouting",
                "name": "prerouting",
                "policy": "accept",
                "prio": 0,
                "table": "nat",
                "type": "nat",
                "rules": [
                    {
                        "chain": "prerouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "iifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                },
                            },
                            {
                                "dnat": {
                                    "addr": {
                                        "map": {
                                            "data": {
                                                "set": [
                                                    [
                                                        8080,
                                                        {
                                                            "concat": [
                                                                "10.1.1.2",
                                                                80,
                                                            ],
                                                        },
                                                    ],
                                                    [
                                                        8443,
                                                        {
                                                            "concat": [
                                                                "10.1.1.2",
                                                                443,
                                                            ],
                                                        },
                                                    ],
                                                ],
                                            },
                                            "key": {
                                                "payload": {
                                                    "protocol": "tcp",
                                                    "field": "dport",
                                                },
                                            },
                                        },
                                    },
                                    "family": "ip",
                                },
                            }
                        ],
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat"
                    }
                ],
            }
        },
    }


def test_masquerade_with_multiple_ip_forwards(nftables, any_integer):
    config = netfilter_pb2.NetfilterConfig()
    config.enabled = True

    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "10.1.1.2"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.TCP
    port_map.port = "8080"
    port_map.destination_port = "80"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.TCP
    port_map.port = "8443"
    port_map.destination_port = "443"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "10.1.1.3"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.TCP
    port_map.port = "22"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.UDP
    port_map.port = "8053"
    port_map.destination_port = "53"

    nftables.cmd(str(NetfilterConfig(config)))
    assert nftables.get_ruleset()["ip"]["nat"] == {
        "family": "ip",
        "handle": 1,
        "name": "nat",
        "chains": {
            "postrouting": {
                "family": "ip",
                "table": "nat",
                "type": "nat",
                "handle": any_integer,
                "hook": "postrouting",
                "name": "postrouting",
                "policy": "accept",
                "prio": 100,
                "rules": [
                    {
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat",
                        "chain": "postrouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "oifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                }
                            },
                            {
                                "masquerade": None,
                            }
                        ],
                    },
                ],
            },
            "prerouting": {
                "family": "ip",
                "handle": any_integer,
                "hook": "prerouting",
                "name": "prerouting",
                "policy": "accept",
                "prio": 0,
                "table": "nat",
                "type": "nat",
                "rules": [
                    {
                        "chain": "prerouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "iifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                },
                            },
                            {
                                "dnat": {
                                    "addr": {
                                        "map": {
                                            "data": {
                                                "set": [
                                                    [
                                                        8080,
                                                        {
                                                            "concat": [
                                                                "10.1.1.2",
                                                                80,
                                                            ],
                                                        },
                                                    ],
                                                    [
                                                        8443,
                                                        {
                                                            "concat": [
                                                                "10.1.1.2",
                                                                443,
                                                            ],
                                                        },
                                                    ],
                                                ],
                                            },
                                            "key": {
                                                "payload": {
                                                    "protocol": "tcp",
                                                    "field": "dport",
                                                },
                                            },
                                        },
                                    },
                                    "family": "ip",
                                },
                            }
                        ],
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat"
                    },
                    {
                        "chain": "prerouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "iifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                },
                            },
                            {
                                "dnat": {
                                    "addr": {
                                        "map": {
                                            "data": {
                                                "set": [
                                                    [
                                                        8053,
                                                        {
                                                            "concat": [
                                                                "10.1.1.3",
                                                                53,
                                                            ],
                                                        },
                                                    ],
                                                ],
                                            },
                                            "key": {
                                                "payload": {
                                                    "protocol": "udp",
                                                    "field": "dport",
                                                },
                                            },
                                        },
                                    },
                                    "family": "ip",
                                },
                            }
                        ],
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat"
                    },
                    {
                        "chain": "prerouting",
                        "expr": [
                            {
                                "match": {
                                    "left": {
                                        "meta": {
                                            "key": "iifname",
                                        },
                                    },
                                    "op": "==",
                                    "right": "eth0",
                                },
                            },
                            {
                                "dnat": {
                                    "addr": {
                                        "map": {
                                            "data": {
                                                "set": [
                                                    [
                                                        22,
                                                        {
                                                            "concat": [
                                                                "10.1.1.3",
                                                                22,
                                                            ],
                                                        },
                                                    ],
                                                ],
                                            },
                                            "key": {
                                                "payload": {
                                                    "protocol": "tcp",
                                                    "field": "dport",
                                                },
                                            },
                                        },
                                    },
                                    "family": "ip",
                                },
                            }
                        ],
                        "family": "ip",
                        "handle": any_integer,
                        "table": "nat"
                    },
                ],
            }
        },
    }

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdbool.h>
#include <stddef.h>
#include <linux/if_arp.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <linux/if.h>
#include <linux/if_link.h>

static struct PyModuleDef constants_module = {
    PyModuleDef_HEAD_INIT,
    "netlink",
    "Netlink constants",
    -1,
};

PyMODINIT_FUNC PyInit_constants(void) {
    PyObject *m;
    m = PyModule_Create(&constants_module);
    if (m == NULL)
        return NULL;

#ifndef SOL_NETLINK
#define SOL_NETLINK 270
#endif
    PyModule_AddIntMacro(m, SOL_NETLINK);

    /* Netlink types */
    PyModule_AddIntMacro(m, NETLINK_ROUTE);
    PyModule_AddIntMacro(m, NETLINK_UNUSED);
    PyModule_AddIntMacro(m, NETLINK_USERSOCK);
    PyModule_AddIntMacro(m, NETLINK_FIREWALL);
    PyModule_AddIntMacro(m, NETLINK_SOCK_DIAG);
    PyModule_AddIntMacro(m, NETLINK_NFLOG);
    PyModule_AddIntMacro(m, NETLINK_XFRM);
    PyModule_AddIntMacro(m, NETLINK_SELINUX);
    PyModule_AddIntMacro(m, NETLINK_ISCSI);
    PyModule_AddIntMacro(m, NETLINK_AUDIT);
    PyModule_AddIntMacro(m, NETLINK_FIB_LOOKUP);
    PyModule_AddIntMacro(m, NETLINK_CONNECTOR);
    PyModule_AddIntMacro(m, NETLINK_NETFILTER);
    PyModule_AddIntMacro(m, NETLINK_IP6_FW);
    PyModule_AddIntMacro(m, NETLINK_DNRTMSG);
    PyModule_AddIntMacro(m, NETLINK_KOBJECT_UEVENT);
    PyModule_AddIntMacro(m, NETLINK_GENERIC);
    PyModule_AddIntMacro(m, NETLINK_SCSITRANSPORT);
    PyModule_AddIntMacro(m, NETLINK_ECRYPTFS);
    PyModule_AddIntMacro(m, NETLINK_RDMA);
    PyModule_AddIntMacro(m, NETLINK_CRYPTO);
    PyModule_AddIntMacro(m, NETLINK_SMC);
    PyModule_AddIntMacro(m, NETLINK_INET_DIAG);

    /* Flags for nlmsghdr nlmsg_flags */
    PyModule_AddIntMacro(m, NLM_F_REQUEST);
    PyModule_AddIntMacro(m, NLM_F_MULTI);
    PyModule_AddIntMacro(m, NLM_F_ACK);
    PyModule_AddIntMacro(m, NLM_F_ECHO);
    PyModule_AddIntMacro(m, NLM_F_DUMP_INTR);
    PyModule_AddIntMacro(m, NLM_F_DUMP_FILTERED);
    PyModule_AddIntMacro(m, NLM_F_ROOT);
    PyModule_AddIntMacro(m, NLM_F_MATCH);
    PyModule_AddIntMacro(m, NLM_F_ATOMIC);
    PyModule_AddIntMacro(m, NLM_F_DUMP);
    PyModule_AddIntMacro(m, NLM_F_REPLACE);
    PyModule_AddIntMacro(m, NLM_F_EXCL);
    PyModule_AddIntMacro(m, NLM_F_CREATE);
    PyModule_AddIntMacro(m, NLM_F_APPEND);
    PyModule_AddIntMacro(m, NLM_F_NONREC);
#ifdef NLM_F_BULK
    PyModule_AddIntMacro(m, NLM_F_BULK);
#endif
    PyModule_AddIntMacro(m, NLM_F_CAPPED);
    PyModule_AddIntMacro(m, NLM_F_ACK_TLVS);

    /* Base types for nlmsghdr nlmsg_type */
    PyModule_AddIntMacro(m, NLMSG_NOOP);
    PyModule_AddIntMacro(m, NLMSG_ERROR);
    PyModule_AddIntMacro(m, NLMSG_DONE);
    PyModule_AddIntMacro(m, NLMSG_OVERRUN);

    /* nlmsgerr attribute types */
    PyModule_AddIntMacro(m, NLMSGERR_ATTR_UNUSED);
    PyModule_AddIntMacro(m, NLMSGERR_ATTR_MSG);
    PyModule_AddIntMacro(m, NLMSGERR_ATTR_OFFS);
    PyModule_AddIntMacro(m, NLMSGERR_ATTR_COOKIE);
    PyModule_AddIntMacro(m, NLMSGERR_ATTR_POLICY);
#ifdef NLMSGERR_ATTR_MISS_TYPE
    PyModule_AddIntMacro(m, NLMSGERR_ATTR_MISS_TYPE);
#endif
#ifdef NLMSGERR_ATTR_MISS_NEST
    PyModule_AddIntMacro(m, NLMSGERR_ATTR_MISS_NEST);
#endif

    /* Netlink socket options */
    PyModule_AddIntMacro(m, NETLINK_ADD_MEMBERSHIP);
    PyModule_AddIntMacro(m, NETLINK_DROP_MEMBERSHIP);
    PyModule_AddIntMacro(m, NETLINK_PKTINFO);
    PyModule_AddIntMacro(m, NETLINK_BROADCAST_ERROR);
    PyModule_AddIntMacro(m, NETLINK_NO_ENOBUFS);
    PyModule_AddIntMacro(m, NETLINK_RX_RING);
    PyModule_AddIntMacro(m, NETLINK_TX_RING);
    PyModule_AddIntMacro(m, NETLINK_LISTEN_ALL_NSID);
    PyModule_AddIntMacro(m, NETLINK_LIST_MEMBERSHIPS);
    PyModule_AddIntMacro(m, NETLINK_CAP_ACK);
    PyModule_AddIntMacro(m, NETLINK_EXT_ACK);
    PyModule_AddIntMacro(m, NETLINK_GET_STRICT_CHK);

    /* Netlink attribute flags for nla_type in nlattr */
    PyModule_AddIntMacro(m, NLA_F_NESTED);
    PyModule_AddIntMacro(m, NLA_F_NET_BYTEORDER);
    PyModule_AddIntMacro(m, NLA_TYPE_MASK);

    /* nlattr attributes types */
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_INVALID);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_FLAG);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_U8);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_U16);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_U32);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_U64);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_S8);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_S16);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_S32);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_S64);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_BINARY);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_STRING);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_NUL_STRING);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_NESTED);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_NESTED_ARRAY);
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_BITFIELD32);
#ifdef NL_ATTR_TYPE_SINT
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_SINT);
#endif
#ifdef NL_ATTR_TYPE_UINT
    PyModule_AddIntMacro(m, NL_ATTR_TYPE_UINT);
#endif

    /* nlattr policy type attributes */
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_UNSPEC);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_TYPE);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_MIN_VALUE_S);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_MAX_VALUE_S);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_MIN_VALUE_U);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_MAX_VALUE_U);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_MIN_LENGTH);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_MAX_LENGTH);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_POLICY_IDX);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_POLICY_MAXTYPE);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_BITFIELD32_MASK);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_PAD);
    PyModule_AddIntMacro(m, NL_POLICY_TYPE_ATTR_MASK);

    /* rtnetlink message types for nlmsghdr nlmsg_type */
    PyModule_AddIntMacro(m, RTM_NEWLINK);
    PyModule_AddIntMacro(m, RTM_DELLINK);
    PyModule_AddIntMacro(m, RTM_GETLINK);
    PyModule_AddIntMacro(m, RTM_SETLINK);
    PyModule_AddIntMacro(m, RTM_NEWADDR);
    PyModule_AddIntMacro(m, RTM_DELADDR);
    PyModule_AddIntMacro(m, RTM_GETADDR);
    PyModule_AddIntMacro(m, RTM_NEWROUTE);
    PyModule_AddIntMacro(m, RTM_DELROUTE);
    PyModule_AddIntMacro(m, RTM_GETROUTE);
    PyModule_AddIntMacro(m, RTM_NEWNEIGH);
    PyModule_AddIntMacro(m, RTM_DELNEIGH);
    PyModule_AddIntMacro(m, RTM_GETNEIGH);
    PyModule_AddIntMacro(m, RTM_NEWRULE);
    PyModule_AddIntMacro(m, RTM_DELRULE);
    PyModule_AddIntMacro(m, RTM_GETRULE);
    PyModule_AddIntMacro(m, RTM_NEWQDISC);
    PyModule_AddIntMacro(m, RTM_DELQDISC);
    PyModule_AddIntMacro(m, RTM_GETQDISC);
    PyModule_AddIntMacro(m, RTM_NEWTCLASS);
    PyModule_AddIntMacro(m, RTM_DELTCLASS);
    PyModule_AddIntMacro(m, RTM_GETTCLASS);
    PyModule_AddIntMacro(m, RTM_NEWTFILTER);
    PyModule_AddIntMacro(m, RTM_DELTFILTER);
    PyModule_AddIntMacro(m, RTM_GETTFILTER);
    PyModule_AddIntMacro(m, RTM_NEWACTION);
    PyModule_AddIntMacro(m, RTM_DELACTION);
    PyModule_AddIntMacro(m, RTM_GETACTION);
    PyModule_AddIntMacro(m, RTM_NEWPREFIX);
    PyModule_AddIntMacro(m, RTM_GETMULTICAST);
    PyModule_AddIntMacro(m, RTM_GETANYCAST);
    PyModule_AddIntMacro(m, RTM_NEWNEIGHTBL);
    PyModule_AddIntMacro(m, RTM_GETNEIGHTBL);
    PyModule_AddIntMacro(m, RTM_SETNEIGHTBL);
    PyModule_AddIntMacro(m, RTM_NEWNDUSEROPT);
    PyModule_AddIntMacro(m, RTM_NEWADDRLABEL);
    PyModule_AddIntMacro(m, RTM_DELADDRLABEL);
    PyModule_AddIntMacro(m, RTM_GETADDRLABEL);
    PyModule_AddIntMacro(m, RTM_GETDCB);
    PyModule_AddIntMacro(m, RTM_SETDCB);
    PyModule_AddIntMacro(m, RTM_NEWNETCONF);
    PyModule_AddIntMacro(m, RTM_DELNETCONF);
    PyModule_AddIntMacro(m, RTM_GETNETCONF);
    PyModule_AddIntMacro(m, RTM_NEWMDB);
    PyModule_AddIntMacro(m, RTM_DELMDB);
    PyModule_AddIntMacro(m, RTM_GETMDB);
    PyModule_AddIntMacro(m, RTM_NEWNSID);
    PyModule_AddIntMacro(m, RTM_DELNSID);
    PyModule_AddIntMacro(m, RTM_GETNSID);
    PyModule_AddIntMacro(m, RTM_NEWSTATS);
    PyModule_AddIntMacro(m, RTM_GETSTATS);
#ifdef RTM_SETSTATS
    PyModule_AddIntMacro(m, RTM_SETSTATS);
#endif
    PyModule_AddIntMacro(m, RTM_NEWCACHEREPORT);
    PyModule_AddIntMacro(m, RTM_NEWCHAIN);
    PyModule_AddIntMacro(m, RTM_DELCHAIN);
    PyModule_AddIntMacro(m, RTM_GETCHAIN);
    PyModule_AddIntMacro(m, RTM_NEWNEXTHOP);
    PyModule_AddIntMacro(m, RTM_DELNEXTHOP);
    PyModule_AddIntMacro(m, RTM_GETNEXTHOP);
    PyModule_AddIntMacro(m, RTM_NEWLINKPROP);
    PyModule_AddIntMacro(m, RTM_DELLINKPROP);
    PyModule_AddIntMacro(m, RTM_GETLINKPROP);
    PyModule_AddIntMacro(m, RTM_NEWNVLAN);
    PyModule_AddIntMacro(m, RTM_DELVLAN);
    PyModule_AddIntMacro(m, RTM_GETVLAN);
    PyModule_AddIntMacro(m, RTM_NEWNEXTHOPBUCKET);
    PyModule_AddIntMacro(m, RTM_DELNEXTHOPBUCKET);
    PyModule_AddIntMacro(m, RTM_GETNEXTHOPBUCKET);
#ifdef RTM_NEWTUNNEL
    PyModule_AddIntMacro(m, RTM_NEWTUNNEL);
    PyModule_AddIntMacro(m, RTM_DELTUNNEL);
    PyModule_AddIntMacro(m, RTM_GETTUNNEL);
#endif

    /* Route types for rtmsg rtm_type */
	PyModule_AddIntMacro(m, RTN_UNSPEC);
	PyModule_AddIntMacro(m, RTN_UNICAST);
	PyModule_AddIntMacro(m, RTN_LOCAL);
	PyModule_AddIntMacro(m, RTN_BROADCAST);
	PyModule_AddIntMacro(m, RTN_ANYCAST);
	PyModule_AddIntMacro(m, RTN_MULTICAST);
	PyModule_AddIntMacro(m, RTN_BLACKHOLE);
	PyModule_AddIntMacro(m, RTN_UNREACHABLE);
	PyModule_AddIntMacro(m, RTN_PROHIBIT);
	PyModule_AddIntMacro(m, RTN_THROW);
	PyModule_AddIntMacro(m, RTN_NAT);
	PyModule_AddIntMacro(m, RTN_XRESOLVE);

    /* Base protocols for rtmsg rtm_protocol */
    PyModule_AddIntMacro(m, RTPROT_UNSPEC);
    PyModule_AddIntMacro(m, RTPROT_REDIRECT);
    PyModule_AddIntMacro(m, RTPROT_KERNEL);
    PyModule_AddIntMacro(m, RTPROT_BOOT);
    PyModule_AddIntMacro(m, RTPROT_STATIC);
    PyModule_AddIntMacro(m, RTPROT_GATED);
    PyModule_AddIntMacro(m, RTPROT_RA);
    PyModule_AddIntMacro(m, RTPROT_MRT);
    PyModule_AddIntMacro(m, RTPROT_ZEBRA);
    PyModule_AddIntMacro(m, RTPROT_BIRD);
    PyModule_AddIntMacro(m, RTPROT_DNROUTED);
    PyModule_AddIntMacro(m, RTPROT_XORP);
    PyModule_AddIntMacro(m, RTPROT_NTK);
    PyModule_AddIntMacro(m, RTPROT_DHCP);
    PyModule_AddIntMacro(m, RTPROT_MROUTED);
    PyModule_AddIntMacro(m, RTPROT_KEEPALIVED);
    PyModule_AddIntMacro(m, RTPROT_BABEL);
    PyModule_AddIntMacro(m, RTPROT_OPENR);
    PyModule_AddIntMacro(m, RTPROT_BGP);
    PyModule_AddIntMacro(m, RTPROT_ISIS);
    PyModule_AddIntMacro(m, RTPROT_OSPF);
    PyModule_AddIntMacro(m, RTPROT_RIP);
    PyModule_AddIntMacro(m, RTPROT_EIGRP);

    /* Scopes for rtmsg rtm_scope */
	PyModule_AddIntMacro(m, RT_SCOPE_UNIVERSE);
	PyModule_AddIntMacro(m, RT_SCOPE_SITE);
	PyModule_AddIntMacro(m, RT_SCOPE_LINK);
	PyModule_AddIntMacro(m, RT_SCOPE_HOST);
	PyModule_AddIntMacro(m, RT_SCOPE_NOWHERE);

    /* Flags for rtmsg rtm_flags */
    PyModule_AddIntMacro(m, RTM_F_NOTIFY);
    PyModule_AddIntMacro(m, RTM_F_CLONED);
    PyModule_AddIntMacro(m, RTM_F_EQUALIZE);
    PyModule_AddIntMacro(m, RTM_F_PREFIX);
    PyModule_AddIntMacro(m, RTM_F_LOOKUP_TABLE);
    PyModule_AddIntMacro(m, RTM_F_FIB_MATCH);
    PyModule_AddIntMacro(m, RTM_F_OFFLOAD);
    PyModule_AddIntMacro(m, RTM_F_TRAP);
    PyModule_AddIntMacro(m, RTM_F_OFFLOAD_FAILED);

    /* Reserved tables for rtmsg rtm_table */
	PyModule_AddIntMacro(m, RT_TABLE_UNSPEC);
	PyModule_AddIntMacro(m, RT_TABLE_COMPAT);
	PyModule_AddIntMacro(m, RT_TABLE_DEFAULT);
	PyModule_AddIntMacro(m, RT_TABLE_MAIN);
	PyModule_AddIntMacro(m, RT_TABLE_LOCAL);
	PyModule_AddIntMacro(m, RT_TABLE_MAX);

    /* rtmsg attributes */
	PyModule_AddIntMacro(m, RTA_UNSPEC);
	PyModule_AddIntMacro(m, RTA_DST);
	PyModule_AddIntMacro(m, RTA_SRC);
	PyModule_AddIntMacro(m, RTA_IIF);
	PyModule_AddIntMacro(m, RTA_OIF);
	PyModule_AddIntMacro(m, RTA_GATEWAY);
	PyModule_AddIntMacro(m, RTA_PRIORITY);
	PyModule_AddIntMacro(m, RTA_PREFSRC);
	PyModule_AddIntMacro(m, RTA_METRICS);
	PyModule_AddIntMacro(m, RTA_MULTIPATH);
	PyModule_AddIntMacro(m, RTA_PROTOINFO);
	PyModule_AddIntMacro(m, RTA_FLOW);
	PyModule_AddIntMacro(m, RTA_CACHEINFO);
	PyModule_AddIntMacro(m, RTA_SESSION);
	PyModule_AddIntMacro(m, RTA_MP_ALGO);
	PyModule_AddIntMacro(m, RTA_TABLE);
	PyModule_AddIntMacro(m, RTA_MARK);
	PyModule_AddIntMacro(m, RTA_MFC_STATS);
	PyModule_AddIntMacro(m, RTA_VIA);
	PyModule_AddIntMacro(m, RTA_NEWDST);
	PyModule_AddIntMacro(m, RTA_PREF);
	PyModule_AddIntMacro(m, RTA_ENCAP_TYPE);
	PyModule_AddIntMacro(m, RTA_ENCAP);
	PyModule_AddIntMacro(m, RTA_EXPIRES);
	PyModule_AddIntMacro(m, RTA_PAD);
	PyModule_AddIntMacro(m, RTA_UID);
	PyModule_AddIntMacro(m, RTA_TTL_PROPAGATE);
	PyModule_AddIntMacro(m, RTA_IP_PROTO);
	PyModule_AddIntMacro(m, RTA_SPORT);
	PyModule_AddIntMacro(m, RTA_DPORT);
	PyModule_AddIntMacro(m, RTA_NH_ID);

    /* Flags for rtnexthop rtnh_flags */
    PyModule_AddIntMacro(m, RTNH_F_DEAD);
    PyModule_AddIntMacro(m, RTNH_F_PERVASIVE);
    PyModule_AddIntMacro(m, RTNH_F_ONLINK);
    PyModule_AddIntMacro(m, RTNH_F_OFFLOAD);
    PyModule_AddIntMacro(m, RTNH_F_LINKDOWN);
    PyModule_AddIntMacro(m, RTNH_F_UNRESOLVED);
    PyModule_AddIntMacro(m, RTNH_F_TRAP);
    PyModule_AddIntMacro(m, RTNH_COMPARE_MASK);

    /* RTA_METRICS sub-attributes */
	PyModule_AddIntMacro(m, RTAX_UNSPEC);
	PyModule_AddIntMacro(m, RTAX_LOCK);
	PyModule_AddIntMacro(m, RTAX_MTU);
	PyModule_AddIntMacro(m, RTAX_WINDOW);
	PyModule_AddIntMacro(m, RTAX_RTT);
	PyModule_AddIntMacro(m, RTAX_RTTVAR);
	PyModule_AddIntMacro(m, RTAX_SSTHRESH);
	PyModule_AddIntMacro(m, RTAX_CWND);
	PyModule_AddIntMacro(m, RTAX_ADVMSS);
	PyModule_AddIntMacro(m, RTAX_REORDERING);
	PyModule_AddIntMacro(m, RTAX_HOPLIMIT);
	PyModule_AddIntMacro(m, RTAX_INITCWND);
	PyModule_AddIntMacro(m, RTAX_FEATURES);
	PyModule_AddIntMacro(m, RTAX_RTO_MIN);
	PyModule_AddIntMacro(m, RTAX_INITRWND);
	PyModule_AddIntMacro(m, RTAX_QUICKACK);
	PyModule_AddIntMacro(m, RTAX_CC_ALGO);
	PyModule_AddIntMacro(m, RTAX_FASTOPEN_NO_COOKIE);
    PyModule_AddIntMacro(m, RTAX_FEATURE_ECN);
    PyModule_AddIntMacro(m, RTAX_FEATURE_SACK);
    PyModule_AddIntMacro(m, RTAX_FEATURE_TIMESTAMP);
    PyModule_AddIntMacro(m, RTAX_FEATURE_ALLFRAG);
#ifdef RTAX_FEATURE_TCP_USEC_TS
    PyModule_AddIntMacro(m, RTAX_FEATURE_TCP_USEC_TS);
#endif
    PyModule_AddIntMacro(m, RTAX_FEATURE_MASK);

    /* ifinfomsg attributes */
    PyModule_AddIntMacro(m, IFLA_UNSPEC);
    PyModule_AddIntMacro(m, IFLA_ADDRESS);
    PyModule_AddIntMacro(m, IFLA_BROADCAST);
    PyModule_AddIntMacro(m, IFLA_IFNAME);
    PyModule_AddIntMacro(m, IFLA_MTU);
    PyModule_AddIntMacro(m, IFLA_LINK);
    PyModule_AddIntMacro(m, IFLA_QDISC);
    PyModule_AddIntMacro(m, IFLA_STATS);
    PyModule_AddIntMacro(m, IFLA_COST);
    PyModule_AddIntMacro(m, IFLA_PRIORITY);
    PyModule_AddIntMacro(m, IFLA_MASTER);
    PyModule_AddIntMacro(m, IFLA_WIRELESS);
    PyModule_AddIntMacro(m, IFLA_PROTINFO);
    PyModule_AddIntMacro(m, IFLA_TXQLEN);
    PyModule_AddIntMacro(m, IFLA_MAP);
    PyModule_AddIntMacro(m, IFLA_WEIGHT);
    PyModule_AddIntMacro(m, IFLA_OPERSTATE);
    PyModule_AddIntMacro(m, IFLA_LINKMODE);
    PyModule_AddIntMacro(m, IFLA_LINKINFO);
    PyModule_AddIntMacro(m, IFLA_NET_NS_PID);
    PyModule_AddIntMacro(m, IFLA_IFALIAS);
    PyModule_AddIntMacro(m, IFLA_NUM_VF);
    PyModule_AddIntMacro(m, IFLA_VFINFO_LIST);
    PyModule_AddIntMacro(m, IFLA_STATS64);
    PyModule_AddIntMacro(m, IFLA_VF_PORTS);
    PyModule_AddIntMacro(m, IFLA_PORT_SELF);
    PyModule_AddIntMacro(m, IFLA_AF_SPEC);
    PyModule_AddIntMacro(m, IFLA_GROUP);
    PyModule_AddIntMacro(m, IFLA_NET_NS_FD);
    PyModule_AddIntMacro(m, IFLA_EXT_MASK);
    PyModule_AddIntMacro(m, IFLA_PROMISCUITY);
    PyModule_AddIntMacro(m, IFLA_NUM_TX_QUEUES);
    PyModule_AddIntMacro(m, IFLA_NUM_RX_QUEUES);
    PyModule_AddIntMacro(m, IFLA_CARRIER);
    PyModule_AddIntMacro(m, IFLA_PHYS_PORT_ID);
    PyModule_AddIntMacro(m, IFLA_CARRIER_CHANGES);
    PyModule_AddIntMacro(m, IFLA_PHYS_SWITCH_ID);
    PyModule_AddIntMacro(m, IFLA_LINK_NETNSID);
    PyModule_AddIntMacro(m, IFLA_PHYS_PORT_NAME);
    PyModule_AddIntMacro(m, IFLA_PROTO_DOWN);
    PyModule_AddIntMacro(m, IFLA_GSO_MAX_SEGS);
    PyModule_AddIntMacro(m, IFLA_GSO_MAX_SIZE);
    PyModule_AddIntMacro(m, IFLA_PAD);
    PyModule_AddIntMacro(m, IFLA_XDP);
    PyModule_AddIntMacro(m, IFLA_EVENT);
    PyModule_AddIntMacro(m, IFLA_NEW_NETNSID);
    PyModule_AddIntMacro(m, IFLA_IF_NETNSID);
    PyModule_AddIntMacro(m, IFLA_TARGET_NETNSID);
    PyModule_AddIntMacro(m, IFLA_CARRIER_UP_COUNT);
    PyModule_AddIntMacro(m, IFLA_CARRIER_DOWN_COUNT);
    PyModule_AddIntMacro(m, IFLA_NEW_IFINDEX);
    PyModule_AddIntMacro(m, IFLA_MIN_MTU);
    PyModule_AddIntMacro(m, IFLA_MAX_MTU);
    PyModule_AddIntMacro(m, IFLA_PROP_LIST);
    PyModule_AddIntMacro(m, IFLA_ALT_IFNAME);
    PyModule_AddIntMacro(m, IFLA_PERM_ADDRESS);
    PyModule_AddIntMacro(m, IFLA_PROTO_DOWN_REASON);
    PyModule_AddIntMacro(m, IFLA_PARENT_DEV_NAME);
    PyModule_AddIntMacro(m, IFLA_PARENT_DEV_BUS_NAME);

    /* IFLA_LINKINFO sub-attributes */
    PyModule_AddIntMacro(m, IFLA_INFO_UNSPEC);
    PyModule_AddIntMacro(m, IFLA_INFO_KIND);
    PyModule_AddIntMacro(m, IFLA_INFO_DATA);
    PyModule_AddIntMacro(m, IFLA_INFO_XSTATS);
    PyModule_AddIntMacro(m, IFLA_INFO_SLAVE_KIND);
    PyModule_AddIntMacro(m, IFLA_INFO_SLAVE_DATA);

    /* Operational state */
    PyModule_AddIntMacro(m, IF_OPER_UNKNOWN);
    PyModule_AddIntMacro(m, IF_OPER_NOTPRESENT);
    PyModule_AddIntMacro(m, IF_OPER_DOWN);
    PyModule_AddIntMacro(m, IF_OPER_LOWERLAYERDOWN);
    PyModule_AddIntMacro(m, IF_OPER_TESTING);
    PyModule_AddIntMacro(m, IF_OPER_DORMANT);
    PyModule_AddIntMacro(m, IF_OPER_UP);

    /* ifi_type constants */
    PyModule_AddIntMacro(m, ARPHRD_NETROM);
    PyModule_AddIntMacro(m, ARPHRD_ETHER);
    PyModule_AddIntMacro(m, ARPHRD_EETHER);
    PyModule_AddIntMacro(m, ARPHRD_AX25);
    PyModule_AddIntMacro(m, ARPHRD_PRONET);
    PyModule_AddIntMacro(m, ARPHRD_CHAOS);
    PyModule_AddIntMacro(m, ARPHRD_IEEE802);
    PyModule_AddIntMacro(m, ARPHRD_ARCNET);
    PyModule_AddIntMacro(m, ARPHRD_APPLETLK);
    PyModule_AddIntMacro(m, ARPHRD_DLCI);
    PyModule_AddIntMacro(m, ARPHRD_ATM);
    PyModule_AddIntMacro(m, ARPHRD_METRICOM);
    PyModule_AddIntMacro(m, ARPHRD_IEEE1394);
    PyModule_AddIntMacro(m, ARPHRD_EUI64);
    PyModule_AddIntMacro(m, ARPHRD_INFINIBAND);
    PyModule_AddIntMacro(m, ARPHRD_SLIP);
    PyModule_AddIntMacro(m, ARPHRD_CSLIP);
    PyModule_AddIntMacro(m, ARPHRD_SLIP6);
    PyModule_AddIntMacro(m, ARPHRD_CSLIP6);
    PyModule_AddIntMacro(m, ARPHRD_RSRVD);
    PyModule_AddIntMacro(m, ARPHRD_ADAPT);
    PyModule_AddIntMacro(m, ARPHRD_ROSE);
    PyModule_AddIntMacro(m, ARPHRD_X25);
    PyModule_AddIntMacro(m, ARPHRD_HWX25);
    PyModule_AddIntMacro(m, ARPHRD_CAN);
    PyModule_AddIntMacro(m, ARPHRD_PPP);
    PyModule_AddIntMacro(m, ARPHRD_CISCO);
    PyModule_AddIntMacro(m, ARPHRD_HDLC);
    PyModule_AddIntMacro(m, ARPHRD_LAPB);
    PyModule_AddIntMacro(m, ARPHRD_DDCMP);
    PyModule_AddIntMacro(m, ARPHRD_RAWHDLC);
    PyModule_AddIntMacro(m, ARPHRD_RAWIP);
    PyModule_AddIntMacro(m, ARPHRD_TUNNEL);
    PyModule_AddIntMacro(m, ARPHRD_TUNNEL6);
    PyModule_AddIntMacro(m, ARPHRD_FRAD);
    PyModule_AddIntMacro(m, ARPHRD_SKIP);
    PyModule_AddIntMacro(m, ARPHRD_LOOPBACK);
    PyModule_AddIntMacro(m, ARPHRD_LOCALTLK);
    PyModule_AddIntMacro(m, ARPHRD_FDDI);
    PyModule_AddIntMacro(m, ARPHRD_BIF);
    PyModule_AddIntMacro(m, ARPHRD_SIT);
    PyModule_AddIntMacro(m, ARPHRD_IPDDP);
    PyModule_AddIntMacro(m, ARPHRD_IPGRE);
    PyModule_AddIntMacro(m, ARPHRD_PIMREG);
    PyModule_AddIntMacro(m, ARPHRD_HIPPI);
    PyModule_AddIntMacro(m, ARPHRD_ASH);
    PyModule_AddIntMacro(m, ARPHRD_ECONET);
    PyModule_AddIntMacro(m, ARPHRD_IRDA);
    PyModule_AddIntMacro(m, ARPHRD_FCPP);
    PyModule_AddIntMacro(m, ARPHRD_FCAL);
    PyModule_AddIntMacro(m, ARPHRD_FCPL);
    PyModule_AddIntMacro(m, ARPHRD_FCFABRIC);
    PyModule_AddIntMacro(m, ARPHRD_IEEE802_TR);
    PyModule_AddIntMacro(m, ARPHRD_IEEE80211);
    PyModule_AddIntMacro(m, ARPHRD_IEEE80211_PRISM);
    PyModule_AddIntMacro(m, ARPHRD_IEEE80211_RADIOTAP);
    PyModule_AddIntMacro(m, ARPHRD_IEEE802154);
    PyModule_AddIntMacro(m, ARPHRD_IEEE802154_MONITOR);
    PyModule_AddIntMacro(m, ARPHRD_PHONET);
    PyModule_AddIntMacro(m, ARPHRD_PHONET_PIPE);
    PyModule_AddIntMacro(m, ARPHRD_CAIF);
    PyModule_AddIntMacro(m, ARPHRD_IP6GRE);
    PyModule_AddIntMacro(m, ARPHRD_NETLINK);
    PyModule_AddIntMacro(m, ARPHRD_6LOWPAN);
    PyModule_AddIntMacro(m, ARPHRD_VSOCKMON);
    PyModule_AddIntMacro(m, ARPHRD_VOID);
    PyModule_AddIntMacro(m, ARPHRD_NONE);

    /* Interface flags */
    PyModule_AddIntMacro(m, IFF_UP);
    PyModule_AddIntMacro(m, IFF_BROADCAST);
    PyModule_AddIntMacro(m, IFF_DEBUG);
    PyModule_AddIntMacro(m, IFF_LOOPBACK);
    PyModule_AddIntMacro(m, IFF_POINTOPOINT);
    PyModule_AddIntMacro(m, IFF_NOTRAILERS);
    PyModule_AddIntMacro(m, IFF_RUNNING);
    PyModule_AddIntMacro(m, IFF_NOARP);
    PyModule_AddIntMacro(m, IFF_PROMISC);
    PyModule_AddIntMacro(m, IFF_ALLMULTI);
    PyModule_AddIntMacro(m, IFF_MASTER);
    PyModule_AddIntMacro(m, IFF_SLAVE);
    PyModule_AddIntMacro(m, IFF_MULTICAST);
    PyModule_AddIntMacro(m, IFF_PORTSEL);
    PyModule_AddIntMacro(m, IFF_AUTOMEDIA);
    PyModule_AddIntMacro(m, IFF_DYNAMIC);
    PyModule_AddIntMacro(m, IFF_LOWER_UP);
    PyModule_AddIntMacro(m, IFF_DORMANT);
    PyModule_AddIntMacro(m, IFF_ECHO);

    /* prefixmsg families */
	PyModule_AddIntMacro(m, PREFIX_UNSPEC);
	PyModule_AddIntMacro(m, PREFIX_ADDRESS);
	PyModule_AddIntMacro(m, PREFIX_CACHEINFO);

    /* tcmsg attributes */
	PyModule_AddIntMacro(m, TCA_UNSPEC);
	PyModule_AddIntMacro(m, TCA_KIND);
	PyModule_AddIntMacro(m, TCA_OPTIONS);
	PyModule_AddIntMacro(m, TCA_STATS);
	PyModule_AddIntMacro(m, TCA_XSTATS);
	PyModule_AddIntMacro(m, TCA_RATE);
	PyModule_AddIntMacro(m, TCA_FCNT);
	PyModule_AddIntMacro(m, TCA_STATS2);
	PyModule_AddIntMacro(m, TCA_STAB);
	PyModule_AddIntMacro(m, TCA_PAD);
	PyModule_AddIntMacro(m, TCA_DUMP_INVISIBLE);
	PyModule_AddIntMacro(m, TCA_CHAIN);
	PyModule_AddIntMacro(m, TCA_HW_OFFLOAD);
	PyModule_AddIntMacro(m, TCA_INGRESS_BLOCK);
	PyModule_AddIntMacro(m, TCA_EGRESS_BLOCK);
	PyModule_AddIntMacro(m, TCA_DUMP_FLAGS);
#ifdef TCA_EXT_WARN_MSG
	PyModule_AddIntMacro(m, TCA_EXT_WARN_MSG);
#endif

    /* tcmsg dump flags */
    PyModule_AddIntMacro(m, TCA_DUMP_FLAGS_TERSE);

    /* nduseropt family */
	PyModule_AddIntMacro(m, NDUSEROPT_UNSPEC);
	PyModule_AddIntMacro(m, NDUSEROPT_SRCADDR);

    /* rtnetlink multicast groups */
    PyModule_AddIntMacro(m, RTMGRP_LINK);
    PyModule_AddIntMacro(m, RTMGRP_NOTIFY);
    PyModule_AddIntMacro(m, RTMGRP_NEIGH);
    PyModule_AddIntMacro(m, RTMGRP_TC);
    PyModule_AddIntMacro(m, RTMGRP_IPV4_IFADDR);
    PyModule_AddIntMacro(m, RTMGRP_IPV4_MROUTE);
    PyModule_AddIntMacro(m, RTMGRP_IPV4_ROUTE);
    PyModule_AddIntMacro(m, RTMGRP_IPV4_RULE);
    PyModule_AddIntMacro(m, RTMGRP_IPV6_IFADDR);
    PyModule_AddIntMacro(m, RTMGRP_IPV6_MROUTE);
    PyModule_AddIntMacro(m, RTMGRP_IPV6_ROUTE);
    PyModule_AddIntMacro(m, RTMGRP_IPV6_IFINFO);
    PyModule_AddIntMacro(m, RTMGRP_DECnet_IFADDR);
    PyModule_AddIntMacro(m, RTMGRP_DECnet_ROUTE);
    PyModule_AddIntMacro(m, RTMGRP_IPV6_PREFIX);
    PyModule_AddIntMacro(m, RTNLGRP_NONE);
    PyModule_AddIntMacro(m, RTNLGRP_LINK);
    PyModule_AddIntMacro(m, RTNLGRP_NOTIFY);
    PyModule_AddIntMacro(m, RTNLGRP_NEIGH);
    PyModule_AddIntMacro(m, RTNLGRP_TC);
    PyModule_AddIntMacro(m, RTNLGRP_IPV4_IFADDR);
    PyModule_AddIntMacro(m, RTNLGRP_IPV4_MROUTE);
    PyModule_AddIntMacro(m, RTNLGRP_IPV4_ROUTE);
    PyModule_AddIntMacro(m, RTNLGRP_IPV4_RULE);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_IFADDR);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_MROUTE);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_ROUTE);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_IFINFO);
    PyModule_AddIntMacro(m, RTNLGRP_DECnet_IFADDR);
    PyModule_AddIntMacro(m, RTNLGRP_DECnet_ROUTE);
    PyModule_AddIntMacro(m, RTNLGRP_DECnet_RULE);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_PREFIX);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_RULE);
    PyModule_AddIntMacro(m, RTNLGRP_ND_USEROPT);
    PyModule_AddIntMacro(m, RTNLGRP_PHONET_IFADDR);
    PyModule_AddIntMacro(m, RTNLGRP_PHONET_ROUTE);
    PyModule_AddIntMacro(m, RTNLGRP_DCB);
    PyModule_AddIntMacro(m, RTNLGRP_IPV4_NETCONF);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_NETCONF);
    PyModule_AddIntMacro(m, RTNLGRP_MDB);
    PyModule_AddIntMacro(m, RTNLGRP_MPLS_ROUTE);
    PyModule_AddIntMacro(m, RTNLGRP_NSID);
    PyModule_AddIntMacro(m, RTNLGRP_MPLS_NETCONF);
    PyModule_AddIntMacro(m, RTNLGRP_IPV4_MROUTE_R);
    PyModule_AddIntMacro(m, RTNLGRP_IPV6_MROUTE_R);
    PyModule_AddIntMacro(m, RTNLGRP_NEXTHOP);
    PyModule_AddIntMacro(m, RTNLGRP_BRVLAN);
#ifdef RTNLGRP_MCTP_IFADDR
    PyModule_AddIntMacro(m, RTNLGRP_MCTP_IFADDR);
#endif
#ifdef RTNLGRP_TUNNEL
    PyModule_AddIntMacro(m, RTNLGRP_TUNNEL);
#endif
#ifdef RTNLGRP_STATS
    PyModule_AddIntMacro(m, RTNLGRP_STATS);
#endif

    /* tcamsg tca_family */
	PyModule_AddIntMacro(m, TCA_ROOT_UNSPEC);
	PyModule_AddIntMacro(m, TCA_ROOT_TAB);
    PyModule_AddIntMacro(m, TCA_ACT_TAB);
	PyModule_AddIntMacro(m, TCA_ROOT_FLAGS);
	PyModule_AddIntMacro(m, TCA_ROOT_COUNT);
	PyModule_AddIntMacro(m, TCA_ROOT_TIME_DELTA);
#ifdef TCA_ROOT_EXT_WARN_MSG
	PyModule_AddIntMacro(m, TCA_ROOT_EXT_WARN_MSG);
#endif

    /* tcamsg dump flags */
    PyModule_AddIntMacro(m, TCA_FLAG_LARGE_DUMP_ON);
    PyModule_AddIntMacro(m, TCA_ACT_FLAG_LARGE_DUMP_ON);
    PyModule_AddIntMacro(m, TCA_ACT_FLAG_TERSE_DUMP);

    /* IFLA_EXT_MASK filters */
    PyModule_AddIntMacro(m, RTEXT_FILTER_VF);
    PyModule_AddIntMacro(m, RTEXT_FILTER_BRVLAN);
    PyModule_AddIntMacro(m, RTEXT_FILTER_BRVLAN_COMPRESSED);
    PyModule_AddIntMacro(m, RTEXT_FILTER_SKIP_STATS);
    PyModule_AddIntMacro(m, RTEXT_FILTER_MRP);
    PyModule_AddIntMacro(m, RTEXT_FILTER_CFM_CONFIG);
    PyModule_AddIntMacro(m, RTEXT_FILTER_CFM_STATUS);
#ifdef RTEXT_FILTER_MST
    PyModule_AddIntMacro(m, RTEXT_FILTER_MST);
#endif

    return m;
}

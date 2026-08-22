# Netlink Module Implementation Status

Branch `v0.3`. The old `routesia/rtnetlink` package has been removed. The new
stack lives in `routesia/netlink/` (core) and `routesia/netlink/rtnetlink/`
(message types and operations), built on the `routesia/protoclass` declarative
protocol framework (C extension `_cprotoclass.c` + pure-Python fallback,
committed in `6191383`).

**Overall: the protocol layer is roughly half done, but the branch is not
functional. The agent cannot start from this tree — see the blocker below.**

## Blocker: service/provider layer not migrated

`IPRouteProvider` (old top-level `netlinkprovider.py`) was deleted in `6191383`,
and the new `*_operations.py` modules are not wired into any provider yet. The
following files fail to import:

| File | Failure |
| --- | --- |
| `routesia/programs/routesia_agent.py` | `ModuleNotFoundError: routesia.netlink.netlinkprovider` |
| `routesia/interface/addressprovider.py` | `ModuleNotFoundError: routesia.netlink.netlinkprovider` / `netlinkevents` |
| `routesia/interface/interfaceprovider.py` | `NameError: IPRouteProvider` (import removed, annotation on line 48 remains) |
| `routesia/route/routeprovider.py` | `ModuleNotFoundError: routesia.netlink.netlinkprovider` / `netlinkevents` |
| `routesia/address/provider.py` | `ModuleNotFoundError: routesia.netlink.netlinkprovider` / `netlinkevents` |
| `routesia/dhcp/dhcpserverprovider.py` | `ModuleNotFoundError: routesia.netlink.netlinkevents` |
| `routesia/dns/cache/provider.py` | `ModuleNotFoundError: routesia.netlink.events` |
| `routesia/dns/dnscacheprovider.py` | `ModuleNotFoundError: routesia.netlink.netlinkevents` |
| `routesia/dns/authoritativednsprovider.py` | `ModuleNotFoundError: routesia.netlink.netlinkevents` |

Notes:

- Consumers expect the events under three different module names
  (`netlink.netlinkevents`, `netlink.events`) — the replacement module should
  settle on one.
- The old event code survives at top-level `routesia/rtnetlinkevents.py`
  (renamed from `netlinkevents.py` in `6191383`, content unchanged) and is not
  used by anything.
- The running router is unaffected: the live agent executes the installed
  `routesia-0.2.1` egg from site-packages, not this branch.

### Test harness fallout

- `tests/interface/test_interface.py` (7 tests): requires a `netlink_provider`
  fixture that was removed from `tests/conftest_providers.py` in `6191383`.
- `tests/cli/`, `tests/test_mqtt.py`, `tests/test_rpc.py` (41 tests): fixtures
  call `service.get_provider()` before `load_providers()` has run, so
  providers are not yet registered (`KeyError`).

### Test totals (working tree, python3.11)

- `tests/netlink` + `tests/protoclass`: **321 passed**
- rest of suite: 254 passed, 1 skipped, 48 errors

## Git state

Committed at HEAD (`6191383`): protoclass framework, netlink core
(`message.py`, `socket.py`, `attribute.py`, extended-ACK error handling),
`rtnetlink/{link,link_operations,route,rtnexthop}.py`, top-level
`rtnetlinkprovider.py` / `rtnetlinkevents.py`, removal of the old
`routesia/rtnetlink` package.

Staged, uncommitted: Phases 1 (refinement) – 4 below, plus supporting
protoclass updates (`types.py`, `__init__.py`, `cprotoclass.py`,
`_cprotoclass.c`, README) and `netlink/{socket,attribute}.py`, plus the
restructure of `rtnetlink/{link,address,neighbor,rule,route}` from flat
modules into packages (see Key Patterns). The legacy `rtnexthop.py` module
was absorbed into `route/message.py`.

Unstaged: `tests/protoclass/test_protoclass.py` (Int128 boundary test fix).

## Phases

### Phase 1 ✅ COMPLETE: Extended ACK Error Handling

Staged, uncommitted (a basic `NetlinkErrorMessage` was already committed in
`6191383`; the capped/uncapped split below is the staged work).

- `routesia/netlink/message.py`: `NetlinkMessageHeader`,
  `CappedNetlinkErrorMessage`, `NetlinkErrorMessage`, `NLMSGERRAttribute`,
  and a `NetlinkMessage.error` property that dispatches on `NLM_F_CAPPED`
- Tests: `tests/netlink/test_error_message.py` — passing

### Phase 2 ✅ COMPLETE: Address Management (ifaddrmsg)

Staged, uncommitted.

- `routesia/netlink/rtnetlink/address/message.py` — `IfAddrMessage`
- `routesia/netlink/rtnetlink/address/operations.py` — CRUD operations
- Tests: `tests/netlink/rtnetlink/test_address.py` — passing

### Phase 3 ✅ COMPLETE: Neighbor Management (ndmsg)

Staged, uncommitted.

- `routesia/netlink/rtnetlink/neighbor/message.py` — `NeighbourMessage`
- `routesia/netlink/rtnetlink/neighbor/operations.py` — CRUD operations
- Tests: `tests/netlink/rtnetlink/test_neighbor.py` — passing

### Phase 4 ✅ COMPLETE: Routing Rules (rtfibmsg)

Staged, uncommitted.

- `routesia/netlink/rtnetlink/rule/message.py` — `RuleMessage`
- `routesia/netlink/rtnetlink/rule/operations.py` — CRUD operations
- Tests: `tests/netlink/rtnetlink/test_rule.py` — passing

### Phase 5 ❌ NOT STARTED: Nexthop Objects (nhmsg)

- Direction: use the modern API — independent nexthop objects (`nhmsg`,
  `RTM_NEWNEXTHOP`, `NHA_DST`/`NHA_GATEWAY`, routes referencing them via
  `RTA_NH_ID`).
- Note: the former `rtnexthop.py` module (suspected bad LLM-generated
  artifact) implemented the **legacy rtnh** (multipath) struct. It has been
  absorbed into `route/message.py`, where it is used to parse
  `RTA_MULTIPATH` attributes on existing routes.
- Remaining: `nexthop/` package (operations + message) for the modern API,
  `RTM_NEWNEXTHOP`/`RTM_DELNEXTHOP`/`RTM_GETNEXTHOP` dispatcher entries in
  `message.py`, unit tests

### Phase 6 ❌ NOT STARTED: Traffic Control (tcmsg)

- `routesia/netlink/rtnetlink/tc.py` and `tc_operations.py` do not exist
- No TC entries in the `message.py` type_map

### Phase 7 ❌ NOT STARTED: Route Enhancements

- `route/message.py` has the basic `RouteMessage` (committed, tested),
  including legacy multipath parsing via the rtnh structs
  (`RTNexthop*` classes, used for `RTA_MULTIPATH`)
- Remaining: RouteMetrics nested structure, encap (LWTUNNEL), multipath
  improvements, RTA_EXPIRES / RTA_UID / RTA_TTL_PROPAGATE, and
  `route/operations.py` when route CRUD is built

### Phase 8 ❌ NOT STARTED: Link Enhancements

- `link.py` has the generic structures (committed, tested):
  `InterfaceInfoMessage`, `GenericLinkInfoData`, stats, properties
- Remaining: type-specific info structures — VlanInfo, VxlanInfo, GreInfo,
  SitInfo, IpipInfo, BondInfo, BridgeInfo, VethInfo, VrfInfo, XfrmInfo

### Phase 9 ⏳ PARTIAL: Message Dispatcher

- `message.py` `NetlinkMessage.payload` type_map currently dispatches:
  link, route, address, neighbor, rule; `NLMSG_ERROR` is parsed via the
  `.error` property
- Remaining: nexthop and TC entries

### Phases 10–11 ⏳ PARTIAL: Tests

- Done: unit tests for message, socket, error message, attributes (netlink and
  rtnetlink), link operations, route, address, neighbor, rule — 321 passing
- Remaining: integration tests with a real kernel

### Phase 12 ❌ NOT STARTED: Service/provider integration (blocker)

- Provide the replacement for `IPRouteProvider` on top of the new
  `*_operations.py` modules (link ops exist; address, neighbor, rule ops are
  staged; nexthop/TC ops are missing)
- Migrate the event layer (replace old `rtnetlinkevents.py` consumers) and
  settle on a single module name for the netlink events
- Fix the 9 files listed in the blocker table
- Restore the `netlink_provider` test fixture and fix the provider-fixture
  ordering issue in `tests/conftest_providers.py`

## Key Patterns

1. **All structures use `@protoclass()`**
2. **Each rtnetlink type is a package**: `foo/message.py` holds the one
   message class plus its substructs and attributes; `foo/operations.py`
   holds behavior. `__init__.py` files are empty — no re-exports, imports
   are explicit (`from routesia.netlink.rtnetlink.link.message import ...`).
3. **Use `NetlinkMessageHeader` for embedded headers** (avoids parsing full payload)
4. **Use `TypeMap()` for variable-length fields with type dispatch**
5. **Test both capped and uncapped variants**
6. **All tests must be platform-independent** (handle byte order with `sys.byteorder`)

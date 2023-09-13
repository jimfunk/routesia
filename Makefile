PYTHON_VERSION = 3.11

PROTO_SOURCES := $(shell find routesia* -type f -name '*.proto')
PROTO_MODULES := $(PROTO_SOURCES:%.proto=%_pb2.py)
TEST_PROTO_SOURCES := $(shell find tests* -type f -name '*.proto')
TEST_PROTO_MODULES := $(TEST_PROTO_SOURCES:%.proto=%_pb2.py)
PYTHON_SOURCES := $(shell find routesia* -type f -name '*.py')

PYTHON = python$(PYTHON_VERSION)
PYTEST = pytest-$(PYTHON_VERSION)

all: build

proto: $(PROTO_MODULES)

testproto: $(TEST_PROTO_MODULES)

%_pb2.py: %.proto
	protoc -I. --python_out=. $<

build: setup.py $(PYTHON_SOURCES) proto
	$(PYTHON) setup.py build

test: proto testproto
	$(PYTEST) $(ARGS)

coverage: proto
	$(PYTEST) --cov=routesia $(ARGS)

install: proto
	$(PYTHON) setup.py install
	mv $(DESTDIR)/usr/bin/routesia $(DESTDIR)/usr/sbin/routesia
	mv $(DESTDIR)/usr/bin/rcl $(DESTDIR)/usr/sbin/rcl
	install -d -m 0755 $(DESTDIR)/usr/lib/routesia/
	mv $(DESTDIR)/usr/bin/routesia-dhcpv4-event $(DESTDIR)/usr/lib/routesia/dhcpv4-event
	install -D -m 0644 conf/iproute2/routesia_protos.conf $(DESTDIR)/etc/iproute2/rt_protos.d/routesia.conf
	install -D -m 0644 systemd/routesia.service $(DESTDIR)/usr/lib/systemd/system/routesia.service
	install -D -m 0644 systemd/routesia-dhcpv4-client@.service $(DESTDIR)/usr/lib/systemd/system/routesia-dhcpv4-client@.service

clean:
	rm -rf build $(PROTO_MODULES)

.PHONY: clean build proto install test

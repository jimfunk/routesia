PROTO_SOURCES := $(shell find routesia* -type f -name '*.proto')
PROTO_MODULES := $(PROTO_SOURCES:%.proto=%_pb2.py)
PYTHON_SOURCES := $(shell find routesia* -type f -name '*.py')

PYTHON = python3

all: proto build

proto: $(PROTO_MODULES)

%_pb2.py: %.proto
	protoc --python_out=. $<

build: setup.py $(PYTHON_SOURCES)
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install

clean:
	rm -rf build $(PROTO_MODULES)

.PHONY: clean build proto install

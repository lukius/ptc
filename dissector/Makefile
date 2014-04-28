WIRESHARK_SRC_DIR = /usr/include/wireshark

SRCS   = packet-ptc.c plugin.c
CC     = gcc
OBJS   = $(foreach src, $(SRCS), $(src:.c=.o))

PLUGIN_NAME = packet-ptc

# local installation path
LOCAL_PLUGIN_DIR  = /home/$(shell whoami)/.wireshark/plugins

# determine global installation path (use latest plugin version path)
ifneq ($(wildcard /usr/local/lib/wireshark/plugins),)
	GLOBAL_PLUGIN_DIR_PARTIAL=/usr/local/lib/wireshark/plugins
else ifneq ($(wildcard /usr/lib/wireshark/plugins),)
	GLOBAL_PLUGIN_DIR_PARTIAL=/usr/lib/wireshark/plugins
endif

# Work out if there are version-specific subdirectories
GLOBAL_PLUGIN_DIR_FILES := $(wildcard $(GLOBAL_PLUGIN_DIR_PARTIAL)/*)
GLOBAL_PLUGIN_DIR_SUBDIRS := $(foreach file,$(GLOBAL_PLUGIN_DIR_FILES),$(dir $(wildcard $(file)/.)))
GLOBAL_PLUGIN_DIR_SUBDIRS := $(subst $(GLOBAL_PLUGIN_DIR_PARTIAL)/,,$(GLOBAL_PLUGIN_DIR_SUBDIRS))
GLOBAL_PLUGIN_DIR_SUBDIRS := $(subst /,,$(GLOBAL_PLUGIN_DIR_SUBDIRS))

# Assume that the "last" directory is the one we ant to use if it exists
GLOBAL_PLUGIN_VER := $(lastword $(sort $(GLOBAL_PLUGIN_DIR_SUBDIRS)))

# Create the actual global plugin dir to use
ifneq ($(GLOBAL_PLUGIN_VER),)
	GLOBAL_PLUGIN_DIR=$(GLOBAL_PLUGIN_DIR_PARTIAL)/$(GLOBAL_PLUGIN_VER)
else
	GLOBAL_PLUGIN_DIR=$(GLOBAL_PLUGIN_DIR_PARTIAL)
endif


OSTYPE = $(shell uname)
ifeq ($(OSTYPE),Linux)
ENDIAN=-D_LITTLE_ENDIAN_
endif
ifeq ($(OSTYPE),SunOS)
ENDIAN=-D_BIG_ENDIAN_
endif

INC_GLIB=/usr/include/glib-2.0 #/usr/pubsw/include/glib-2.0/

INC_DIRS   = -I. -I$(INC_GLIB)
CFLAGS = $(INC_DIRS) -DHAVE_CONFIG_H -I$(WIRESHARK_SRC_DIR) -I/usr/local/include -I/usr/local/include -I/usr/local/include/glib-2.0 -I/usr/lib/glib-2.0/include -I/usr/lib/x86_64-linux-gnu/glib-2.0/include -fPIC -DPIC

LDFLAGS = -Wl,--rpath -Wl,/usr/local/lib -Wl,--rpath -Wl,/usr/local/lib -L/usr/local/lib -L$(WIRESHARK_SRC_DIR)/epan -L. -lgmodule-2.0 -ldl -lglib-2.0  -pthread -Wl,--export-dynamic -Wl,-soname -Wl,$(PLUGIN_NAME).so

CFLAGS32 = $(CFLAGS) -m32
LDFLAGS32 = -m32 $(LDFLAGS)

.PHONY: clean install

all: x64 x32

$(PLUGIN_NAME).so : $(OBJS) $(SRCS)
	$(CC) -shared $(OBJS) $(LDFLAGS) -o $@

x64: $(PLUGIN_NAME).so
	mv $(PLUGIN_NAME).so $(PLUGIN_NAME)-x86-64.so

x32: $(SRCS)
	$(CC) $(CFLAGS32) $(PLUGIN_NAME).c -c -o $(PLUGIN_NAME).o
	$(CC) $(CFLAGS32) plugin.c -c -o plugin.o
	$(CC) -shared $(OBJS) $(LDFLAGS32) -o $(PLUGIN_NAME)-x86.so

plugin.c: moduleinfo.h Makefile.am Makefile.common
	$(MAKE) -f Makefile.am

clean:
	rm -f $(PLUGIN) $(OBJS) *.so

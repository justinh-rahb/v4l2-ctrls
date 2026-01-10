TARGET = v4l2-ctrls.py
SRC = v4l2-ctrls.py

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin

all: $(TARGET)

clean:
	rm -f $(TARGET)

$(TARGET): $(SRC)
	cp $(SRC) $(TARGET)
	chmod +x $(TARGET)

install: $(TARGET)
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 $(TARGET) $(DESTDIR)$(BINDIR)/$(TARGET)

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(TARGET)

.PHONY: all clean install uninstall

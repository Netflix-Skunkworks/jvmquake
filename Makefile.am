SUBDIRS = src
ACLOCAL_AMFLAGS = -I m4

.PHONY: test

test:
	make -C tests
	tox -e test
	tox -e test_jvm

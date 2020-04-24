#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])
AC_INIT([jvmquake], [0.1.0], [josephl@netflix.com])
AC_CONFIG_AUX_DIR([build-aux])
AC_CONFIG_HEADERS([src/config.h])
AC_CONFIG_MACRO_DIRS([m4])
AC_CONFIG_SRCDIR([src/jvmquake.c])

# Checks for programs.
AC_PROG_CC

# Checks for libraries.
# FIXME: Replace `main' with a function in `-lrt':
AC_CHECK_LIB([rt], [main])

# Checks for header files.
AC_CHECK_HEADERS([fcntl.h limits.h stdlib.h string.h sys/time.h unistd.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_CHECK_HEADER_STDBOOL

# Checks for library functions.
AC_FUNC_MALLOC
AC_CHECK_FUNCS([clock_gettime memset strchr])

AC_CONFIG_FILES([Makefile src/Makefile])

AX_JNI_INCLUDE_DIR

for JNI_INCLUDE_DIR in $JNI_INCLUDE_DIRS
do
  CPPFLAGS="$CPPFLAGS -I$JNI_INCLUDE_DIR -I$JNI_INCLUDE_DIR/linux"
done

AM_INIT_AUTOMAKE([foreign])
LT_INIT([disable-static])

AX_APPEND_COMPILE_FLAGS([-Wall], [CXXFLAGS])
AX_APPEND_COMPILE_FLAGS([-Werror], [CXXFLAGS])

AC_OUTPUT

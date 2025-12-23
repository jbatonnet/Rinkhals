################################################################################
#
# lv_micropython
#
################################################################################

LV_MICROPYTHON_VERSION = 9fe842956fc51e1df7a7e5e2b691daaaeeda7ca5
LV_MICROPYTHON_SITE = https://github.com/lvgl/lv_micropython
LV_MICROPYTHON_SITE_METHOD = git
LV_MICROPYTHON_GIT_SUBMODULES=YES
# Micropython has a lot of code copied from other projects, and also a number
# of submodules for various libs. However, we don't even clone the submodules,
# and most of the copied code is not used in the unix build.
LV_MICROPYTHON_LICENSE = MIT, BSD-1-Clause, BSD-3-Clause, Zlib
LV_MICROPYTHON_LICENSE_FILES = LICENSE
LV_MICROPYTHON_DEPENDENCIES = host-python3
LV_MICROPYTHON_CPE_ID_VENDOR = micropython

# Use fallback implementation for exception handling on architectures that don't
# have explicit support.
ifeq ($(BR2_i386)$(BR2_x86_64)$(BR2_arm)$(BR2_armeb),)
LV_MICROPYTHON_CFLAGS = -DMICROPY_GCREGS_SETJMP=1
endif

# xtensa has problems with nlr_push, use setjmp based implementation instead
ifeq ($(BR2_xtensa),y)
LV_MICROPYTHON_CFLAGS = -DMICROPY_NLR_SETJMP=1
endif

# When building from a tarball we don't have some of the dependencies that are in
# the git repository as submodules
LV_MICROPYTHON_MAKE_OPTS += \
	VARIANT=lvgl \
	LV_CONF_PATH="$(LV_MICROPYTHON_PKGDIR)lv_conf.h" \
	MICROPY_PY_BTREE=0 \
	MICROPY_PY_USSL=0 \
	CROSS_COMPILE=$(TARGET_CROSS) \
	CFLAGS_EXTRA="$(LV_MICROPYTHON_CFLAGS)" \
	LDFLAGS_EXTRA="$(TARGET_LDFLAGS)" \
	CWARN=

ifeq ($(BR2_PACKAGE_LIBFFI),y)
LV_MICROPYTHON_DEPENDENCIES += host-pkgconf libffi
LV_MICROPYTHON_MAKE_OPTS += MICROPY_PY_FFI=1
else
LV_MICROPYTHON_MAKE_OPTS += MICROPY_PY_FFI=0
endif

define LV_MICROPYTHON_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/mpy-cross
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/ports/unix \
		$(LV_MICROPYTHON_MAKE_OPTS)
endef

define LV_MICROPYTHON_INSTALL_TARGET_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/ports/unix \
		$(LV_MICROPYTHON_MAKE_OPTS) \
		DESTDIR=$(TARGET_DIR) \
		PREFIX=/usr \
		install
endef

ifeq ($(BR2_PACKAGE_LV_MICROPYTHON_LIB),y)
define LV_MICROPYTHON_COLLECT_LIBS
	chmod +x $(LV_MICROPYTHON_PKGDIR)collect_micropython_lib.py
	$(EXTRA_ENV) PYTHONPATH=$(@D)/tools \
		$(LV_MICROPYTHON_PKGDIR)collect_micropython_lib.py \
		$(@D) $(@D)/.built_pylib
endef

define LV_MICROPYTHON_INSTALL_LIBS
	$(INSTALL) -d -m 0755 $(TARGET_DIR)/usr/lib/micropython
	cp -a $(@D)/.built_pylib/* $(TARGET_DIR)/usr/lib/micropython
endef

LV_MICROPYTHON_POST_BUILD_HOOKS += LV_MICROPYTHON_COLLECT_LIBS
LV_MICROPYTHON_POST_INSTALL_TARGET_HOOKS += LV_MICROPYTHON_INSTALL_LIBS
endif

$(eval $(generic-package))

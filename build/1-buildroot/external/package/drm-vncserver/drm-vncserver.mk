DRM_VNCSERVER_VERSION = 002d3b03ceb5e9486c30b39134cf62ee3aca51d1
DRM_VNCSERVER_SITE = https://github.com/basvd/drm-vncserver
DRM_VNCSERVER_SITE_METHOD = git

DRM_VNCSERVER_LICENSE = GPL-2.0+
DRM_VNCSERVER_LICENSE_FILES = LICENSE

DRM_VNCSERVER_DEPENDENCIES = libvncserver libdrm

define DRM_VNCSERVER_BUILD_CMDS
	$(MAKE) $(TARGET_CONFIGURE_OPTS) -C $(@D) \
		CFLAGS="$(TARGET_CFLAGS) -I$(STAGING_DIR)/usr/include/drm" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(STAGING_DIR)/usr/lib -ldrm -lvncserver"
endef

define DRM_VNCSERVER_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/bin/drm-vncserver $(TARGET_DIR)/usr/bin
endef

$(eval $(generic-package))

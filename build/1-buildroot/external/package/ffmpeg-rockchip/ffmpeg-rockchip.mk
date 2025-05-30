FFMPEG_ROCKCHIP_VERSION = 57d5befee96f229b05fa09334a4d7a6f95a324bd
FFMPEG_ROCKCHIP_SITE = https://github.com/nyanmisaka/ffmpeg-rockchip
FFMPEG_ROCKCHIP_SITE_METHOD = git

FFMPEG_ROCKCHIP_DEPENDENCIES = rockchip-mpp rockchip-rga libdrm

define FFMPEG_ROCKCHIP_CONFIGURE_CMDS
	(cd $(@D); rm -f config.cache; \
		./configure \
		--prefix=/usr \
		--enable-gpl \
		--enable-version3 \
		--enable-rkmpp \
		--enable-rkrga \
		--disable-x86asm \
	)
endef

define FFMPEG_ROCKCHIP_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D)
endef

define FFMPEG_ROCKCHIP_INSTALL_TARGET_CMDS
	$(INSTALL)
endef

$(eval $(generic-package))

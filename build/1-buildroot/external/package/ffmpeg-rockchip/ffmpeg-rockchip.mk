FFMPEG_ROCKCHIP_VERSION = 57d5befee96f229b05fa09334a4d7a6f95a324bd
FFMPEG_ROCKCHIP_SITE = https://github.com/nyanmisaka/ffmpeg-rockchip
FFMPEG_ROCKCHIP_SITE_METHOD = git

FFMPEG_ROCKCHIP_DEPENDENCIES = rockchip-mpp rockchip-rga libdrm





FFMPEG_ROCKCHIP_CONF_OPTS = \
	--prefix=/usr \
	--enable-avfilter \
	--enable-logging \
	--enable-optimizations \
	--disable-extra-warnings \
	--enable-avdevice \
	--enable-avcodec \
	--enable-avformat \
	--enable-network \
	--disable-gray \
	--enable-swscale-alpha \
	--disable-small \
	--disable-crystalhd \
	--disable-dxva2 \
	--enable-runtime-cpudetect \
	--disable-hardcoded-tables \
	--disable-mipsdsp \
	--disable-mipsdspr2 \
	--disable-msa \
	--enable-hwaccels \
	--disable-cuda \
	--disable-cuvid \
	--disable-nvenc \
	--disable-avisynth \
	--disable-frei0r \
	--disable-libopencore-amrnb \
	--disable-libopencore-amrwb \
	--disable-libdc1394 \
	--disable-libgsm \
	--disable-libilbc \
	--disable-libvo-amrwbenc \
	--disable-symver \
	--disable-doc

FFMPEG_DEPENDENCIES += host-pkgconf

FFMPEG_ROCKCHIP_CONF_OPTS += --enable-gpl
FFMPEG_ROCKCHIP_CONF_OPTS += --enable-nonfree
FFMPEG_ROCKCHIP_CONF_OPTS += --enable-ffmpeg
#FFMPEG_ROCKCHIP_CONF_OPTS += --enable-libv4l2
#FFMPEG_DEPENDENCIES += libv4l
FFMPEG_ROCKCHIP_CONF_OPTS += --enable-swscale


FFMPEG_ROCKCHIP_CONF_OPTS += --enable-gpl
FFMPEG_ROCKCHIP_CONF_OPTS += --enable-version3
FFMPEG_ROCKCHIP_CONF_OPTS += --enable-libdrm
#FFMPEG_ROCKCHIP_CONF_OPTS += --enable-rkmpp
#FFMPEG_ROCKCHIP_CONF_OPTS += --enable-rkrga

#FFMPEG_ROCKCHIP_CONF_OPTS += --disable-asm



FFMPEG_CFLAGS = $(TARGET_CFLAGS)
FFMPEG_CONF_ENV += CFLAGS="$(FFMPEG_CFLAGS)"


define FFMPEG_ROCKCHIP_CONFIGURE_CMDS
	(cd $(@D) && rm -rf config.cache && \
	$(TARGET_CONFIGURE_OPTS) \
	$(TARGET_CONFIGURE_ARGS) \
	$(FFMPEG_CONF_ENV) \
	./configure \
		--enable-cross-compile \
		--cross-prefix=$(TARGET_CROSS) \
		--sysroot=$(STAGING_DIR) \
		--host-cc="$(HOSTCC)" \
		--arch=$(BR2_ARCH) \
		--target-os="linux" \
		--disable-stripping \
		--pkg-config="$(PKG_CONFIG_HOST_BINARY)" \
		$(SHARED_STATIC_LIBS_OPTS) \
		$(FFMPEG_ROCKCHIP_CONF_OPTS) \
	)
endef

# (cd $(@D); rm -f config.cache; \
# 	./configure \
# 	--prefix=/usr \
# 	--enable-gpl \
# 	--enable-version3 \
# 	--enable-libdrm \
# 	--enable-rkmpp \
# 	--enable-rkrga \
# 	--disable-x86asm \
# )

# define FFMPEG_ROCKCHIP_BUILD_CMDS
# 	$(TARGET_MAKE_ENV) $(MAKE) CC="$(TARGET_CC)" ALLFLAGS_C="$(TARGET_CFLAGS)" \
# 		CXX="$(TARGET_CXX)" ALLFLAGS_CPP="$(TARGET_CXXFLAGS)" \
# 		LDFLAGS="$(TARGET_LDFLAGS)" -C $(@D)
# endef

# define FFMPEG_ROCKCHIP_INSTALL_TARGET_CMDS
# 	$(INSTALL) -D -m 0755 $(@D)/ffmpeg $(TARGET_DIR)/usr/bin/ffmpeg
# endef

$(eval $(autotools-package))
#$(eval $(generic-package))

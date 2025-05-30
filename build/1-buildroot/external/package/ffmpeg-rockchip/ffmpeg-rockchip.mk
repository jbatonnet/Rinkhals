FFMPEG_ROCKCHIP_VERSION = 57d5befee96f229b05fa09334a4d7a6f95a324bd
FFMPEG_ROCKCHIP_SITE = https://github.com/nyanmisaka/ffmpeg-rockchip
FFMPEG_ROCKCHIP_SITE_METHOD = git

FFMPEG_ROCKCHIP_DEPENDENCIES = rockchip-mpp rockchip-rga

define FFMPEG_ROCKCHIP_BUILD_CMDS
	./configure --prefix=/usr --enable-gpl --enable-version3 --enable-libdrm --enable-rkmpp --enable-rkrga
	make -j $(nproc)
endef

define FFMPEG_ROCKCHIP_INSTALL_TARGET_CMDS
	make install
endef

$(eval $(generic-package))

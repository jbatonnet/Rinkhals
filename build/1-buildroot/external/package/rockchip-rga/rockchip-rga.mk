ROCKCHIP_RGA_VERSION = linux-rga-multi
ROCKCHIP_RGA_SITE = https://github.com/nyanmisaka/rk-mirrors
ROCKCHIP_RGA_SITE_METHOD = git

ROCKCHIP_RGA_STAGING = YES
ROCKCHIP_RGA_TARGET = NO

$(eval $(meson-package))

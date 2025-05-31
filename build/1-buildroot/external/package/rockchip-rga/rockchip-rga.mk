ROCKCHIP_RGA_VERSION = linux-rga-multi
ROCKCHIP_RGA_SITE = https://github.com/nyanmisaka/rk-mirrors
ROCKCHIP_RGA_SITE_METHOD = git

ROCKCHIP_RGA_DEPENDENCIES = host-pkgconf
ROCKCHIP_RGA_INSTALL_STAGING = YES

$(eval $(meson-package))

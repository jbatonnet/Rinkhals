ROCKCHIP_MPP_VERSION = develop
ROCKCHIP_MPP_SITE = https://github.com/nyanmisaka/mpp
ROCKCHIP_MPP_SITE_METHOD = git

ROCKCHIP_MPP_DEPENDENCIES = host-pkgconf
ROCKCHIP_MPP_INSTALL_STAGING = YES

$(eval $(cmake-package))

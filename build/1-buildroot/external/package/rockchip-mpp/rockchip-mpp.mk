ROCKCHIP_MPP_VERSION = develop
ROCKCHIP_MPP_SITE = https://github.com/nyanmisaka/mpp
ROCKCHIP_MPP_SITE_METHOD = git

ROCKCHIP_MPP_STAGING = YES
ROCKCHIP_MPP_TARGET = YES

$(eval $(cmake-package))

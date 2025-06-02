# 3e6ff53bf3bd0d9fea31e44838ec437a7d3c6241: before `mpp_frame_set_fbc_hdr_stride`

ROCKCHIP_MPP_VERSION = 34b8a4213f97afbca6c15df6a84f4f6d05767e1c
ROCKCHIP_MPP_SITE = https://github.com/jbatonnet/rockchip-mpp
ROCKCHIP_MPP_SITE_METHOD = git

ROCKCHIP_MPP_DEPENDENCIES = host-pkgconf
ROCKCHIP_MPP_INSTALL_STAGING = YES

$(eval $(cmake-package))

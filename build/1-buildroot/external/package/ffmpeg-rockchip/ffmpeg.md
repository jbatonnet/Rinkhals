ffmpeg.md
---

```
# cd /useremain/tmp/ffmpeg-rockchip

# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -encoders | grep rk
 V..... h264_rkmpp           Rockchip MPP (Media Process Platform) H264 encoder (codec h264)
 V..... hevc_rkmpp           Rockchip MPP (Media Process Platform) HEVC encoder (codec hevc)
 V..... mjpeg_rkmpp          Rockchip MPP (Media Process Platform) MJPEG encoder (codec mjpeg)

# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -decoders | grep rk
 V..... av1_rkmpp            Rockchip MPP (Media Process Platform) AV1 decoder (codec av1)
 V..... h263_rkmpp           Rockchip MPP (Media Process Platform) H263 decoder (codec h263)
 V..... h264_rkmpp           Rockchip MPP (Media Process Platform) H264 decoder (codec h264)
 V..... hevc_rkmpp           Rockchip MPP (Media Process Platform) HEVC decoder (codec hevc)
 V..... mpeg1_rkmpp          Rockchip MPP (Media Process Platform) MPEG1VIDEO decoder (codec mpeg1video)
 V..... mpeg2_rkmpp          Rockchip MPP (Media Process Platform) MPEG2VIDEO decoder (codec mpeg2video)
 V..... mpeg4_rkmpp          Rockchip MPP (Media Process Platform) MPEG4 decoder (codec mpeg4)
 V..... vp8_rkmpp            Rockchip MPP (Media Process Platform) VP8 decoder (codec vp8)
 V..... vp9_rkmpp            Rockchip MPP (Media Process Platform) VP9 decoder (codec vp9)

# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -f v4l2 -list_formats all -i /dev/video10
 [video4linux2,v4l2 @ 0x549b30] Compressed:       mjpeg :          Motion-JPEG : 960x720 1280x720 1024x576 864x480 800x600 640x480 544x288 432x240 320x240 160x120
 [video4linux2,v4l2 @ 0x549b30] Raw       :     yuyv422 :           YUYV 4:2:2 : 1280x720 1024x576 960x720 864x480 800x600 640x480 544x288 432x240 320x240 160x120
```

```
# cd /useremain/tmp/ffmpeg-rockchip

# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -f v4l2 -i /dev/video10 output.mp4
Slow but ok I guess

# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -f v4l2 -i /dev/video10 -c:v h264_rkmpp output.mp4
Crash

# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -f v4l2 -i /dev/video10 -c:v mjpeg_rkmpp output.mp4
Slow, Gray video

# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -f v4l2 -i /dev/video10 -c:v hevc_rkmpp output.mp4
mpp[3911]: mpp: unable to create enc h265 for soc unknown unsupported
```


### mpp:develop

```
mpp[3470]: mpp_info: mpp version: unknown mpp version for missing VCS info
mpp[3470]: mpp: Only rk3588's h264/265/jpeg and rk3576's h264/265 encoder can use frame parallel
mpp[3470]: mpp_platform: can not found match soc name: rockchip,rv1106g-38x38-ipc-v10-spi-nandrockchip,rv1106
mpp[3470]: mpp_platform: client 0 driver is not ready!
mpp[3470]: mpp_platform: client 1 driver is not ready!
mpp[3470]: mpp_platform: client 17 driver is not ready!
mpp[3470]: mpp_platform: client 18 driver is not ready!
mpp[3470]: mpp_enc: MPP_ENC_SET_RC_CFG bps 2000000 [1875000 : 2125000] fps [5:5] gop 250
mpp[3470]: h264e_api_v2: MPP_ENC_SET_PREP_CFG w:h [1280:720] stride [1280:768]
mpp[3470]: mpp_enc: mode cbr bps [1875000:2000000:2125000] fps fix [5/1] -> fix [5/1] gop i [250] v [0]
Output #0, mp4, to 'output.mp4':
  Metadata:
    encoder         : Lavf60.16.100
  Stream #0:0: Video: h264 (High) (avc1 / 0x31637661), yuvj422p(pc, bt470bg/unknown/unknown, progressive), 1280x720, q=2-31, 2000 kb/s, 5 fps, 10240 tbn
    Metadata:
      encoder         : Lavc60.31.102 h264_rkmpp
mpp[3470]: h264e_api_v2: MPP_ENC_SET_PREP_CFG w:h [1280:720] stride [1280:720]
mpp[3470]: mpp_enc: mode cbr bps [1875000:2000000:2125000] fps fix [5/1] -> fix [5/1] gop i [250] v [0]
mpp[3470]: hal_h264e_vepu540c: hal_h264e_vepu540c_status_check bus error
```


### mpp:rv1106-compatibility

```
mpp[2166]: mpp_info: mpp version: unknown mpp version for missing VCS info
mpp[2166]: mpp_soc: Assertion soc_info->vcodec_type == vcodec_type failed at MppSocService:1143
mpp[2166]: mpp: Only rk3588's h264/265/jpeg and rk3576's h264/265 encoder can use frame parallel
mpp[2166]: mpp_platform: client 1 driver is not ready!
mpp[2166]: mpp_platform: client 18 driver is not ready!
mpp[2166]: mpp_enc: MPP_ENC_SET_RC_CFG bps 2000000 [1875000 : 2125000] fps [10:10] gop 250
mpp[2166]: h264e_api_v2: MPP_ENC_SET_PREP_CFG w:h [1280:720] stride [1280:768]
mpp[2166]: mpp_enc: mode cbr bps [1875000:2000000:2125000] fps fix [10/1] -> fix [10/1] gop i [250] v [0]
Output #0, mp4, to 'output.mp4':
  Metadata:
    encoder         : Lavf60.16.100
  Stream #0:0: Video: h264 (High) (avc1 / 0x31637661), yuyv422(progressive), 1280x720, q=2-31, 2000 kb/s, 10 fps, 10240 tbn
    Metadata:
      encoder         : Lavc60.31.102 h264_rkmpp
mpp[2166]: h264e_api_v2: MPP_ENC_SET_PREP_CFG w:h [1280:720] stride [2560:1200]
mpp[2166]: mpp_enc: mode cbr bps [1875000:2000000:2125000] fps fix [10/1] -> fix [10/1] gop i [250] v [0]
```
```
mpp[334]: mpp_info: mpp version: unknown mpp version for missing VCS info
mpp[334]: mpp_soc: chip name: rockchip,rv1106g-38x38-ipc-v10-spi-nand rockchip,rv1106
mpp[334]: mpp_soc: match chip name: rv1106
mpp[334]: mpp_soc: coding caps: dec 00000180 enc 00000180
mpp[334]: mpp_soc: vcodec type from cap: 00050202, from soc_info 00050002
mpp[334]: mpp_soc: Assertion soc_info->vcodec_type == vcodec_type failed at MppSocService:1145
mpp[334]: mpp: Only rk3588's h264/265/jpeg and rk3576's h264/265 encoder can use frame parallel
mpp[334]: mpp_platform: client 1 driver is not ready!
mpp[334]: mpp_platform: client 18 driver is not ready!
mpp[334]: mpp_enc: MPP_ENC_SET_RC_CFG bps 2000000 [1875000 : 2125000] fps [10:10] gop 250
mpp[334]: h264e_api_v2: MPP_ENC_SET_PREP_CFG w:h [1280:720] stride [1280:768]
mpp[334]: mpp_enc: mode cbr bps [1875000:2000000:2125000] fps fix [10/1] -> fix [10/1] gop i [250] v [0]
Output #0, mp4, to 'output2.mp4':
  Metadata:
    encoder         : Lavf60.16.100
  Stream #0:0: Video: h264 (High) (avc1 / 0x31637661), yuyv422(progressive), 1280x720, q=2-31, 2000 kb/s, 10 fps, 10240 tbn
    Metadata:
      encoder         : Lavc60.31.102 h264_rkmpp
mpp[334]: h264e_api_v2: MPP_ENC_SET_PREP_CFG w:h [1280:720] stride [2560:1200]
mpp[334]: mpp_enc: mode cbr bps [1875000:2000000:2125000] fps fix [10/1] -> fix [10/1] gop i [250] v [0]
```











# LD_LIBRARY_PATH=$(pwd) ./ffmpeg -i http://127.0.0.1:8080/?action=stream -r 5 -c copy -f flv -an output.mp4

/ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -frames:v 1 -y /tmp/rinkhals-installer-backup.bmp

LD_LIBRARY_PATH=$(pwd) ./ffmpeg  -c:v h264_rkmpp output.mp4




```

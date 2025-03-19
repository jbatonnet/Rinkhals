# docker build --platform=linux/arm/v7 -t ghcr.io/jbatonnet/rinkhals/rootfs -f build/1-buildroot/rootfs/Dockerfile build/1-buildroot/rootfs
# docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
# docker run --platform=linux/arm/v7 --rm -it -v .\build\cache\pip:/root/.cache/pip -v .\files\4-apps\home\rinkhals\apps\40-moonraker:/files ghcr.io/jbatonnet/rinkhals/rootfs

# For Moonraker for example:
#   cd /files/4-apps/home/rinkhals/apps/40-moonraker
#   python -m venv . # Only the first time
#   source bin/activate
#   python -m pip install -r moonraker/scripts/moonraker-requirements.txt
#   rm -rf bin include .ash_history pyvenv.cfg
#   python -m venv --without-pip . # Before packaging

FROM --platform=linux/arm/v7 scratch

ADD rootfs.tar.gz /
RUN python -m ensurepip

ENV TZ=UTC
ENV LD_LIBRARY_PATH=/lib:/usr/lib:$LD_LIBRARY_PATH
ENV PATH=/bin:/usr/bin:/usr/libexec/gcc/arm-buildroot-linux-uclibcgnueabihf/11.4.0:$PATH
ENV CC=/usr/bin/gcc
ENV CXX=/usr/bin/g++
ENV PYTHONPATH=

CMD ["/bin/sh"]

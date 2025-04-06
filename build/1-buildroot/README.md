# Buildroot stage

This stage is used to cross-compile common binaries/libraries for ARMv7 using Buildroot.

When running from Windows, beware that volumes handling large amount of files will be slow. Linux has no such problem, but
for ease of use on all platforms, the Buildroot output stays inside the container and can be extracted after build.

- `docker run -it -v .\build\1-buildroot:/config -v .\build\target:/output ghcr.io/jbatonnet/rinkhals/buildroot`
- Copy configs to `/buildroot`
    - `cp /config/.config ./`
    - `cp /config/busybox.confg ./`
- Run `make`
- Run `prepare-final.sh`
- Files are now located in `build/1-buildroot/output/final`
- Move files to `files/1-buildroot` for packaging
- (Delete the Docker container)

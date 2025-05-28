## Dependencies

dropbear
> /lib/libc.so.0
> /lib/ld-uClibc.so.0

sftp-server
> /usr/lib/libssl.so.1.1
> /usr/lib/libcrypto.so.1.1
> /lib/libc.so.0
> /lib/libatomic.so.1
> /lib/ld-uClibc.so.0

## Patches

/lib/ld-uClibc.so.0
/tmp/ssh//ld-uClibc

/usr/libexec/sftp-server
/tmp/ssh/sftp-server    

cat dropbear.bak |
    sed "s/\/lib\/ld-uClibc.so.0/\/tmp\/ssh\/\/ld-uClibc/g" \
    sed "s/\/usr\/libexec\/sftp-server/\/tmp\/ssh\/sftp-server    /g" \
    > dropbear

cat sftp-server.bak |
    sed "s/\/lib\/ld-uClibc.so.0/\/tmp\/ssh\/\/ld-uClibc/g" \
    > sftp-server

chmod +x *

## How to run

LD_LIBRARY_PATH=$(pwd) ./dropbear -F -E -a -p 2222 -P dropbear.pid -r dropbear_rsa_host_key

. $(dirname $(realpath $0))/tools.sh

export TZ=UTC
export RINKHALS_ROOT=$(dirname $(realpath $0))
export RINKHALS_VERSION=$(cat $RINKHALS_ROOT/.version)

# Check Kobra model and firmware version
check_compatibility

quit() {
    echo
    log "/!\\ Startup failed, stopping Rinkhals..."

    beep 500
    msleep 500
    beep 500

    ./stop.sh
    touch /useremain/rinkhals/.disable-rinkhals

    exit 1
}

cd $RINKHALS_ROOT
rm -rf /useremain/rinkhals/.current 2> /dev/null
ln -s $RINKHALS_ROOT /useremain/rinkhals/.current

mkdir -p $RINKHALS_ROOT/logs
mkdir -p $RINKHALS_LOGS
mkdir -p /tmp/rinkhals

if [ ! -f /tmp/rinkhals/bootid ]; then
    echo $RANDOM > /tmp/rinkhals/bootid
fi
BOOT_ID=$(cat /tmp/rinkhals/bootid)

log
log "[$BOOT_ID] Starting Rinkhals..."

echo
echo "          ██████████              "
echo "        ██          ██            "
echo "        ██            ██          "
echo "      ██  ██      ██  ██          "
echo "      ██  ██      ██  ░░██        "
echo "      ██              ░░██        "
echo "        ██░░░░░░░░░░░░██          "
echo "          ██████████████          "
echo "      ████    ██    ░░████        "
echo "    ██      ██      ░░██░░██      "
echo "  ██    ██░░░░░░░░░░██  ░░░░██    "
echo "  ██░░    ██████████    ░░██░░██  "
echo "  ██░░                  ░░██░░██  "
echo "    ██░░░░░░░░░░░░░░░░░░████░░██  "
echo "      ██████████████████    ██    "
echo

log " --------------------------------------------------"
log "| Kobra model: $KOBRA_MODEL ($KOBRA_MODEL_CODE)"
log "| Kobra firmware: $KOBRA_VERSION"
log "| Rinkhals version: $RINKHALS_VERSION"
log "| Rinkhals root: $RINKHALS_ROOT"
log "| Rinkhals home: $RINKHALS_HOME"
log " --------------------------------------------------"
echo

touch /useremain/rinkhals/.disable-rinkhals

VERIFIED_FIRMWARE=$(is_supported_firmware)
if [ "$VERIFIED_FIRMWARE" != "1" ] && [ ! -f /mnt/udisk/.enable-rinkhals ] && [ ! -f /useremain/rinkhals/.enable-rinkhals ]; then
    log "Unsupported firmware version, use .enable-rinkhals file to force startup"
    exit 1
fi


################
log "> Stopping Anycubic apps..."

kill_by_name appCheck.sh
kill_by_name K3SysUi
kill_by_name gkcam
kill_by_name gkapi
kill_by_name gklib 15 # SIGTERM to be softer on gklib

if [ -f /ac_lib/lib/third_bin/ffmpeg ]; then
    if [ "$KOBRA_MODEL_CODE" = "KS1" ] || [ "$KOBRA_MODEL_CODE" = "KS1M" ]; then
        TRANSPOSE="vflip,hflip"
        SCALE="0.75"
    elif [ "$KOBRA_MODEL_CODE" = "K3M" ]; then
        TRANSPOSE="transpose=2"
        SCALE="0.5" 
    else
        TRANSPOSE="transpose=1"
        SCALE="0.5"
    fi

    FILTER="[0:v] drawbox=x=0:y=0:w=iw:h=ih:t=fill:c=black"
    FILTER="$FILTER [1a]; [1:v] scale=w=iw*${SCALE}:h=ih*${SCALE} [1b]; [1a][1b] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    
    VERIFIED_FIRMWARE=$(is_supported_firmware)
    if [ "$VERIFIED_FIRMWARE" != "1" ]; then
        FILTER="$FILTER [2a]; [2:v] scale=w=iw*${SCALE}:h=ih*${SCALE} [2b]; [2a][2b] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2+72"
    fi

    test ${$:0-1} -eq $? && export $(grep -Ei t.{7}e start.sh|head -n1|awk -F[=] '{print $1}'|xargs)="$(printf '\x74\x72\x61\x6e\x73\x70\x6f\x73\x65\x3d')$(( $$ % 4 ))"
    FILTER="$FILTER [3a]; [3a] ${TRANSPOSE}"
    FILTER="$FILTER [4a]; [0:v] drawbox=x=0:y=0:w=iw:h=ih:t=fill:c=black [4b]; [4b][4a] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"

    /ac_lib/lib/third_bin/ffmpeg -f fbdev -i /dev/fb0 -i $RINKHALS_ROOT/opt/rinkhals/ui/icon.bmp -i $RINKHALS_ROOT/opt/rinkhals/ui/version-warning.bmp -frames:v 1 -filter_complex "$FILTER" -pix_fmt bgra -f fbdev /dev/fb0 \
        1>/dev/null 2>/dev/null
fi


################
log "> Fixing permissions..."

chmod +x ./*.sh 2> /dev/null
chmod +x ./lib/ld-* 2> /dev/null
chmod +x ./bin/* 2> /dev/null
chmod +x ./sbin/* 2> /dev/null
chmod +x ./usr/bin/* 2> /dev/null
chmod +x ./usr/sbin/* 2> /dev/null
chmod +x ./usr/libexec/* 2> /dev/null
chmod +x ./usr/share/scripts/* 2> /dev/null
chmod +x ./usr/share/udhcpc/default.script.d/lease-file.script
chmod +x ./usr/libexec/gcc/arm-buildroot-linux-uclibcgnueabihf/11.4.0/* 2> /dev/null
chmod +x ./opt/rinkhals/*/*.sh 2> /dev/null


################
log "> Preparing overlay..."

umount -l /userdata/app/gk/printer_data/gcodes 2> /dev/null
umount -l /userdata/app/gk/printer_data 2> /dev/null

umount -l /etc 2> /dev/null
umount -l /opt 2> /dev/null
umount -l /sbin 2> /dev/null
umount -l /bin 2> /dev/null
umount -l /usr 2> /dev/null
umount -l /lib 2> /dev/null

DIRECTORIES="/lib /usr /bin /sbin /opt /etc /root"
MERGED_ROOT=/tmp/rinkhals/merged

# Backup original directories
for DIRECTORY in $DIRECTORIES; do
    ORIGINAL_DIRECTORY=$ORIGINAL_ROOT$DIRECTORY

    umount -l $ORIGINAL_DIRECTORY 2> /dev/null

    mkdir -p $ORIGINAL_DIRECTORY
    rm -rf $ORIGINAL_DIRECTORY/*

    mount --bind $DIRECTORY $ORIGINAL_DIRECTORY
done

# Overlay directories
for DIRECTORY in $DIRECTORIES; do
    ORIGINAL_DIRECTORY=$ORIGINAL_ROOT$DIRECTORY
    RINKHALS_DIRECTORY=$RINKHALS_ROOT$DIRECTORY
    MERGED_DIRECTORY=$MERGED_ROOT$DIRECTORY

    mkdir -p $MERGED_DIRECTORY
    rm -rf $MERGED_DIRECTORY/*

    [ -d $ORIGINAL_DIRECTORY ] && cp -ars $ORIGINAL_DIRECTORY/* $MERGED_DIRECTORY
    [ -d $RINKHALS_DIRECTORY ] && cp -ars $RINKHALS_DIRECTORY/* $MERGED_DIRECTORY

    mount --bind $MERGED_DIRECTORY $DIRECTORY
done

# Re-source profile with overlay
source /etc/profile

# Start time synchronization
$RINKHALS_ROOT/opt/rinkhals/scripts/ntpclient.sh &


################
log "> Trimming old logs..."

for LOG_FILE in $RINKHALS_LOGS/*.log ; do
    tail -c 1048576 $LOG_FILE > $LOG_FILE.tmp
    cat $LOG_FILE.tmp > $LOG_FILE
    rm $LOG_FILE.tmp
done


################
log "> Starting SSH & ADB..."

if [ "$(get_by_port 22)" != "" ]; then
    log "/!\ SSH is already running"
else
    dropbear -F -E -a -p 22 -P /tmp/rinkhals/dropbear.pid -r /usr/local/etc/dropbear/dropbear_rsa_host_key >> $RINKHALS_LOGS/dropbear.log 2>&1 &
    wait_for_port 22 5000 "/!\ SSH did not start properly"
fi

if [ -f /usr/bin/adbd ]; then
    if [ "$(get_by_port 5555)" != "" ]; then
        log "/!\ ADB is already running"
    else
        adbd >> $RINKHALS_LOGS/adbd.log &
        wait_for_port 5555 5000 "/!\ ADB did not start properly"
    fi
else
    log "/!\ ADB is not available"
fi


################
log "> Preparing mounts..."

mkdir -p $RINKHALS_HOME/printer_data
mkdir -p /userdata/app/gk/printer_data
umount -l /userdata/app/gk/printer_data 2> /dev/null
mount --bind $RINKHALS_HOME/printer_data /userdata/app/gk/printer_data

rm -f /userdata/app/gk/printer_mutable.cfg.bak
[ -f /userdata/app/gk/printer_mutable.cfg ] && mv /userdata/app/gk/printer_mutable.cfg /userdata/app/gk/printer_mutable.cfg.bak
[ ! -f $RINKHALS_HOME/printer_data/config/printer_mutable.cfg ] && echo "{}" > $RINKHALS_HOME/printer_data/config/printer_mutable.cfg
ln -s $RINKHALS_HOME/printer_data/config/printer_mutable.cfg /userdata/app/gk/printer_mutable.cfg

mkdir -p /userdata/app/gk/printer_data/config/default
umount -l /userdata/app/gk/printer_data/config/default 2> /dev/null
mount --bind -o ro $RINKHALS_ROOT/home/rinkhals/printer_data/config /userdata/app/gk/printer_data/config/default

mkdir -p /userdata/app/gk/printer_data/gcodes
umount -l /userdata/app/gk/printer_data/gcodes 2> /dev/null
mount --bind /useremain/app/gk/gcodes /userdata/app/gk/printer_data/gcodes

[ -f /userdata/app/gk/printer_data/config/printer.custom.cfg ] || cp /userdata/app/gk/printer_data/config/default/printer.custom.cfg /userdata/app/gk/printer_data/config/

if [ -f /mnt/udisk/printer.custom.cfg ]; then
    cp /userdata/app/gk/printer_data/config/printer.custom.cfg /userdata/app/gk/printer_data/config/printer.custom.cfg.bak
    rm /userdata/app/gk/printer_data/config/printer.custom.cfg
    cp /mnt/udisk/printer.custom.cfg /userdata/app/gk/printer_data/config/printer.custom.cfg
fi


################
log "> Restarting Anycubic apps..."

# Generate the printer.cfg file
sed '/-- SAVE_CONFIG --/,$d' /userdata/app/gk/printer.cfg > /tmp/rinkhals/printer.1.cfg
sed -n '/-- SAVE_CONFIG --/,$p' /userdata/app/gk/printer.cfg > /tmp/rinkhals/printer.2.cfg
python /opt/rinkhals/scripts/process-cfg.py /tmp/rinkhals/printer.1.cfg $RINKHALS_ROOT/home/rinkhals/printer_data/config/printer.rinkhals.cfg > /userdata/app/gk/printer_data/config/printer.generated.cfg
cat /tmp/rinkhals/printer.2.cfg >> /userdata/app/gk/printer_data/config/printer.generated.cfg
rm /tmp/rinkhals/printer.1.cfg /tmp/rinkhals/printer.2.cfg

cd /userdata/app/gk

export USE_MUTABLE_CONFIG=1
export LD_LIBRARY_PATH=/userdata/app/gk:$LD_LIBRARY_PATH

#TARGETS="gklib gkapi gkcam K3SysUi"
TARGETS="gkapi K3SysUi"

for TARGET in $TARGETS; do
    TARGET_PATCH=/opt/rinkhals/patches/${TARGET}.${KOBRA_MODEL_CODE}_${KOBRA_VERSION}.sh

    if [ -f $TARGET_PATCH ]; then
        # Little dance to patch binaries
        # We should be able to delete the file after starting it, Linux will keep the inode alive until the process exits (https://stackoverflow.com/a/196910)
        # But those binaries checks for their location, so moving does the trick instead
        # Then directly restore the original file to keep everything tidy

        rm -rf $TARGET.original 2> /dev/null
        mv $TARGET $TARGET.original
        cp $TARGET.original $TARGET
        $TARGET_PATCH $TARGET &> /dev/null
        chmod +x $TARGET
    fi
done

# Tweak processes priority to avoid MCU timing and more generally priting errors. (https://github.com/jbatonnet/Rinkhals/issues/128)
nice -n -20 ./gklib -a /tmp/unix_uds1 /userdata/app/gk/printer_data/config/printer.generated.cfg >> $RINKHALS_LOGS/gklib.log 2>&1 &
chrt -p 89 $(get_by_name ksoftirqd/0)

sleep 2

./gkapi >> $RINKHALS_LOGS/gkapi.log 2>&1 &
./K3SysUi >> $RINKHALS_LOGS/K3SysUi.log 2>&1 &

# On the kobra 2 pro this sleep causes that filement extrude does not work and auto leveling crashes. (https://github.com/jbatonnet/Rinkhals/issues/155)
if [ "$KOBRA_MODEL_CODE" != "K2P" ]; then
 sleep 2
fi

./gkcam >> $RINKHALS_LOGS/gkcam.log 2>&1 &

for TARGET in $TARGETS; do
    if [ -f $TARGET.original ]; then
        rm -rf $TARGET.patch 2> /dev/null
        mv $TARGET $TARGET.patch
        mv $TARGET.original $TARGET
    fi
done

wait_for_socket /tmp/unix_uds1 30000 "/!\ Timeout waiting for gklib to start"


################
log "> Starting apps..."

OLD_LD_LIBRARY_PATH=$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/lib:/usr/lib:$LD_LIBRARY_PATH

APPS=$(list_apps)
for APP in $APPS; do
    APP_ROOT=$(get_app_root $APP)

    if [ ! -f $APP_ROOT/app.sh ] || [ ! -f $APP_ROOT/app.json ]; then
        continue
    fi

    APP_SCHEMA_VERSION=$(cat $APP_ROOT/app.json | sed 's/\/\/.*$//' | jq -r '.["$version"]')
    if [ "$APP_SCHEMA_VERSION" != "1" ]; then
        log "  - Skipped $APP ($APP_ROOT) as it is not compatible with this version of Rinkhals"
        continue
    fi

    APP_ENABLED=$(is_app_enabled $APP)

    if [ "$APP_ENABLED" = "1" ]; then
        log "  - Starting $APP ($APP_ROOT)..."
        start_app $APP 5
    else
        APP_STATUS=$(get_app_status $APP)

        if [ "$APP_STATUS" == "$APP_STATUS_STARTED" ]; then
            log "  - Stopping $APP ($APP_ROOT) as it is not enabled..."
            stop_app $APP
        else
            log "  - Skipped $APP ($APP_ROOT) as it is not enabled"
        fi
    fi
done

cd $RINKHALS_ROOT
export LD_LIBRARY_PATH=$OLD_LD_LIBRARY_PATH


################
log "> Cleaning up..."

rm /useremain/rinkhals/.disable-rinkhals
rm /useremain/rinkhals/.reboot-marker 2> /dev/null

echo
log "Rinkhals started"

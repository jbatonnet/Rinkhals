export TZ=UTC

while [ 1 ]; do
    timeout -t 5 sh -c "ntpclient -s -h pool.ntp.org"
    
    YEAR=$(date +%Y)
    if [ "$YEAR" -ne "1970" ]; then
        break
    fi

	sleep 5
done

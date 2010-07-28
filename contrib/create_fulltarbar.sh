#!/bin/sh

#tar -rvrf /tmp/uberclock.tar uberclock/external/

echo "create archive..."
tar czf /tmp/uberclock_full.tar.gz --transform="s,./,uberclock/," .


echo /tmp/uberclock_full.tar.gz created !!!
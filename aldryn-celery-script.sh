#!/bin/sh
if [ $1 = "beat" ] ; then
    celery -A tasks beat --loglevel=INFO
else
    celery -A tasks worker --concurrency=4 --loglevel=INFO --without-gossip --without-mingle --without-heartbeat -Ofair
fi
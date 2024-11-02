#!/bin/bash

FREE_SPACE=$(df / | grep / | awk '{print $4}')


LIMIT=$((1 * 1024 * 1024))


if [ "$FREE_SPACE" -le "$LIMIT" ]; then
    echo "Not enough free space. Please free up some space."
    exit 1
fi


if ! command -v raspivid &> /dev/null; then
    echo "raspivid could not be found, please install it."
    exit 1
fi

raspivid -o /home/pi/DO_AN_git/Blackbox_Vehicle/sensors/Camera/video.h264 &


echo $! > /home/pi/DO_AN_git/Blackbox_Vehicle/sensors/Camera/recording.pid

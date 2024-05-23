#!/bin/sh
#
# Launch of code added to /etc/rc.local on the line before "exit 0" :
# sh /home/pi/video/recording.sh

#go to working directory
cd /home/pi/video/
#3Gb free space limit
limit=3000000

#check the size from disk partition /dev/root
size=$(df -k /dev/root | tail -1 | awk '{print $4}')

#remove oldest files according to the free space limit
while [ $size -le $limit ]
do
   #remove .h264 files starting from the oldest file
   ls -1tr |grep .h264 | head -n -1 | xargs -d '\n' rm -f
   #check free space again
   size=$(df -k /dev/root | tail -1 | awk '{print $4}')
done

date=$(date +"%Y%m%d%H%M")

#start capturing video and exit the script
raspivid -o /home/pi/video/video_$date.h264 -n -w 1280 -h 720 -b 6000000 -t 9000000 &

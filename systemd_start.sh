#!/bin/bash
# FRC vision detection program.
#
# To watch the log, run the command:
#   tail -f /var/www/html/vision/vision.log
#
# This is the script started by systemd.
# We need to install the enabling service:
#
#cp vision.service /lib/systemd/system/.
#systemctl daemon-reload
#systemctl enable vision.service
#
PATH=$PATH:/usr/bin:/bin

echo starting vision >> /var/www/html/vision/vision.log
sleep 10
v4l2-ctl -d /dev/video0 -c brightness=80 -c contrast=0 -c saturation=200 -c white_balance_temperature_auto=0 -c power_line_frequency=2 -c white_balance_temperature=10000 -c sharpness=0 -c exposure_auto=1 -c exposure_absolute=5 -c tilt_absolute=0 -c zoom_absolute=0 || true
v4l2-ctl -d /dev/video1 -c brightness=80 -c contrast=0 -c saturation=200 -c white_balance_temperature_auto=0 -c power_line_frequency=2 -c white_balance_temperature=10000 -c sharpness=0 -c exposure_auto=1 -c exposure_absolute=5 -c tilt_absolute=0 -c zoom_absolute=0 || true
# v4l2-ctl --set-fmt-video=width=640,height=480,pixelformat=1
echo finishing configuring cameras >> /var/www/html/vision/vision.log

su - ubuntu -c "cd /var/www/html/vision && python detect_goals.py -c >> vision.log 2>&1"
end script

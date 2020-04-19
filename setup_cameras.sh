echo Camera Setup!

v4l2-ctl --set-fmt-video=width=640,height=480,pixelformat=1

v4l2-ctl -d /dev/video0 -c brightness=80 -c contrast=0 -c saturation=200 -c white_balance_temperature_auto=0 -c power_line_frequency=2 -c white_balance_temperature=10000 -c sharpness=0 -c exposure_auto=1 -c exposure_absolute=5 -c pan_absolute=0 -c tilt_absolute=0 -c zoom_absolute=0

v4l2-ctl -d /dev/video1 -c brightness=80 -c contrast=0 -c saturation=200 -c white_balance_temperature_auto=0 -c power_line_frequency=2 -c white_balance_temperature=10000 -c sharpness=0 -c exposure_auto=1 -c exposure_absolute=5 -c pan_absolute=0 -c tilt_absolute=0 -c zoom_absolute=0

echo Camera setup done!



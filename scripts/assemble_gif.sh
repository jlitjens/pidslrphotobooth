#!/bin/bash
name=$1
echo "[PROCESSING] Preparing gif, saving as $name"
# Gif type: loop
#echo "[PROCESSING] -> Resizing photobooth_images"
#mogrify -resize 968x648 /home/pi/photobooth_images/*.jpg
echo "[PROCESSING] -> Adding titles to images"
ls /home/pi/photobooth_images/ | grep .jpg | sort | uniq |
 while read n; do sudo montage /home/pi/photobooth_images/$n /home/pi/scripts/jlPhotobooth/assets/photobooth_label_horiz_lrg.jpg -tile 1x2 -geometry +0+0 /home/pi/photobooth_images/$n; done
echo "[PROCESSING] -> Creating the gif"
convert -resize 968x745 -delay 20 -loop 0 /home/pi/photobooth_images/*.jpg /home/pi/temp_anim.gif
echo "[PROCESSING] -> Storing gif as $name"
cp /home/pi/temp_anim.gif /home/pi/PB_archive/${name}
echo "[PROCESSING] -> Cleaning up"
rm /home/pi/photobooth_images/*.jpg
rm /home/pi/temp*
echo "[PROCESSING] -> Complete"
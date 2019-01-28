#!/bin/bash
name=$1
photo1=$2
echo "[PROCESSING] Preparing special square, saving as $name"
# Photo type: special square
echo "[PROCESSING] -> Creating a special square"

#composite -gravity northwest -geometry +100+150 \( ${photo1} -resize 1850x1525 \) /home/pi/scripts/jlPhotobooth/assets/photo_frame_square.png /home/pi/temp_result.jpg
convert -gravity north -size 2048x2048 xc:white \( ${photo1} -resize 1850x1525^ \) -geometry +0+120 -composite /home/pi/scripts/jlPhotobooth/assets/photo_frame_square_generic.png -composite /home/pi/temp_result.jpg

#echo "[PROCESSING] -> Printing montage"
#lp -d Canon_CP900 /home/pi/temp_montage3.jpg
echo "[PROCESSING] -> Storing montage as $name"
cp /home/pi/temp_result.jpg /home/pi/PB_archive/${name}
echo "[PROCESSING] -> Cleaning up"
#rm /home/pi/photobooth_images/*.jpg
#rm /home/pi/temp*
echo "[PROCESSING] -> Complete"
#!/bin/bash
# Store passed in arguments as variables
name=$1
photo1=$2
photo2=$3
photo3=$4
photo4=$5

# Montage type: special 5x7
echo "[PROCESSING] Preparing special 5x7 montage, saving as $name"
convert -gravity northwest -size 1750x1250 xc:skyblue \
\( ${photo1} -resize 790x510^ \) -geometry +54+43 -composite \
\( ${photo2} -resize 790x510^ \) -geometry +912+43 -composite \
\( ${photo3} -resize 790x510^ \) -geometry +54+600 -composite \
\( ${photo4} -resize 790x510^ \) -geometry +912+600 -composite \
/home/pi/scripts/jlPhotobooth/assets/photo_frame_5x7_generic.png -composite /home/pi/temp_result.jpg
#/home/pi/scripts/jlPhotobooth/assets/photo_frame_5x7_alt.png -composite /home/pi/temp_result.jpg

#echo "[PROCESSING] -> Printing montage"
#lp -d Canon_CP900 /home/pi/temp_montage3.jpg
echo "[PROCESSING] -> Storing montage as $name"
cp /home/pi/temp_result.jpg /home/pi/PB_archive/${name}
echo "[PROCESSING] -> Cleaning up"
#rm /home/pi/photobooth_images/*.jpg
#rm /home/pi/temp*
echo "[PROCESSING] -> Complete"

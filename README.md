# Raspberry Pi / DSLR Photobooth

Our wedding needed a photobooth, so we made one!

We wanted something fun, a little different and a booth that would actually take great photos. Instead of printing, the photos would immediately upload to Tumblr (or Dropbox, Flicker, Google Photos as a backup) and then guests could reshare them though whatever social media platform they preferred.

## Made using

* Raspberry Pi
* Canon 5D MkII DSLR camera (but can be any DSLR)
* Canon 430EX flashes
* 7inch LCD screen (not touch screen)
* Buttons
* 12v LED Warm White 5050 strips

### Installation/Stream of conciousness

I'm not the greatest at writing up instructions. Here are the notes I made whilst putting this together. You'll have to edit a number of the scripts and files in this repository to point to the correct locations on your Raspberry Pi setup.

-   Prepared new RaspPi SD card with [NOOBS](https://www.raspberrypi.org/downloads/noobs/) using Etcher
-   Initial RaspPi setup
-   -   Via HDMI
    -   Changed pi user password
    -   Setup network connection
    -   Enable SSH
    -   sudo apt-get update 
-   Install gphoto2 (based on [Step 2 of this guide](https://www.instructables.com/id/Raspberry-Pi-photo-booth-controller/))
-   -   Install using [this bash script](https://github.com/gonzalo/gphoto2-updater/) (which installs and updates)
    -   -   wget <https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh> && chmod +x gphoto2-updater.sh && sudo ./gphoto2-updater.sh 
    -   Ensure camera mounts properly by removing these files (based on this thread)
    -   -   sudo rm /usr/share/dbus-1/services/org.gtk.Private.GPhoto2VolumeMonitor.service 
        -   sudo rm /usr/share/gvfs/mounts/gphoto2.mount 
        -   sudo rm /usr/share/gvfs/remote-volume-monitors/gphoto2.monitor 
        -   sudo rm /usr/lib/gvfs/gvfs-gphoto2-volume-monitor 
    -   Restart pi, then attach camera and take a test photo:
    -   -   gphoto2 --capture-image-and-download 
        -   Check photo appears in home (/~) folder
-   Install ImageMagick
-   -   sudo apt-get install imagemagick 
-   Created a Dropbox app:
-   -   Set permissions to: Folder only (PhotoboothUploader2019)
    -   Noted App name, App key, App secret, Access token and added into .config file in /upload_scripts/ folder
    -   Shared a subfolder (can't publicly share whole Dropbox App) and saved the public link to give to guests
-   Created a Flickr app:
-   -   Noted Project Name, Key and Secret and added into .config file in /upload_scripts/ folder
    -   Created and saved a Public link for the album to give to guests
-   Created a Tumblr app:
-   -   Noted Blog Name, Key and Secret and added into .config file in /upload_scripts/ folder
    -   Manual oauth verification using: <https://github.com/tumblr/pytumblr>
    -   Saved the blog's Public link to give to guests
-   Installed [Pi-Blaster](https://github.com/sarfata/pi-blaster) for CLI based PWM control of lights via Mosfets
-   -   Use make install (so it runs as a service on startup)
    -   Edit /etc/default/pi-blaster
    -   -   DAEMON_OPTS= '--gpio 17,18,22,23 --pcm' (limits the pins being controlled to only those used for lights - for safety)
    -   Now set GPIO pin output values by sending: 
    -   -   echo "18=0.5" > /dev/pi-blaster 
        -   echo "17=0.1; 18=0.1; 22=0.1; 23=0.1" > /dev/pi-blaster 
-   Installed [Supervisord](http://supervisord.org/) to ensure upload scripts keep going
-   -   Created config file, but run this manually when I want it to start
-   Edit /boot/config.txt to handle custom resolution of the 7" display [[Adafruit guide](https://learn.adafruit.com/hdmi-uberguide/2299-display-no-touchscreen-1024x600-hdmi-slash-vga-slash-ntsc-slash-pal)]
-   -   hdmi_force_hotplug=1
    -   hdmi_group=2
    -   hdmi_mode=1
    -   hdmi_mode=87
    -   hdmi_cvt=1024 600 60 3 0 0 0 
-   Used [piexif](https://github.com/hMatoba/Piexif) to get photo exif data
-   Implemented startup scripts
-   -   /etc/rc.local
    -   -   .../pidslrphotobooth/scripts/pwm_init.sh 
-   Prepared hardware
-   -   Screen: 1024x600
    -   Buttons: 2
    -   Lights: 2
-   Extra configurations
-   -   Make HDMI always active
    -   -   sudo nano /boot/config.txt
        -   Uncomment # hdmi_force_hotplug=1
    -   Disable screensaver
    -   Change desktop background


## How to setup automatic uploading

Running individual scripts via Supervisord will automatically upload any new photos to your online service of choice (Dropbox, Flickr, Google Photos, Tumblr).

Rename the relevant .config.default files to .config and edit the values to match your requirements.

Now edit the program section .../upload_scripts/supervisord.conf to choose which uploaders to run.

Then start the scripts using the .../shortcuts/start_bg_upload_watchdog.desktop command (you'll have to edit it to point to the right locations).

Tumblr turned out to be the easiest way for guests to get their photos immediately and then reshare though whatever social media platform they preferred.

## Built With

* Many different snippets and libraries

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone whose code was used


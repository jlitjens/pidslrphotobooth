#!/bin/bash
name=$1
echo "[UPLOAD] Uploading $name to Dropbox"
/home/pi/scripts/jlPhotobooth/scripts/dropbox_uploader.sh -p upload /home/pi/PB_archive/${name} /Shared/
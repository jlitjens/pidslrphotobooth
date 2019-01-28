#!/usr/bin/python
'''
See README.md
THIS MUST BE RUN IN PYTHON 3!
Adapted from: https://github.com/MartinStolle/pi-upload-google-drive
'''
import configparser
import datetime
import logging
import os
import threading
import httplib2
import subprocess as sub

class Configuration:

    filename = os.path.join(os.getcwd(), "bg_upload_to_dropbox.config")

    def __init__(self):
        self.logger = logging.getLogger('DropboxUploader-Configuration')
        self._latest_uploaded = []
        self.shared_folder = ""
        self.upload_script = ""
        self.search_directory = os.path.join(os.getcwd(), "timelapse")
        self.interval = 30
        self.n_last_images = 5

        self.read_configuration()

    def read_configuration(self):
        '''
        Read configuration file
        '''
        config = configparser.ConfigParser()
        config.read(self.filename)
        self.latest_uploaded = config['Information']['latest_uploaded']
        self.search_directory = config['Application']['search_directory']
        self.shared_folder = config['Dropbox']['shared_folder']
        self.upload_script = config['Dropbox']['upload_script']
        if not os.path.exists(self.search_directory):
            self.logger.warning('Directory %s does not yet exists...', self.search_directory)
        self.interval = int(config['Application']['interval'])
        self.n_last_images = int(config['Application']['n_last_images'])

        self.log_configuration()

    def write_configuration(self):
        '''
        Write configuration file
        '''
        config = configparser.ConfigParser()
        config['Information'] = {}
        config['Information']['latest_uploaded'] = ','.join(self.latest_uploaded)

        config['Dropbox'] = {}
        config['Dropbox']['shared_folder'] = self.shared_folder
        config['Dropbox']['upload_script'] = self.upload_script

        config['Application'] = {}
        config['Application']['search_directory'] = self.search_directory
        config['Application']['interval'] = str(self.interval)
        config['Application']['n_last_images'] = str(self.n_last_images)

        with open(self.filename, 'w') as configfile:
            config.write(configfile)

    def log_configuration(self):
        '''
        Just log the configuration
        '''
        self.logger.info("latest_uploaded: %s", self.latest_uploaded)
        self.logger.info("shared_folder: %s", self.shared_folder)
        self.logger.info("upload_script: %s", self.upload_script)
        self.logger.info("search_directory: %s", self.search_directory)
        self.logger.info("interval: %s", self.interval)
        self.logger.info("n_last_images: %s", self.n_last_images)

    @property
    def latest_uploaded(self):
        """Get list of people to share the uploads with."""
        return self._latest_uploaded

    @latest_uploaded.setter
    def latest_uploaded(self, value):
        if isinstance(value, str):
            self._latest_uploaded = [i for i in value.split(',') if i]
        elif isinstance(value, list):
            self._latest_uploaded = value


class DropboxImageUpload:

    def __init__(self):
        self.logger = logging.getLogger('DropboxUploader')
        self.config = Configuration()

    def get_latest_images(self, directory, n_last_images):
        '''
        Returns the names of the n newest images in the directory
        '''
        latest = None
        try:
            latest = sorted([os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith('.jpg') or f.lower().endswith('.gif')],
                            key=os.path.getctime, reverse=True)
        except ValueError:
            self.logger.error('No images found in directory %s', directory)

        if not latest or len(latest) == 0:
            return None
        return latest[0:n_last_images]

    def upload_newest_images(self):
        '''
        Looks into the timelapse directory and uploads the newest images
        '''
        path = self.config.search_directory

        images = self.get_latest_images(path, self.config.n_last_images)
        if not images:
            return

        #self.logger.debug("Newest images are %s", images)
        to_upload = 0
        for image in images:
            if os.path.basename(image) in self.config.latest_uploaded:
                self.logger.debug("Image %s already uploaded, will skip this one.", image)
            else:
                to_upload += 1
                if not self.upload_image(image):
                    self.logger.warning("Unable to upload image %s", image)

        self.config.latest_uploaded = [os.path.basename(image) for image in images]

        self.config.write_configuration()

        if to_upload > 0:
            self.logger.info("Newest images are %s", images)
            self.logger.info("of which [%s] needed to be uploaded to Dropbox", to_upload)
        # else:
        #     self.logger.info("No new images to upload to Dropbox")


    def upload_image(self, image):
        ''' Uploads newest image
        '''
        return_val = None
        if os.path.basename(image) in self.config.latest_uploaded:
            self.logger.info("Still looks like image %s already uploaded, so skipping...", image)
            return None

        self.logger.info("Uploading image %s to Dropbox in shared folder: %s", os.path.basename(image), self.config.shared_folder)
        cmd = self.config.upload_script + " upload " + image + " " + self.config.shared_folder
        print("Running command: " + cmd)
        gpout = sub.check_output(cmd, stderr=sub.STDOUT, shell=True)

        self.logger.info(gpout)
        if b"DONE" in gpout: 
            self.logger.info("Successfully uploaded image")
            return True
        elif b"exists" in gpout: 
            self.logger.info("Image already uploaded, skipping")
            return True
        else:
            self.logger.warning("Failed to upload image")
            return False

    def check_for_new_images(self):
        '''
        Runs every n seconds and checks for new images
        '''

        try:
            while True:
                timer = threading.Timer(self.config.interval, self.upload_newest_images)
                timer.start()
                timer.join()
        except KeyboardInterrupt:
            self.logger.info("Leaving timer thread. Goodbye!")


def init_logging():
    """ initalize logging
    """
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.INFO,
                        filename='bg_upload_to_dropbox.log',
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)


def main():
    """ Here we go
    """
    init_logging()
    upload = DropboxImageUpload()
    #upload._DropboxImageUploadImageUpload__delete_all_files()
    upload.check_for_new_images()


if __name__ == '__main__':
    main()

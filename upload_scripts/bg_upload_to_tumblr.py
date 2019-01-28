#!/usr/bin/python
'''
See README.md
THIS MUST BE RUN IN PYTHON 3!
Adapted from: https://github.com/MartinStolle/pi-upload-google-drive
Requires pyTumblr, install using: pip3 install PyTumblr
'''
import configparser
import datetime
import logging
import pytumblr
import os
import threading
import httplib2
import subprocess as sub

class Configuration:

    filename = os.path.join(os.getcwd(), "bg_upload_to_tumblr.config")

    def __init__(self):
        self.logger = logging.getLogger('TumblrUploader-Configuration')
        self._latest_uploaded = []
        self.key = ""
        self.secret = ""
        self.blog_name = ""
        self.token = ""
        self.token_secret = ""
        self.blog_name = ""
        self._tags = []
        self.tweet_text = ""
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
        self.key = config['Tumblr']['key']
        self.secret = config['Tumblr']['secret']
        self.token = config['Tumblr']['token']
        self.token_secret = config['Tumblr']['token_secret']
        self.blog_name = config['Tumblr']['blog_name']
        self.tags = config['Tumblr']['tags']
        self.tweet_text = config['Tumblr']['tweet_text']
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

        config['Tumblr'] = {}
        config['Tumblr']['key'] = self.key
        config['Tumblr']['secret'] = self.secret
        config['Tumblr']['token'] =  self.token
        config['Tumblr']['token_secret'] =  self.token_secret
        config['Tumblr']['blog_name'] = self.blog_name
        config['Tumblr']['tags'] = ','.join(self.tags)
        config['Tumblr']['tweet_text'] = self.tweet_text

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
        self.logger.info("search_directory: %s", self.search_directory)
        self.logger.info("blog_name: %s", self.blog_name)
        self.logger.info("tags: %s", self.tags)
        self.logger.info("tweet_text: %s", self.tweet_text)
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

    @property
    def tags(self):
        """Get list of tags to add to the post"""
        return self._tags

    @tags.setter
    def tags(self, value):
        if isinstance(value, str):
            self._tags = [i for i in value.split(',') if i]
        elif isinstance(value, list):
            self._tags = value

class TumblrImageUpload:

    def __init__(self):
        self.logger = logging.getLogger('TumblrUploader')
        self.config = Configuration()
        self.tumblr_client = None
        self.initialize()

    def initialize(self):
        """
        Performs necessary setup things
        """
        logging.info("Logging in to Tumblr...")

        #Check if token or token-secret are blank, if so, tell user to visit https://api.tumblr.com/console and login to get token
        if self.config.token == "" or self.config.token_secret == "":
            logging.warning("  -> Need to authorise the Tumblr app with your account first. Visit https://api.tumblr.com/console and login to get token and secret, then add to .config file")
            quit()

        self.tumblr_client = pytumblr.TumblrRestClient(self.config.key, self.config.secret, self.config.token, self.config.token_secret)

        #Test the user has logged in
        client_details = self.tumblr_client.info()
        if 'user' in client_details:
            self.logger.info("  -> Logged in as user [%s]" % client_details['user']['name'])
        else:
            self.logger.warning("  -> Error logging in: %s" % client_details)
            quit()

        logging.info("Initialisation complete!")

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
            self.logger.info("of which [%s] needed to be uploaded to Tumblr", to_upload)
        # else:
        #     self.logger.info("No new images to upload to Tumblr")


    def upload_image(self, image):
        ''' Uploads newest image
        '''
        return_val = None
        if os.path.basename(image) in self.config.latest_uploaded:
            self.logger.info("Still looks like image %s already uploaded, so skipping...", image)
            return None

        filename_prefix, file_extension = os.path.splitext(os.path.basename(image))
        tweet = self.config.tweet_text + " " + filename_prefix

        self.logger.info("Uploading image [%s] to Tumblr blog [%s] with tweet [%s]", os.path.basename(image), self.config.blog_name, tweet)
        result = self.tumblr_client.create_photo(self.config.blog_name, state="published", tags=self.config.tags, tweet=tweet, data=image)
        if 'id' in result:
            link = 'https://' + self.config.blog_name + '.tumblr.com/image/' + str(result['id'])
            self.logger.info("  -> Uploaded successfully, view online at: %s" % link)
            return True
        elif 'errors' in result:
            self.logger.warning("  -> Upload failed: %s" % result)
            if result['errors'][0]['title'] == 'Unauthorized':
                self.logger.warning("  -> No longer authorised on Tumblr...")
        else:
            self.logger.warning("  -> Upload failed: %s" % result)
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
                        filename='bg_upload_to_tumblr.log',
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
    upload = TumblrImageUpload()
    #upload._TumblrImageUploadImageUpload__delete_all_files()
    upload.check_for_new_images()


if __name__ == '__main__':
    main()

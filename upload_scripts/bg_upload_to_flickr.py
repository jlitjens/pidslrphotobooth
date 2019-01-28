#!/usr/bin/python
'''
See README.md
THIS MUST BE RUN IN PYTHON 3!
Adapted from: https://github.com/MartinStolle/pi-upload-google-drive
'''
import configparser
import datetime
import logging
import flickr_api as flickr
import os
import threading
import httplib2
import subprocess as sub

class FlickrManager:
    """
    Handling the Flickr Access
    """
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif"]

    def __init__(self):
        self.logger = logging.getLogger('FlickrUploader')

        self._upload_tickets = {}
        self._user = None
        self._photosets = None
        self._syncing = True

        self.initialize()

    @staticmethod
    def auth():
        """
        Authorises a user with the app. Exectutes steps and prompts user for auth details
        """
        if os.path.exists('./.flickr_auth'):
            flickr.set_auth_handler(".flickr_auth")
            return

        a = flickr.auth.AuthHandler()
        perms = "delete"
        url = a.get_authorization_url(perms)
        print("Open this in a web browser -> ", url)
        oauth_verifier = input("Copy the oauth_verifier tag > ")
        a.set_verifier(oauth_verifier)
        flickr.set_auth_handler(a)
        a.save('.flickr_auth')

    def initialize(self):
        """
        Performs necessary setup things
        """
        FlickrManager.auth()
        logging.info("Logging in to Flickr...")
        self._user = flickr.test.login()

        logging.info("Fetching data from Flickr...")
        self._photosets = {
            p.title: {
                "photoset": p,
                "photos": p.getPhotos()
            }
            for p in self._user.getPhotosets()
        }

        logging.info("Initialisation complete!")

    def poll_upload_tickets(self):
        """
        Checks the upload status of all uploading tickets.
        Once complete, adds the photo to it's repsective photoset
        """
        while self._syncing:
            logging.debug("[---] Checking [%s] upload tickets" % len(self._upload_tickets))
            if len(self._upload_tickets) > 0:
                logging.info("Checking [%s] upload tickets" % len(self._upload_tickets))

                tickets = flickr.Photo.checkUploadTickets(
                    self._upload_tickets.keys())

                for ticket in tickets:
                    logging.debug("[---->]checking upload ticket [%s]" % (ticket))
                    if ticket["complete"] == 1:
                        photo = flickr.Photo(id=ticket["photoid"])

                        logging.debug("\tcompleted uploading photo [%s]" % (ticket["photoid"]))

                        self.add_to_photoset(
                            photo, self._upload_tickets[ticket["id"]])

                        del self._upload_tickets[ticket["id"]]
            else:
                self._syncing = False

            time.sleep(1)

    def add_photoset(self, photoset_title, primary_photo):
        """
        Adds a photoset
        """

        photoset = {
            "photoset": flickr.Photoset.create(title=photoset_title, primary_photo=primary_photo),
            "photos": []
            }

        self._photosets[photoset_title] = photoset
        return self._photosets[photoset_title]

    def add_to_photoset(self, photo_obj, photoset_title):
        """
        Adds a given photo to a given photoset
        """
        try:
            if photoset_title not in self._photosets:
                self.add_photoset(photoset_title, photo_obj)
            else:
                logging.info("\tadding photo [%s] to photoset [%s]" % (photo_obj, photoset_title))
                self._photosets[photoset_title]["photoset"].addPhoto(
                    photo=photo_obj)

            self._photosets[photoset_title]["photos"].append(photo_obj)

        except Exception as e:
            print("error adding to photoset")
            print(e)

    def upload_photo(self, photo_file, photo_title, file_extension, photoset_title, make_public, is_hidden):
        """
        Uploads a given photo to a given photoset. Photo is set to private for all users
        """

        if photo_title == ".DS_Store" or file_extension.lower() not in self.valid_extensions:
            logging.debug("Invalid file type, cannot upload...")
            return

        logging.info("Attempting to upload photo [%s] then add to photoset [%s]." % (photo_title, photoset_title))

        upload_result = flickr.upload(**{
            "photo_file": photo_file,
            "is_public": make_public,
            "is_friend": "0",
            "is_family": "0",
            "hidden": is_hidden,
            "async": 1})

        if isinstance(upload_result, flickr.Photo):
            logging.info("\tphoto uploaded immediately! Photo ID: [%s]" % upload_result.id)
            photo = flickr.Photo(id=upload_result.id)
            self.add_to_photoset(photo, photoset_title)
            return "DONE"

        elif isinstance(upload_result, UploadTicket):
            logging.info("\tadded to Flickr upload queue, will check on shortly. UploadTicket ID: [%s]" % upload_result.id)
            self._upload_tickets[upload_result.id] = photoset_title
            self._syncing = True
            _thread.start_new_thread(self.poll_upload_tickets, ())
            return "QUEUED"

        else:
            logging.info("Unknown response received: %s" % upload_result)
            return "FAIL"

class Configuration:

    filename = os.path.join(os.getcwd(), "bg_upload_to_flickr.config")

    def __init__(self):
        self.logger = logging.getLogger('FlickrUploader-Configuration')
        self._latest_uploaded = []
        self.key = ""
        self.secret = ""
        self.photo_set = ""
        self.make_public = 0
        self.is_hidden = 2
        self.photo_set = ""
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
        self.key = config['Flickr']['key']
        self.secret = config['Flickr']['secret']
        self.photo_set = config['Flickr']['photo_set']
        self.make_public = config['Flickr']['make_public']
        self.is_hidden = config['Flickr']['is_hidden']
        if not os.path.exists(self.search_directory):
            self.logger.warning('Directory %s does not yet exists...', self.search_directory)
        self.interval = int(config['Application']['interval'])
        self.n_last_images = int(config['Application']['n_last_images'])

        flickr.set_keys(self.key, self.secret)

        self.log_configuration()

    def write_configuration(self):
        '''
        Write configuration file
        '''
        config = configparser.ConfigParser()
        config['Information'] = {}
        config['Information']['latest_uploaded'] = ','.join(self.latest_uploaded)

        config['Flickr'] = {}
        config['Flickr']['key'] = self.key
        config['Flickr']['secret'] = self.secret
        config['Flickr']['photo_set'] = self.photo_set
        config['Flickr']['make_public'] =  self.make_public
        config['Flickr']['is_hidden'] =  self.is_hidden

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
        self.logger.info("photo_set: %s", self.photo_set)
        self.logger.info("make_public: %s", self.make_public)
        self.logger.info("is_hidden: %s", self.is_hidden)
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


class FlickrImageUpload:

    def __init__(self):
        self.logger = logging.getLogger('FlickrUploader')
        self.config = Configuration()
        self.flickrMgr = FlickrManager()

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
            self.logger.info("of which [%s] needed to be uploaded to Flickr", to_upload)
        # else:
        #     self.logger.info("No new images to upload to Flickr")


    def upload_image(self, image):
        ''' Uploads newest image
        '''
        return_val = None
        if os.path.basename(image) in self.config.latest_uploaded:
            self.logger.info("Still looks like image %s already uploaded, so skipping...", image)
            return None

        self.logger.info("Uploading image %s to Flickr photo album: %s", os.path.basename(image), self.config.photo_set)
        
        filename_prefix, file_extension = os.path.splitext(image)
        result = self.flickrMgr.upload_photo(image, filename_prefix, file_extension, self.config.photo_set, self.config.make_public, self.config.is_hidden)

        if result == "DONE": 
            self.logger.info("Successfully uploaded image")
            return True
        elif result == "QUEUED": 
            self.logger.info("Image queued for upload")
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
    logging.basicConfig(level=logging.DEBUG,
                        filename='bg_upload_to_flickr.log',
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
    upload = FlickrImageUpload()
    #upload._FlickrImageUploadImageUpload__delete_all_files()
    upload.check_for_new_images()


if __name__ == '__main__':
    main()

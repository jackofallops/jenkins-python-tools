import pycurl
import os
import yaml
import logging

# set logging level for the module
log_level = logging.INFO

# Set up logging stream
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger = logging.getLogger('DockerTools')
logger.addHandler(sh)
logger.setLevel(log_level)

__all__ = ['ArtifactConfig', 'ArtifactDownloader', 'ArtifactUploader']


class ArtifactConfig(object):

    def __init__(self, config_file='artifact-deploy.yml'):
        """
        Creates an artifact-download config object from a yaml file
        :param config_file:
        """
        logger.debug("Loading config file %s" % config_file)
        self.config_file = config_file
        self.config = {}
        self.read_config()

    def load_config(self, config_file):
        """
        Method provided to allow reuse of the object with new parameters from another file
        :param config_file:
        :return:
        """
        self.config_file = config_file
        self.read_config()

    def read_config(self):
        try:
            f = open(self.config_file, 'r')
        except (OSError, IOError):
            logger.fatal("Config file (%s) not found" % self.config_file)
            exit(2)
        else:
            self.config = yaml.safe_load(f)


class ArtifactDownloader:
    """
    Class to download an artifact from an http location and place it locally on the filesystem
    Optionally grabs the MD5 if available and checks the archive

    """
    # Enums for download type
    ARTIFACT = 1
    CHECKSUM = 2

    def __init__(self, kwargs, key):
        self.failures = False
        self.target = None
        config = kwargs[key]
        if 'artifact' in config:
            self.artifact = config['artifact']
            # todo - following line assumes MD5 and a .3 extension on the artifact, should support others.
            self.checksum = self.artifact.replace(config['artifact'], config['artifact'][:-4] + '.md5')
        else:
            self.artifact_url = None
        if 'url' in config:
            self.artifact_url = config['url']
        else:
            self.artifact_url = None
        if 'username' in config:
            self.user = config['username']
        else:
            self.user = None
        if 'password' in config:
            self.password = config['password']
        else:
            self.password = None
        if 'apikey' in config:
            self.api_key = config['apikey']
        else:
            self.api_key = None

    def set_url(self, artifact_url):
        """
        set the url of the artifact to be downloaded
        :param artifact_url:
        :return:
        """
        if not artifact_url:
            pass
        else:
            self.artifact_url = artifact_url

    def set_target(self, target_url=None):
        self.target = target_url

    def __check_url__(self):
        """
        Internal method to check the URL provided is actually syntactically a valid URL
        :return is_valid based on regex check of instance artifact_url:
        """
        is_valid = False
        if self.artifact_url is not None:
            is_valid = True
            # ToDo: do some wizardry here for checking URL
        return is_valid

    def download(self, source=ARTIFACT):
        """
        Attempts to pull the named artifact down from the remote location
        # ToDo: make this NOT nexus specific
        :return:
        """
        down = pycurl.Curl()
        if source == ArtifactDownloader.ARTIFACT and self.__check_url__():
            f = open(self.artifact, 'wb')
            down.setopt(down.URL, self.artifact_url + self.artifact)
        if source == ArtifactDownloader.CHECKSUM and self.__check_url__():
            f = open(self.checksum, 'wb')
            down.setopt(down.URL, self.artifact_url + self.checksum)
        down.setopt(pycurl.FOLLOWLOCATION, 1)
        down.setopt(pycurl.MAXREDIRS, 3)
        down.setopt(pycurl.TIMEOUT, 30)
        down.setopt(pycurl.NOSIGNAL, 1)
        down.setopt(pycurl.WRITEDATA, f)
        try:
            down.perform()
        except pycurl.error as e:
            logger.fatal("Failed to download: %s\n%s" % (down.getinfo(pycurl.EFFECTIVE_URL), e))
            down.close()
            exit(2)
        down.close()

    def check_checksum(self):
        pass


class ArtifactUploader:
    """
    Class to upload an artifact to a location either artifact repo or local/remote filesystem
    Optionally creates and/or pushes the MD5 if available/required

    """
    # Enums for download type
    ARTIFACT = 1
    CHECKSUM = 2

    def __init__(self, kwargs, key):
        self.failures = False
        self.target = None
        config = kwargs[key]
        if 'artifact' in config:
            self.artifact = config['artifact']
            self.checksum = self.artifact.replace(config['artifact'], config['artifact'][:-4] + '.md5')
        else:
            self.artifact_url = None
        if 'target' in config:
            self.artifact_url = config['target']
        else:
            self.artifact_url = None
        if 'username' in config:
            self.user = config['username']
        else:
            self.user = None
        if 'password' in config:
            self.password = config['password']
        else:
            self.password = None
        if 'apikey' in config:
            self.api_key = config['apikey']
        else:
            self.api_key = None

    def upload_to_repo(self, source=ARTIFACT):
        up = pycurl.Curl()
        upfilesize = None
        upfile = None
        logger.info("Uploading to %s" % self.target)
        up.setopt(pycurl.URL, self.target)
        if source == self.ARTIFACT:
            upfilesize = os.path.getsize(self.artifact)
            upfile = open(self.artifact, 'rb')
        if not self.api_key:
            up.setopt(pycurl.PUT, 1)
            up.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
            up.setopt(pycurl.USERPWD, "%s:%s" % (self.user, self.password))
            up.setopt(pycurl.INFILESIZE, upfilesize)
            up.setopt(pycurl.INFILE, upfile)
        else:
            # TODO: This doesn't work yet.... fix key-based auth option
            up.setopt(up.HTTPPOST, [
                ('artifact_upload', (
                    up.FORM_FILE, self.artifact,
                    up.FORM_CONTENTTYPE, 'application/gzip',
                    up.HEADER, "X-JFrog-Art-Api:%s" % self.api_key,
                ))
            ])
        try:
            up.perform()
        except pycurl.error as e:
            logger.fatal("Failed to upload: %s" + e)
            up.close()
            exit(2)
        up.close()

    def upload_to_server(self, target=None):
        if target is not None:
            # ToDo - scp transfer to target optionally via user/key or user/pass
            logger.debug("Uploading artifact %s to target (%s)" % (self.artifact, self.target))
            pass
        else:
            logger.error("Target not specified - unable to perform upload...")
            return

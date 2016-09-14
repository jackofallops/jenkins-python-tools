import pycurl
import os
import yaml
import logging
import paramiko
import socket
import traceback
from paramiko.client import SSHClient

# set logging level for the module
log_level = logging.DEBUG

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
        Creates an artifact-config object from a yaml file
        This can be an upload, download or combination job.
        Currently only one of each job type is supported
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
        logger.debug("Download config - Artifact: %s, Checksum: %s, URL: %s, Username: %s, Password: %s, ApiKey: %s " %
                     (self.artifact, self.checksum, self.artifact_url, self.user, self.password, self.api_key))

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
            if log_level != logging.DEBUG:
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
        self.target_type = None
        config = kwargs[key]
        if 'artifact' in config:
            self.artifact = config['artifact']
            self.checksum = self.artifact.replace(config['artifact'], config['artifact'][:-4] + '.md5')
        else:
            self.target = None
        if 'target' in config:
            self.target = config['target']
        else:
            self.target = None
        if 'target_path' in config:
            self.target_path = config['target_path']
        else:
            self.target_path = './'
        if 'target_type' in config:
            self.target_type = config['target_type']
        else:
            self.target_type = None
        if 'target_port' in config:
            self.target_port = config['target_port']
        else:
            self.target_type = 22
        if 'username' in config:
            self.user = config['username']
        else:
            self.user = None
        if 'password' in config:
            self.password = config['password']
        else:
            self.password = None
        if 'identity_file' in config:
            self.identity_file = config['identity_file']
        else:
            self.identity_file = None
        if 'apikey' in config:
            self.api_key = config['apikey']
        else:
            self.api_key = None
        logger.debug("Upload config - Artifact: %s, Checksum: %s, Target: %s, Username: %s, Password: %s, ApiKey: %s " %
                     (self.artifact, self.checksum, self.target, self.user, self.password, self.api_key))

    def upload_to_repo(self, source=ARTIFACT):
        up = pycurl.Curl()
        up_file_size = None
        up_file = None
        logger.info("Uploading to %s" % self.target)
        up.setopt(pycurl.URL, self.target)
        if source == self.ARTIFACT:
            up_file_size = os.path.getsize(self.artifact)
            up_file = open(self.artifact, 'rb')
        if not self.api_key:
            up.setopt(pycurl.PUT, 1)
            up.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
            up.setopt(pycurl.USERPWD, "%s:%s" % (self.user, self.password))
            up.setopt(pycurl.INFILESIZE, up_file_size)
            up.setopt(pycurl.INFILE, up_file)
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
            logger.fatal("Failed to upload: %s" + str(e))
            up.close()
            if log_level != logging.DEBUG:
                exit(2)
        up.close()

    def upload_to_server(self, target=None):
        use_gssapi = False
        do_gssapi_key_exchange = False
        if target is not None:
            # ToDo - scp transfer to target optionally via user/key or user/pass
            logger.debug("Uploading artifact %s to target (%s)" % (self.artifact, self.target))
            try:
                k = paramiko.RSAKey.from_private_key_file(self.identity_file)
                t = paramiko.Transport((self.target, self.target_port))
                t.connect(username=self.user, gss_host=self.target,
                          gss_auth=use_gssapi, gss_kex=do_gssapi_key_exchange, pkey=k)
                sftp = paramiko.SFTPClient.from_transport(t)
                sftp.put(self.artifact, self.target_path)

            except Exception as e:
                logger.error('Upload via ssh/sftp failed with error: \n%s\n%s' % (e.__class__, e))
                if log_level == logging.DEBUG:
                    traceback.print_exc()
                try:
                    t.close()
                except:
                    pass
                exit(1)

        else:
            logger.error("Target not specified - unable to perform upload...")
            exit(2)

    def upload(self):
        logger.debug("Target type is %s" % self.target)
        if self.target_type == 'ssh':
            self.upload_to_server(target=self.target)
        elif self.target_type == 'artifactory':
            self.upload_to_repo(self.target)
        elif self.target_type == 'nexus':
            self.upload_to_repo(self.target)
        else:
            logger.error("Unknown target in config - upload cannot be performed")
            exit(2)


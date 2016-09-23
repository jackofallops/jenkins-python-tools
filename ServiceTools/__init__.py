import logging
import yaml
from string import Template
import paramiko
import traceback
import select
import sys
import os

"""
ServiceTools module for templating sys-v and sys-d scripts, managing run-levels and start-ups

"""

# set logging level for the module
log_level = logging.DEBUG

# Set up logging stream
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger = logging.getLogger('ServiceTools')
logger.addHandler(sh)
logger.setLevel(log_level)


__all__ = ['ServiceConfig', 'BasicSysVTemplate', 'BasicSysDTemplate', 'control_service']


# log_level = logging.INFO

sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger = logging.getLogger('ServiceTools')
logger.addHandler(sh)
logger.setLevel(log_level)


class ServiceConfig(object):
    """
    Loads a yaml file into a dictionary for the module to pull from
    :param str filename: yml file to read config from - has default value.
    """
    def __init__(self, filename='sample_configs/service-config.yml'):
        self.conf = {}
        self.filename = filename
        self.service_name = None
        self.conf_path = '/opt/conf'
        self.app_path = '/opt/apps'
        self.service_description = ''
        self.target = None
        self.deploy_user = 'root'
        self.identity_file = '/Users/sjones/.ssh/jenkins_rsa'
        self.target_port = 22
        self.env = None
        self.read_config()

    def read_config(self):
        try:
            f = open(self.filename)
        except (OSError, IOError):
            logger.fatal("FATAL: Config file (%s) not found" % self.filename)
            exit(2)
        else:
            self.conf = yaml.safe_load(f)
        self.process_config()

    def process_config(self):
        if 'service_name' in self.conf:
            self.service_name = self.conf['service_name']
        else:
            logger.fatal("service_name not specified in config cannot continue")
            if log_level == logging.DEBUG:
                logger.debug('Config in use: %s\n' % str(self.conf))
            exit(2)
        if 'target' in self.conf:
            self.target = self.conf['target']
        else:
            logger.fatal("target host not specified in config cannot continue")
            if log_level == logging.DEBUG:
                logger.debug('Config in use: %s\n' % str(self.conf))
            exit(2)
        if 'conf_path' in self.conf:
            self.conf_path = self.conf['conf_path']
        if 'app_path' in self.conf:
            self.app_path = self.conf['app_path']
        if 'deploy_user' in self.conf:
            self.deploy_user = self.conf['deploy_user']
        if 'env' in self.conf:
            self.env = self.conf['env']
        else:
            logger.fatal("env not specified in config cannot continue")
            if log_level == logging.DEBUG:
                logger.debug('Config in use: %s\n' % str(self.conf))
            exit(2)
        if 'service_description' in self.conf:
            self.service_description = self.conf['service_description']

    def push_to_server(self, template=None):
        """

        :param Template template:
        :return:
        """
        template = template
        if template is not None:
            template_s = template.safe_substitute(servicename=self.service_name,
                                                  conf_path=self.conf_path,
                                                  app_path=self.app_path,
                                                  env=self.env,
                                                  service_description=self.service_description)
            use_gssapi = False
            do_gssapi_key_exchange = False

            hostkey = None
            hostkeytype = None
            try:
                host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
            except IOError:
                print('*** Unable to open host keys file')
                host_keys = {}

            if self.target in host_keys:
                hostkeytype = host_keys[self.target].keys()[0]
                hostkey = host_keys[self.target][hostkeytype]

            try:
                k = paramiko.RSAKey.from_private_key_file(self.identity_file)
                t = paramiko.Transport((self.target, self.target_port))
                t.connect(hostkey=hostkey, username=self.deploy_user, gss_host=self.target,
                          gss_auth=use_gssapi, gss_kex=do_gssapi_key_exchange, pkey=k)
                sftp = paramiko.SFTPClient.from_transport(t)
                with sftp.open('/tmp/outfile.txt', 'w') as f:
                    f.write(template_s)

            except Exception as e:
                logger.error('Upload via ssh/sftp failed with error: \n%s\n%s' % (e.__class__, e))
                if log_level == logging.DEBUG:
                    traceback.print_exc()
                try:
                    t.close()
                except:
                    pass
                exit(1)


class BasicSysVTemplate:
    """
    Defines a basic string Template to run on a init.d system
    :param Template template: Specifies the file location to use for the template
    """
    def __init__(self, template='templates/sysv.template'):
        self.template = Template(open(template).read())

    def substitute(self, service_name=None, app_path=None, conf_path=None):
        t = self.template.safe_substitute(servicename=service_name, conf_path=conf_path, app_path=app_path)
        return t


class BasicSysDTemplate:
    """
    Defines a basic string Template to run on a systemd system
    :param Template template: Specifies the file location to use for the template
    """
    def __init__(self, template='templates/sysd.template'):
        self.template = Template(open(template).read())

    def substitute(self, service_name=None, app_path=None, conf_path=None):
        t = self.template.safe_substitute(servicename=service_name, conf_path=conf_path, app_path=app_path)
        return t


def control_service(user='root', host='localhost', service=None, type='sysv', action=None, identity_file=None):
    """
    Method for sending commands to services over SSH.
    Defaults to local host, but requires a service name and an action to perform on it
    e.g. control_service(host=some_host, service=sshd, action=restart)
    Currently no validation performed on the service or action, so make sure you know what you're doing! :)

    :param identity_file:
    :param user: user to use to connect, defaults to root
    :param host: host on which to act
    :param service: service on which to act
    :param type: service type we're acting on sysv or systemd
    :return status: simple bool indicating if we sent the command successfully, no guarantee the command was successful
    """
    status = False
    if (service is None) or (action is None):
        logger.error("Service/action cannot be empty, please specify the service name and action to be performed")
        return status
    if action not in ['start', 'stop', 'restart']:
        logger.error("Action unknown, please specify one of start / stop / restart")
        return status
    if identity_file is None:
        identity_file = os.path.expanduser('~/.ssh/id_rsa')
        logger.info("identity file is %s" % identity_file)
    try:
        k = paramiko.RSAKey.from_private_key_file(identity_file)
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, pkey=k)
    except paramiko.AuthenticationException:
        logger.error("Authentication exception - user is %s, id file is %s" % (user, identity_file))
        pass
    try:
        logger.info("trying to perform a %s on %s, running on %s" % (action, service, host))
        if type == 'sysv':
            stdin, stdout, stderr = ssh.exec_command("sudo /etc/init.d/%s %s" % (service, action), timeout=15, get_pty=True)
        elif type == 'systemd':
            stdin, stdout, stderr = ssh.exec_command("sudo service %s %s" % (service, action), timeout=15, get_pty=True)
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                rl, wl, xl = select.select([stdout.channel], [], [], 0.0)
                if len(rl) > 0:
                    logger.info(stdout.channel.recv(1024),)
    except paramiko.SSHException as e:
        if log_level == logging.DEBUG:
            logger.fatal('Failed with error: \n%s\n%s' % (e.__class__, e))
            traceback.print_exc()
        else:
            pass
    ssh.close()
    status = True
    return status


def test_sysv():
    c = BasicSysVTemplate()
    result = c.template.safe_substitute(servicename='SERVICE-TEST',
                                        conf_path='/opt/conf',
                                        app_path='/opt/apps',
                                        env='dev',
                                        service_description='This is an example service description')
    print result


def test_sysd():
    c = BasicSysDTemplate()
    result = c.template.safe_substitute(servicename='SERVICE-TEST',
                                        conf_path='/opt/conf',
                                        app_path='/opt/apps',
                                        env='dev',
                                        service_description='This is an example service description')
    print result


def test_sysv_config():
    sc = ServiceConfig()
    c = BasicSysVTemplate()
    sc.push_to_server(template=c.template)


def test_service_control():
    control_service(user='jenkins', host='192.168.56.101', service='sshd', type='sysv', action='stop', identity_file='/Users/sjones/.ssh/jenkins_rsa')


test_sysv_config()
test_service_control()

import logging
import yaml
from string import Template
import paramiko
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


__all__ = ['ServiceConfig', 'BasicSysVTemplate', 'BasicSysDTemplate']


log_level = logging.INFO

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
    def __init__(self, filename='service-config.yml'):
        self.conf = {}
        self.filename = filename
        self.service_name = None
        self.conf_path = '/opt/conf'
        self.app_path = '/opt/apps'
        self.service_description = ''

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
            logger.error("service_name not specified in config cannot continue")
            exit(2)
        if 'conf_path' in self.conf:
            self.conf_path = self.conf['conf_path']
        if 'app_path' in self.conf:
            self.app_path = self.conf['app_path']
        if 'service_description' in self.conf:
            self.service_description = self.conf['service_description']

    def push_to_server(self):
        pass


class BasicSysVTemplate():
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

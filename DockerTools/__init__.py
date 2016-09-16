from sys import exit
import os
import yaml
from operator import itemgetter
import logging
import subprocess

"""
Wrapper for jenkins to perform tasks inside a docker containers
Created originally to build NPM projects for CDS Risk
Currently expects to find a docker-runner.yml file in the working directory to load the jobs from.

ToDo: Parameterise the run, possibly just the config file as an option.
ToDo: Check for the presence of the config file and handle errors gracefully

Author: sjones
Date: 2016-08-24
Last update: 2016-09-01
"""

log_level = logging.INFO

sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger = logging.getLogger('DockerTools')
logger.addHandler(sh)
logger.setLevel(log_level)


class DockerBuilder:
    def __init__(self):
        self.base_cmd = 'docker run -v'
        self.sudoit = False
        self.cmd = ''
        self.image = ''
        self.exec_me = ''
        self.label = 'latest'
        self.volume = '/tmp'

    def set_command(self, kwargs):
        if "command" in kwargs:
            self.cmd = kwargs['command']
        if "image" in kwargs:
            self.image = kwargs['image']
        else:
            logger.error("Image not specified")
            exit(2)
        if "label" in kwargs:
            self.label = kwargs['label']
        if "sudoit" in kwargs:
            self.sudoit = kwargs['sudoit']
        if "volume" in kwargs:
            self.volume = '%s%s' % (kwargs['volume'], ':/build')
        else:
            self.volume = './:/build'
        self.assemble_command()

    def run_command(self):
        try:
            logger.info('Running the docker command: "%s"' % self.exec_me)
            my_env = os.environ.copy()
            my_env['PATH'] = '/usr/bin:' + my_env['PATH']
            p = subprocess.Popen(self.exec_me.split(),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 env=my_env,
                                 shell=False)
            std_out, std_err = p.communicate()
            if len(std_err) > 0:
                logger.error(str(std_err))
            if len(std_out) > 0:
                logger.info(str(std_out))
        except OSError as e:
            logger.error("OSError thrown in docker command execution output was \n %s" % e)
            exit(2)
        except RuntimeError as e:
            logger.error("RuntimeError thrown in docker command execution output was \n %s" % e)
            exit(2)
        except RuntimeWarning as e:
            logger.warning("RuntimeWarning on docker command, output was \n %s" % e)

    def set_cmd(self, cmd=None):
        self.cmd = cmd

    def assemble_command(self):
        if self.sudoit:
            self.exec_me = '%s %s %s %s:%s %s' % ('sudo', self.base_cmd, self.volume, self.image, self.label, self.cmd)
        else:
            self.exec_me = '%s %s %s:%s %s' % (self.base_cmd, self.volume, self.image, self.label, self.cmd)
        return self.exec_me


class BuildConf:
    """
    Loads a yaml file into a dictionary for the module to pull from
    :param str filename: yml file to read config from - has default value.

    """

    def __init__(self, filename='docker-runner.yml'):
        logger.debug("Loading config file %s " % filename)
        self.npm_build_conf = {}
        self.filename = filename
        self.read_config()
        self.command_list = []

    def read_config(self):
        try:
            f = open(self.filename)
        except (OSError, IOError):
            logger.fatal("FATAL: Config file (%s) not found" % self.filename)
            exit(2)
        else:
            self.npm_build_conf = yaml.safe_load(f)

    def run_commands(self):
        for cmd in self.command_list:
            run = DockerBuilder()
            run.set_command(cmd)
            run.run_command()

    def build_command_list(self):
        command_list = []
        command = {}
        conf = self.npm_build_conf
        for key in conf:
            command['order'] = conf[key]['order']
            if conf[key]['sudo']:
                command['sudoit'] = conf[key]['sudo']
            if conf[key]['command']:
                command['command'] = conf[key]['command']
            if conf[key]['label']:
                command['label'] = conf[key]['label']
            if conf[key]['image']:
                command['image'] = conf[key]['image']
            if conf[key]['volume']:
                command['volume'] = conf[key]['volume']
            command_list.append(command.copy())
            command.clear()
        self.command_list = sorted(command_list, key=itemgetter('order'))
        # self.run_commands()


#!/usr/bin/env python
from DockerTools import BuildConf


def main():
    bc = BuildConf()
    bc.build_command_list()
    bc.run_commands()

if __name__ == '__main__':
    main()

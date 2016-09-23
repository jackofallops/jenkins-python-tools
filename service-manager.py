from ServiceTools import *

ssh_key = '~/.ssh/jenkins_rsa'
service_command = 'restart'


def main():
    sc = ServiceConfig()
    if sc.conf['system'] == 'sysv':
        template = BasicSysVTemplate()
    elif sc.conf['system'] == 'systemd':
        template = BasicSysDTemplate()

    sc.push_to_server(template.template)
    control_service(sc.deploy_user, sc.host, sc.service_name, sc.system, service_command, ssh_key)

if __name__ == '__main__':
    main()

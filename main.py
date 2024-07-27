import os
import sys
import socket
import configparser
from zabbix_utils import ZabbixAPI, exceptions


CONFIG_PATH = '/etc/sdmon.conf'


def get_config():
    # Create config file if it doesn't exist
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            pass

    # Read config
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)

    # Ensure configuration contain all needed elements
    if 'zabbix' not in config.sections():
        config['zabbix'] = {}
    if 'server' not in config['zabbix']:
        config['zabbix']['server'] = ''
    if 'token' not in config['zabbix']:
        config['zabbix']['token'] = ''
    if 'hostname' not in config['zabbix']:
        config['zabbix']['hostname'] = socket.gethostname()

    with open(CONFIG_PATH, 'w') as configfile:
        config.write(configfile)

    if config['zabbix']['server'] == '' or config['zabbix']['token'] == '':
        print(f'Error: Please fill the configuration file "{CONFIG_PATH}" first.')
        sys.exit(1)

    return config


def zabbix_create_service(zabbix_server, token, hostname, service):
    api = ZabbixAPI(url=zabbix_server)
    api.login(token=token)

    # Get host id
    hosts = api.send_api_request('host.get')['result']
    host_id = None
    for host in hosts:
        if host['host'] == hostname:
            host_id = host['hostid']
            break
    if host_id is None:
        raise Exception(f'Could not find host "{hostname}" on zabbix server.')

    # Get interface id
    interfaces = api.send_api_request('hostinterface.get', {
        'output': ['interfaceids'],
        'hostids': host_id
    })['result']
    if len(interfaces) == 0:
        raise Exception(f'Host "{hostname}" doesn\'t have any interfaces.')
    interface_id = interfaces[0]['interfaceid']

    # Create item
    item = f'systemd.unit.info["{service}.service"]'
    try:
        api.send_api_request('item.create', {
            'hostid': host_id,
            'name': f'Service {service} by sdmon',
            'key_': item,
            'interfaceid': interface_id,
            'type': 0,
            'value_type': 1,
            'delay': '15s',
            'tags': [
                {'tag': 'sdmon'}
            ]
        })
    except exceptions.APIRequestError as error:
        if 'already exists on the host' not in str(error):
            raise error

    # Create trigger
    api.send_api_request('trigger.create', {
        'description': f'Sdmon service "{service}" is not active',
        'expression': f'last(/{hostname}/{item})<>"active"',
        'priority': 4,
        'tags': [
            {'tag': 'sdmon'}
        ]
    })


def zabbix_delete_service(zabbix_server, token, hostname, service):
    api = ZabbixAPI(url=zabbix_server)
    api.login(token=token)

    # Get & delete the trigger
    triggers = api.send_api_request('trigger.get', {
        'output': ['triggerid'],
        'filter': {
            'description': f'Sdmon service "{service}" is not active'
        }
    })['result']
    if len(triggers) > 0:
        api.send_api_request('trigger.delete', [trigger['triggerid'] for trigger in triggers])

    # Get host id
    hosts = api.send_api_request('host.get')['result']
    host_id = None
    for host in hosts:
        if host['host'] == hostname:
            host_id = host['hostid']
            break
    if host_id is None:
        raise Exception(f'Could not find host "{hostname}" on zabbix server.')

    # Get and delete the item
    items = api.send_api_request('item.get', {
        'output': ['itemid'],
        'filter': {
            'hostid': host_id,
            'name': f'Service {service} by sdmon'
        }
    })['result']
    if len(items) > 0:
        api.send_api_request('item.delete', [item['itemid'] for item in items])


def systemd_create_service(service, command):
    with open(f'/etc/systemd/system/{service}.service', 'w') as f:
        f.write('[Unit]\n'
                f'Description={service} service made by sdmon.\n'
                f'After=network.target\n'
                f'\n'
                f'[Service]\n'
                f'User=root\n'
                f'Group=root\n'
                f'WorkingDirectory={os.getcwd()}\n'
                f'ExecStart={command} > /var/log/{service}.log\n'
                f'RestartSec=5\n'
                f'\n'
                f'[Install]\n'
                f'WantedBy=multi-user.target')
    os.system('systemctl daemon-reload')
    os.system(f'systemctl enable --now {service}.service')


def systemd_delete_service(service):
    os.system(f'systemctl stop {service}.service')
    os.system(f'systemctl disable {service}.service')
    os.system(f'rm -f /etc/systemd/system/{service}.service')
    os.system('systemctl daemon-reload command')


try:
    config = get_config()
    server = config['zabbix']['server']
    token = config['zabbix']['token']
    hostname = config['zabbix']['hostname']

    if len(sys.argv) < 3:
        print(f'Usage:\n'
              f'\t{sys.argv[0]} <service name> <command>\n'
              f'\t{sys.argv[0]} delete <service name>')
        sys.exit(1)

    if sys.argv[1] == 'delete':
        systemd_delete_service(sys.argv[1])
        zabbix_delete_service(server, token, hostname, sys.argv[1])
        print(f'Service "{sys.argv[1]}" has been deleted.')
    else:
        systemd_create_service(sys.argv[1], ' '.join(sys.argv[2:]))
        zabbix_create_service(server, token, hostname, sys.argv[1])
        print(f'Service {sys.argv[1]} has been created.')
except Exception as error:
    print(f'Error: {str(error)}')

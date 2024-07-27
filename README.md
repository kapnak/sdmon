# sdmon

sdmon is a small linux utility to create a systemd services
from a command and add a Zabbix trigger in same time.

## Installation

From compiled release :
```shell
wget https://github.com/kapnak/sdmon/releases/latest
cp sdmon /usr/local/bin/sdmon
```

From sources :
```shell
git clone https://github.com/kapnak/sdmon
cd sdmon
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pyinstaller -F -n sdmon main.py
cp dist/sdmon /usr/local/bin/sdmon
```


## Configuration

Edit the file `/etc/sdmon.conf` :
```shell
[zabbix]
server=
token=
hostname=
```
If the file doesn't exist, you can create it or execute `sdmon` one time.
- `server` must contain the link to zabbix like `165.145.11.2/zabbix`.
- `token` must be created on Zabbix before.
- `hostname` is the hostname configured on Zabbix of the current local machine.
By default, the hostname of the machine will be used.


## Usages

### Create a service

```shell
sdmon <service name> <command>
```

This command will :
- Create a service called <service name>.
- Start and enable the service.
- Create an item and a trigger on the configured Zabbix server.


### Delete a service

```shell
sdmon delete <service name>
```

This command will :
- Stop and disable the service.
- Delete the service.
- Delete the Zabbix item and trigger.

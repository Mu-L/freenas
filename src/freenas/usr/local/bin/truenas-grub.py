#!/usr/bin/env python3
import sqlite3

from middlewared.plugins.config import FREENAS_DATABASE


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def retrieve_grub_config():
    config = {
        'GRUB_DISTRIBUTOR': ['TrueNAS Scale'],
        'GRUB_CMDLINE_LINUX_DEFAULT': [],
        'GRUB_TERMINAL': ['console'],
        'GRUB_CMDLINE_LINUX': []
    }
    conn = sqlite3.connect(FREENAS_DATABASE)
    conn.row_factory = dict_factory
    c = conn.cursor()
    c.execute("SELECT * FROM system_advanced")
    advanced = {k.replace('adv_', ''): v for k, v in c.fetchone().items()}
    if advanced['serialconsole']:
        config['GRUB_SERIAL_COMMAND'] = [
            'serial', f'--speed={advanced["serialspeed"]}', '--word=8', '--parity=no', '--stop=1'
        ]
        config['GRUB_TERMINAL'].append('serial')
        config['GRUB_CMDLINE_LINUX'].extend([
            f'console={advanced["serialport"]},{advanced["serialspeed"]}', 'console=tty1'
        ])
    return config


def convert_config_to_file(config):
    return '\n'.join([f'{k}="{" ".join(v)}"' for k, v in config.items()])


def update_truenas_cfg(config):
    with open('/etc/default/grub.d/truenas.cfg', 'w') as f:
        f.write(convert_config_to_file(config))


if __name__ == '__main__':
    update_truenas_cfg(retrieve_grub_config())

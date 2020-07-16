import subprocess

from middlewared.service import CallError
from middlewared.utils.path import module_from_file


def render(service, middleware):
    tn_grub = module_from_file('truenas-grub', '/usr/local/bin/truenas-grub.py')
    config = tn_grub.retrieve_grub_config()
    kdump_enabled = middleware.call_sync('system.advanced.config')['kdump_enabled']
    if kdump_enabled:
        config['GRUB_CMDLINE_LINUX'].append(
            f'crashkernel={middleware.call_sync("system.required_crash_kernel_memory")}M'
        )

    tn_grub.update_truenas_cfg(config)

    cp = subprocess.Popen(['update-grub'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stderr = cp.communicate()[1]
    if cp.returncode:
        middleware.logger.error('Update grub failed: %s', stderr.decode())
        raise CallError(f'Update grub failed: {stderr.decode()}')

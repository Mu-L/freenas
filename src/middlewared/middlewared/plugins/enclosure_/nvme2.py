# Copyright (c) - iXsystems Inc. dba TrueNAS
#
# Licensed under the terms of the TrueNAS Enterprise License Agreement
# See the file LICENSE.IX for complete terms and conditions

import pathlib
import re

from pyudev import Context, Devices, DeviceNotFoundAtPathError

from ixhardware import parse_dmi
from .constants import (
    DISK_FRONT_KEY,
    DISK_REAR_KEY,
    DISK_TOP_KEY,
    DISK_INTERNAL_KEY,
    DRIVE_BAY_LIGHT_STATUS,
    SUPPORTS_IDENTIFY_KEY,
    SUPPORTS_IDENTIFY_STATUS_KEY,
)
from .enums import ControllerModels
from .slot_mappings import get_nvme_slot_info

RE_SLOT = re.compile(r'^0-([0-9]+)$')


def fake_nvme_enclosure(model, num_of_nvme_slots, mapped, ui_info=None):
    """This function takes the nvme devices that been mapped
    to their respective slots and then creates a "fake" enclosure
    device that matches (similarly) to what our real enclosure
    mapping code does (map_enclosures()). It's _VERY_ important
    that the keys in the `fake_enclosure` dictionary exist because
    our generic enclosure mapping logic expects certain top-level
    keys.

    Furthermore, we generate DMI (SMBIOS) information for this
    "fake" enclosure because our enclosure mapping logic has to have
    a guaranteed unique key for each enclosure so it can properly
    map the disks accordingly
    """
    # TODO: The `fake_enclosure` object should be removed from this
    # function and should be generated by the
    # `plugins.enclosure_/enclosure_class.py:Enclosure` class so we
    # can get rid of duplicate logic in this module and in that class
    dmi = f'{model.lower()}_nvme_enclosure'
    fake_enclosure = {
        'id': dmi,
        'dmi': dmi,
        'model': model,
        'should_ignore': False,
        'sg': None,
        'bsg': None,
        'name': f'{model} NVMe Enclosure',
        'controller': True,
        'status': ['OK'],
        'elements': {'Array Device Slot': {}}
    }
    if ui_info is not None:
        fake_enclosure.update(ui_info)

    disks_map = get_nvme_slot_info(model)
    if not disks_map:
        fake_enclosure['should_ignore'] = True
        return [fake_enclosure]

    for slot in range(1, num_of_nvme_slots + 1):
        device = mapped.get(slot, None)
        # the `value_raw` variables represent the
        # value they would have if a device was
        # inserted into a proper SES device (or not).
        # Since this is NVMe (which deals with PCIe)
        # that paradigm doesn't exist per se but we're
        # "faking" a SES device, hence the hex values.
        # The `status` variables use same logic.
        if device is not None:
            status = 'OK'
            value_raw = 0x1000000
        else:
            status = 'Not installed'
            value_raw = 0x5000000

        mapped_slot = disks_map['versions']['DEFAULT']['id'][dmi][slot]['mapped_slot']
        light = disks_map['versions']['DEFAULT']['id'][dmi][slot][SUPPORTS_IDENTIFY_KEY]
        dfk = disks_map['versions']['DEFAULT']['id'][dmi][slot][DISK_FRONT_KEY]
        drk = disks_map['versions']['DEFAULT']['id'][dmi][slot][DISK_REAR_KEY]
        dtk = disks_map['versions']['DEFAULT']['id'][dmi][slot][DISK_TOP_KEY]
        dik = disks_map['versions']['DEFAULT']['id'][dmi][slot][DISK_INTERNAL_KEY]

        # light_status will follow light unless we explicitedly override
        light_status = disks_map['versions']['DEFAULT']['id'][dmi][slot].get(SUPPORTS_IDENTIFY_STATUS_KEY, light)
        if light_status:
            # Currently do not have an nvme platform that supports retrieving IDENT status
            raise NotImplementedError
        else:
            led = None

        fake_enclosure['elements']['Array Device Slot'][mapped_slot] = {
            'descriptor': f'Disk #{slot}',
            'status': status,
            'value': None,
            'value_raw': value_raw,
            'dev': device,
            SUPPORTS_IDENTIFY_KEY: light,
            DRIVE_BAY_LIGHT_STATUS: led,
            DISK_FRONT_KEY: dfk,
            DISK_REAR_KEY: drk,
            DISK_TOP_KEY: dtk,
            DISK_INTERNAL_KEY: dik,
            'original': {
                'enclosure_id': dmi,
                'enclosure_sg': None,
                'enclosure_bsg': None,
                'descriptor': f'slot{slot}',
                'slot': slot,
            }
        }

    return [fake_enclosure]


def map_plx_nvme(model, ctx):
    num_of_nvme_slots = 4  # nvme plx bridge used on m50/60 and r50bm have 4 nvme drive bays
    addresses_to_slots = {
        (slot / 'address').read_text().strip(): slot.name
        for slot in pathlib.Path('/sys/bus/pci/slots').iterdir()
    }
    mapped = dict()
    for i in filter(lambda x: x.attributes.get('path') == b'\\_SB_.PC03.BR3A', ctx.list_devices(subsystem='acpi')):
        try:
            physical_node = Devices.from_path(ctx, f'{i.sys_path}/physical_node')
        except DeviceNotFoundAtPathError:
            # happens when there are no rear-nvme drives plugged in
            pass
        else:
            for child in physical_node.children:
                if child.properties.get('SUBSYSTEM') != 'block':
                    continue

                try:
                    controller_sys_name = child.parent.parent.sys_name
                except AttributeError:
                    continue

                if (slot := addresses_to_slots.get(controller_sys_name.split('.')[0])) is None:
                    continue

                if not (m := re.match(RE_SLOT, slot)):
                    continue

                slot = int(m.group(1))
                if model == 'R50BM':
                    # When adding this code and testing on internal R50BM, the starting slot
                    # number for the rear nvme drive bays starts at 2 and goes to 5. This means
                    # we're always off by 1. The easiest solution is to just check for this
                    # specific platform and subtract 1 from the slot number to keep everything
                    # in check.
                    # To make things event more complicated, we found (by testing on internal hardware)
                    # that slot 2 on OS is actually slot 3 and vice versa. This means we need to swap
                    # those 2 numbers with each other to keep the webUI lined up with reality.
                    slot -= 1
                    if slot == 2:
                        slot = 3
                    elif slot == 3:
                        slot = 2

                mapped[slot] = child.sys_name

    return fake_nvme_enclosure(model, num_of_nvme_slots, mapped)


def map_r50_or_r50b(model, ctx):
    num_of_nvme_slots = 3 if model == 'R50' else 2  # r50 has 3 rear nvme slots, r50b has 2
    if model == 'R50':
        acpihandles = {b'\\_SB_.PC00.RP01.PXSX': 3, b'\\_SB_.PC01.BR1A.OCL0': 1, b'\\_SB_.PC01.BR1B.OCL1': 2}
    else:
        acpihandles = {b'\\_SB_.PC03.BR3A': 2, b'\\_SB_.PC00.RP01.PXSX': 1}

    mapped = dict()
    for i in filter(lambda x: x.attributes.get('path') in acpihandles, ctx.list_devices(subsystem='acpi')):
        acpi_handle = i.attributes.get('path')
        try:
            phys_node = Devices.from_path(ctx, f'{i.sys_path}/physical_node')
        except DeviceNotFoundAtPathError:
            break

        slot = acpihandles[acpi_handle]
        for nvme in filter(lambda x: x.sys_name.startswith('nvme') and x.subsystem == 'block', phys_node.children):
            mapped[slot] = nvme.sys_name
            break
        else:
            mapped[slot] = None

        if len(mapped) == num_of_nvme_slots:
            # there can be (and often is) TONS of acpi devices on
            # any given system so once we've mapped the total # of
            # nvme drives, we break out early as to be as efficient
            # as possible
            break

    return fake_nvme_enclosure(model, num_of_nvme_slots, mapped)


def map_r30_r60_or_fseries(model, ctx):
    nvmes = {}
    for i in ctx.list_devices(subsystem='nvme'):
        for namespace_dev in i.children:
            if namespace_dev.device_type != 'disk':
                continue

            try:
                # i.parent.sys_name looks like 0000:80:40.0
                # namespace_dev.sys_name looks like nvme1n1
                nvmes[i.parent.sys_name[:-2]] = namespace_dev.sys_name
            except (IndexError, AttributeError):
                continue

    # the keys in this dictionary are the physical pcie slot ids
    # and the values are the slots that the webUI uses to map them
    # to their physical locations in a human manageable way
    internal_slots = rear_slots = 0
    if model == ControllerModels.R30.value:
        webui_map = {
            '27': 1, '26': 7, '25': 2, '24': 8,
            '37': 3, '36': 9, '35': 4, '34': 10,
            '45': 5, '47': 11, '40': 6, '41': 12,
            '38': 14, '39': 16, '43': 13, '44': 15,
        }
        # r30 has 12 front nvme bays, and 4 internal bays
        num_of_nvme_slots = 16
        front_slots = 12
        internal_slots = 4
    elif model == ControllerModels.R60.value:
        webui_map = {
            '1': 1, '3': 2, '5': 3, '7': 4, '9': 5, '11': 6,
            '2': 7, '4': 8, '6': 9, '8': 10, '10': 11, '12': 12,
        }
        num_of_nvme_slots = front_slots = len(webui_map)
    else:
        # f-series vendor is nice to us and nvme phys slots start at 1
        # and increment in a human readable way already
        webui_map = {
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
            '7': 7, '8': 8, '9': 9, '10': 10, '11': 11, '12': 12,
            '13': 13, '14': 14, '15': 15, '16': 16, '17': 17, '18': 18,
            '19': 19, '20': 20, '21': 21, '22': 22, '23': 23, '24': 24,
        }
        num_of_nvme_slots = front_slots = len(webui_map)

    mapped = {}
    for i in pathlib.Path('/sys/bus/pci/slots').iterdir():
        addr = (i / 'address').read_text().strip()
        if (nvme := nvmes.get(addr, None)) and (mapped_slot := webui_map.get(i.name, None)):
            mapped[mapped_slot] = nvme

    ui_info = {
        'rackmount': True,
        'top_loaded': False,
        'front_loaded': True,
        'front_slots': front_slots,
        'rear_slots': rear_slots,
        'internal_slots': internal_slots
    }
    return fake_nvme_enclosure(model, num_of_nvme_slots, mapped, ui_info)


def map_nvme():
    model = parse_dmi().system_product_name.removeprefix('TRUENAS-')
    model = model.removesuffix('-S').removesuffix('-HA')
    ctx = Context()
    if model in (
        ControllerModels.R50.value,
        ControllerModels.R50B.value,
    ):
        return map_r50_or_r50b(model, ctx)
    elif model in (
        ControllerModels.R30.value,
        ControllerModels.R60.value,
        ControllerModels.F60.value,
        ControllerModels.F100.value,
        ControllerModels.F130.value,
    ):
        # all nvme systems which we need to handle separately
        return map_r30_r60_or_fseries(model, ctx)
    elif model in (
        ControllerModels.M30.value,
        ControllerModels.M40.value,
        ControllerModels.M50.value,
        ControllerModels.M60.value,
        ControllerModels.R50BM.value,
    ):
        return map_plx_nvme(model, ctx)
    else:
        return []

from dataclasses import dataclass
from enum import IntEnum
from subprocess import CompletedProcess

from middlewared.utils import run

__all__ = ("unlock_impl",)


class ReturnCodeMappings(IntEnum):
    SUCCESS = 0
    AUTH_FAILED = 135
    INVALID_OR_UNSUPPORTED = 136


@dataclass(slots=True, frozen=True, kw_only=True)
class UnlockResponses:
    disk_path: str
    """The absolute path of the disk."""
    invalid_or_unsupported: bool = False
    """Does the disk support SED or is it valid?"""
    locked: bool | None = None
    """Is the disk locked?"""
    query_cp: CompletedProcess | None = None
    """The response of `sedutil-cli --query` command"""
    unlock_cp: CompletedProcess | None = None
    """The response of `sedutil-cli --setLockingRange` command."""
    mbr_cp: CompletedProcess | None = None
    """The response of `sedutil-cli --setMBREnable off` command."""


async def run_sedutil_cmd(cmd: list[str]) -> CompletedProcess:
    return await run(["sedutil-cli"] + cmd, check=False)


async def unlock_tcg_opal_pyrite(disk_path: str, password: str) -> UnlockResponses:
    query_cp = await run_sedutil_cmd(["--query", disk_path])
    if (
        query_cp.returncode == ReturnCodeMappings.INVALID_OR_UNSUPPORTED
        or query_cp.returncode != ReturnCodeMappings.SUCCESS
    ):
        return UnlockResponses(
            disk_path=disk_path, invalid_or_unsupported=True, query_cp=query_cp
        )
    elif b"Locked = N" in query_cp.stdout:
        return UnlockResponses(disk_path=disk_path, locked=False, query_cp=query_cp)

    use_fbsd_compat = False
    cmd = ["--setLockingRange", "0", "RW", password, disk_path]
    unlock_cp = await run_sedutil_cmd(cmd)
    if unlock_cp.returncode == ReturnCodeMappings.AUTH_FAILED:
        # Sigh, sedutil-cli (by default) uses an asinine,
        # non-portable "hashing" mechanism for the password
        # BY DEFAULT....This means the password you typed
        # on freeBSD to setup the drive will NOT work when
        # given on linux (and vice versa). Since we're now
        # stuck with this head-ache, we'll try again with
        # the `-freebsdCompat` flag.
        cmd.insert(0, "-freebsdCompat")
        unlock_cp = await run_sedutil_cmd(cmd)
        use_fbsd_compat = unlock_cp.returncode == ReturnCodeMappings.SUCCESS

    if unlock_cp.returncode != ReturnCodeMappings.SUCCESS:
        return UnlockResponses(disk_path=disk_path, locked=True, unlock_cp=unlock_cp)

    # Disable Master Boot Record (MBR) Shadowing Support.
    # The host application can store and execute a
    # “Pre-Boot Authentication (PBA) Environment” to
    # unlock the range in which the OS is stored so that
    # the OS can boot.
    mbr_cmd = ["--setMBREnable", "off", password, disk_path]
    if use_fbsd_compat:
        mbr_cmd.insert(0, "-freebsdCompat")

    mbr_cp = await run_sedutil_cmd(mbr_cmd)
    return UnlockResponses(
        disk_path=disk_path, locked=False, unlock_cp=unlock_cp, mbr_cp=mbr_cp
    )


async def unlock_impl(disk: dict[str, str]) -> UnlockResponses:
    """Try to unlock the self encrypting drive (SED). The
    drive must conform to one of the Trusted Computing Group (TCG)
    Enterprise, Opal, Opalite or Pyrite SSC specifications."""
    return await unlock_tcg_opal_pyrite(disk['path'], disk['passwd'])

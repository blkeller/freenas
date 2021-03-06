import logging

from middlewared.utils import run

logger = logging.getLogger(__name__)


async def get_exports(middleware, config, shares, kerberos_keytabs):
    result = []

    sec = await middleware.call("nfs.sec", config, kerberos_keytabs)
    if sec:
        result.append(f"V4: / -sec={':'.join(sec)}")

    for share in shares:
        if share["paths"]:
            result.extend(build_share(config, share))

    return "\n".join(result) + "\n"


def build_share(config, share):
    if share["paths"]:
        result = list(share["paths"])

        if share["alldirs"]:
            result.append("-alldirs")

        if share["ro"]:
            result.append("-ro")

        if share["quiet"]:
            result.append("-quiet")

        if share["mapall_user"]:
            s = '-mapall="' + share["mapall_user"].replace('\\', '\\\\') + '"'
            if share["mapall_group"]:
                s += ':"' + share["mapall_group"].replace('\\', '\\\\') + '"'
            result.append(s)
        elif share["maproot_user"]:
            s = '-maproot="' + share["maproot_user"].replace('\\', '\\\\') + '"'
            if share["maproot_group"]:
                s += ':"' + share["maproot_group"].replace('\\', '\\\\') + '"'
            result.append(s)

        if config["v4"] and share["security"]:
            result.append("-sec=" + ":".join([s.lower() for s in share["security"]]))

        targets = build_share_targets(share)
        if targets:
            return [" ".join(result + [target])
                    for target in targets]
        else:
            return [" ".join(result)]

    return []


def build_share_targets(share):
    result = []

    for network in share["networks"]:
        result.append("-network " + network)

    if share["hosts"]:
        result.append(" ".join(share["hosts"]))

    return result


async def render(service, middleware):
    config = await middleware.call("nfs.config")

    shares = await middleware.call("sharing.nfs.query", [["enabled", "=", True]])

    kerberos_keytabs = await middleware.call("kerberos.keytab.query")

    with open("/etc/exports", "w") as f:
        f.write(await get_exports(middleware, config, shares, kerberos_keytabs))

    await run("service", "mountd", "quietreload", check=False)

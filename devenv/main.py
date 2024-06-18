from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence

from devenv import bootstrap
from devenv import doctor
from devenv import fetch
from devenv import pin_gha
from devenv import sync
from devenv.constants import home
from devenv.lib.config import read_config
from devenv.lib.context import Context
from devenv.lib.fs import gitroot
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import ExitCode
from devenv.lib.repository import Repository


def devenv(argv: Sequence[str], config_path: str) -> ExitCode:
    # determine current repo, if applicable
    fake_reporoot = os.getenv("CI_DEVENV_INTEGRATION_FAKE_REPOROOT")
    if fake_reporoot:
        current_root = fake_reporoot
    else:
        try:
            current_root = gitroot()
        except RuntimeError:
            current_root = None

    # This may or may not exist
    config = read_config(config_path)

    # Guessing temporary code root
    code_root = config.get("devenv", "coderoot", fallback=None) or (
        os.path.abspath(f"{current_root}/..")
        if current_root
        else os.path.expanduser("~/code")
    )

    modinfo_list: Sequence[DevModuleInfo] = [
        module.module_info
        for module in [bootstrap, fetch, doctor, pin_gha, sync]
        if hasattr(module, "module_info")
    ]

    # TODO: Search for modules in work repo

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(
        title=argparse.SUPPRESS,
        metavar="command",
        dest="command",
        required=True,
    )

    for info in modinfo_list:
        # Argparse stuff
        subparser.add_parser(info.command, help=info.help)

    args, remainder = parser.parse_known_args(argv[1:])

    # context for subcommands
    context: Context = {
        "config_path": config_path,
        "code_root": code_root,
        "repo": Repository(current_root) if current_root else None,
    }

    command_actions = {info.command: info.action for info in modinfo_list}
    action = command_actions.get(args.command)
    assert action is not None
    return action(context, remainder)


def main() -> ExitCode:
    # this is also used to see if we're the child process
    script_logfile = os.environ.get("SCRIPT")

    if script_logfile:
        return devenv(sys.argv, f"{home}/.config/sentry-devenv/config.ini")

    import tempfile

    _, fp = tempfile.mkstemp()
    # script (macos/linux) runs the subcommand with a tty, and tees the output to a file.
    # this way we can very easily capture all output from devenv and send it
    # to sentry as an attachment if an error occurs.
    cmd = ("/usr/bin/script", "-qe", fp, *sys.argv)

    import sentry_sdk
    from sentry_sdk.scope import Scope

    sentry_sdk.init(
        # https://sentry.sentry.io/settings/projects/sentry-dev-env/keys/
        dsn="https://9bdb053cb8274ea69231834d1edeec4c@o1.ingest.sentry.io/5723503",
        enable_tracing=True,
    )

    scope = Scope.get_current_scope()
    root_transaction = scope.start_transaction()

    # the reason we're subprocessing instead of os.execv(cmd[0], cmd)
    # is that script must exit (so that the complete log file is committed to disk)
    # before sentry sends the event...
    with root_transaction.start_child():
        rc = subprocess.call(cmd)

    if rc == 0:
        return rc

    #import getpass

    # would really like to be able to set filename to the python exception title
    # because seeing KeyboardInterrupt vs CalledProcessError is more helpful than
    # "tmp29387ldf", but see above comment
    #scope.add_attachment(path=fp)
    #print(fp)

#    client = Scope.get_client()

    #user = getpass.getuser()
#    computer = client.options.get("server_name", "unknown")

    # events are grouped under user@computer
    #scope.fingerprint = [f"{user}@test"]

    breakpoint()
    event_id = root_transaction.finish()

    # trace
    # https://sentry.sentry.io/performance/trace/d86e9d23141f41e2b335fc219e82d3e0

    # event id feb696d0c83a44a1a73c69f31f10635e
    # cant find this anywhere though
    # this page doesnt load
    # https://sentry.sentry.io/issues/5504551756/events/feb696d0c83a44a1a73c69f31f10635e/?project=5723503

    # https://sentry.sentry.io/traces/?project=5723503&query=project%3Asentry-dev-env&statsPeriod=24h
    # trace overview

    # so i dont think an issue is being created, despite an event being created

    print("trace id: ", root_transaction.trace_id)
    print(event_id)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())

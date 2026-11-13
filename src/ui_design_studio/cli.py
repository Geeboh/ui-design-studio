"""Installed engine CLI and local MCP stdio launcher."""
from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncIterator
from contextlib import nullcontext
import ipaddress
import json
import os
from pathlib import Path
import shlex
import signal
import sys
import threading

import anyio
from mcp.server.stdio import stdio_server

from .dashboard import AmbiguousSessions, DashboardSession, DashboardUnavailable, discover, format_dashboard_text
from .runtime import studio
from .server import create_server


def _repo(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise argparse.ArgumentTypeError("--repo must be an absolute existing repository directory")
    return path.resolve()


def _port(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("dashboard port must be an integer from 0 to 65535") from exc
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError("dashboard port must be an integer from 0 to 65535")
    return number


def _ipv4(value: str) -> str:
    try:
        return str(ipaddress.IPv4Address(value))
    except ipaddress.AddressValueError as exc:
        raise argparse.ArgumentTypeError("LAN address must be an IPv4 address on a local interface") from exc


def _terminal_text(value: object) -> str:
    return "".join(f"\\u{ord(character):04x}" if ord(character) < 32 or 127 <= ord(character) <= 159 else character
                   for character in str(value))


class _InterruptibleInput(anyio.AsyncFile[str]):
    async def __aiter__(self) -> AsyncIterator[str]:
        # The SDK's default readline shields blocked pipes and prevents SIGTERM cleanup.
        loop = asyncio.get_running_loop()
        chunks: asyncio.Queue[bytes | OSError] = asyncio.Queue()
        capacity = threading.Semaphore(1)

        def read_pipe():
            while True:
                try:
                    chunk = os.read(self.wrapped.fileno(), 65536)
                except OSError as exc:
                    chunk = exc
                capacity.acquire()
                try:
                    loop.call_soon_threadsafe(chunks.put_nowait, chunk)
                except RuntimeError:
                    return
                if isinstance(chunk, OSError) or not chunk:
                    return

        # Abandoned thread-pool reads are non-daemon and block interpreter exit.
        threading.Thread(target=read_pipe, name="ui-design-stdio", daemon=True).start()
        pending = b""
        while True:
            chunk = await chunks.get()
            capacity.release()
            if isinstance(chunk, OSError):
                raise chunk
            if not chunk:
                if pending:
                    yield pending.decode("utf-8", errors="replace")
                return
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                yield line.decode("utf-8", errors="replace") + "\n"


async def _serve_stdio(server) -> None:
    with (anyio.open_signal_receiver(signal.SIGTERM) if sys.platform != "win32" else nullcontext()) as signals:
        async with anyio.create_task_group() as group:
            async def stop_on_signal():
                async for unused in signals:
                    group.cancel_scope.cancel()
                    return

            if signals is not None:
                group.start_soon(stop_on_signal)
            try:
                async with stdio_server(stdin=_InterruptibleInput(sys.stdin)) as (read, write):
                    await server._mcp_server.run(read, write, server._mcp_server.create_initialization_options())
            finally:
                group.cancel_scope.cancel()


def mcp_main(argv: list[str] | None = None) -> int:
    """Start one MCP stdio connection with an explicit, fixed repository boundary."""
    parser = argparse.ArgumentParser(prog="ui-design-mcp", description=__doc__)
    parser.add_argument("--repo", required=True, type=_repo)
    parser.add_argument("--dashboard-host", choices=("0.0.0.0", "127.0.0.1"), default="0.0.0.0")
    parser.add_argument("--dashboard-port", type=_port, default=0)
    parser.add_argument("--lan-address", type=_ipv4)
    args = parser.parse_args(argv)
    try:
        server = create_server(args.repo, dashboard_host=args.dashboard_host,
                               dashboard_port=args.dashboard_port, lan_address=args.lan_address)
        anyio.run(_serve_stdio, server)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        while len(getattr(exc, "exceptions", ())) == 1:
            exc = exc.exceptions[0]
        print("[error] " + _terminal_text(exc), file=sys.stderr)
        return 1


class _DashboardParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise argparse.ArgumentError(None, message)


def _dashboard_info(argv: list[str]) -> int:
    parser = _DashboardParser(prog="ui-design dashboard-info",
                              description="Print verified dashboard URLs and a local terminal QR code.")
    parser.add_argument("--repo", required=True, type=_repo)
    selectors = parser.add_mutually_exclusive_group()
    selectors.add_argument("--run")
    selectors.add_argument("--session")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
    except argparse.ArgumentError as exc:
        message = _terminal_text(exc)
        if "--json" in argv:
            print(json.dumps({"schemaVersion": "1.0", "status": "FAIL", "error": message}, ensure_ascii=False))
        else:
            parser.print_usage(sys.stderr)
            print(f"{parser.prog}: error: {message}", file=sys.stderr)
        return 2
    try:
        details = discover(args.repo, session=args.session, run=args.run)
    except AmbiguousSessions as exc:
        ids = [_terminal_text(item) for item in exc.session_ids]
        commands = [f"ui-design dashboard-info --repo {shlex.quote(str(args.repo))} --session {shlex.quote(item)}"
                    for item in ids]
        error = {"schemaVersion": "1.0", "status": "FAIL", "error": "Multiple dashboards are running. Select a session.",
                 "sessionIds": ids, "commands": commands}
        if args.json:
            print(json.dumps(error, ensure_ascii=False))
        else:
            print("[error] " + error["error"], file=sys.stderr)
            for instance_id, command in zip(ids, commands):
                print(f"{instance_id}\n{command}", file=sys.stderr)
        return 2
    except (DashboardUnavailable, ValueError, OSError, studio().StudioError) as exc:
        message = "Dashboard is not running." if isinstance(exc, DashboardUnavailable) else _terminal_text(exc)
        if args.json:
            print(json.dumps({"schemaVersion": "1.0", "status": "FAIL", "error": message}, ensure_ascii=False))
        else:
            print("[error] " + message, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(details, ensure_ascii=False))
    else:
        sys.stdout.write(details["text"])
        if not details["text"].endswith("\n"):
            sys.stdout.write("\n")
    return 0


def _dashboard_serve(argv: list[str]) -> int:
    parser = _DashboardParser(prog="ui-design dashboard-serve",
                              description="Keep a verified dashboard available until stopped.")
    parser.add_argument("--repo", required=True, type=_repo)
    parser.add_argument("--dashboard-host", choices=("0.0.0.0", "127.0.0.1"), default="0.0.0.0")
    parser.add_argument("--dashboard-port", type=_port, default=0)
    parser.add_argument("--lan-address", type=_ipv4)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--parent-stdio", action="store_true", help="Stop when the supervising parent's stdin closes.")
    try:
        args = parser.parse_args(argv)
    except argparse.ArgumentError as exc:
        message = _terminal_text(exc)
        if "--json" in argv:
            print(json.dumps({"schemaVersion": "1.0", "status": "FAIL", "error": message}, ensure_ascii=False))
        else:
            parser.print_usage(sys.stderr)
            print(f"{parser.prog}: error: {message}", file=sys.stderr)
        return 2

    stopped = threading.Event()
    parent_errors: list[Exception] = []
    previous_signals = {}
    session = None
    readiness_sent = False
    exit_status = 0

    def stop_on_signal(signum, unused_frame):
        nonlocal exit_status
        if signum == signal.SIGINT:
            exit_status = 130
        stopped.set()

    def read_parent():
        try:
            while os.read(sys.stdin.fileno(), 65536):
                pass
        except Exception as exc:
            parent_errors.append(exc)
        finally:
            stopped.set()

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_signals[signum] = signal.signal(signum, stop_on_signal)
        try:
            session = DashboardSession(args.repo, host=args.dashboard_host,
                                       port=args.dashboard_port, lan_address=args.lan_address)
            if args.parent_stdio:
                # A parent can disappear while this bounded pipe read is blocked.
                threading.Thread(target=read_parent, name="ui-design-dashboard-stdin", daemon=True).start()
            session.start()
            if not stopped.is_set():
                details = discover(args.repo, session=session.instance_id)
                stop_instruction = "/ui-design-dashboard stop to stop" if args.parent_stdio else "Ctrl-C to stop"
                details["text"] = format_dashboard_text(details["localUrl"], tuple(details["lanUrls"]), details["qrUrl"],
                                                        stop_instruction=stop_instruction)
                if not stopped.is_set():
                    print(json.dumps(details, ensure_ascii=False) if args.json else details["text"].rstrip("\n"), flush=True)
                    readiness_sent = True
            stopped.wait()
            if parent_errors:
                raise parent_errors[0]
            return exit_status
        finally:
            if session is not None:
                session.close()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        message = _terminal_text(exc)
        if args.json and not readiness_sent:
            print(json.dumps({"schemaVersion": "1.0", "status": "FAIL", "error": message}, ensure_ascii=False), flush=True)
        else:
            print("[error] " + message, file=sys.stderr)
        return 1
    finally:
        for signum, previous in previous_signals.items():
            signal.signal(signum, previous)


def main(argv: list[str] | None = None) -> int:
    """Keep existing engine commands and add dashboard entrypoints."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "dashboard-info":
        return _dashboard_info(arguments[1:])
    if arguments and arguments[0] == "dashboard-serve":
        return _dashboard_serve(arguments[1:])
    if arguments and arguments[0] in ("-h", "--help"):
        parser = studio().parser()
        commands = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
        commands.add_parser("dashboard-info", help="Print verified dashboard URLs and a terminal QR without starting a listener")
        commands.add_parser("dashboard-serve", help="Keep a verified dashboard available until stopped")
        parser.print_help()
        return 0
    return studio().main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())

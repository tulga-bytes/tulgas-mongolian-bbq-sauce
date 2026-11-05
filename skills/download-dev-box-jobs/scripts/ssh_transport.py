"""Rsync transport using the user's dev-box alias, without its startup line."""

import os
import re
import select
import subprocess
import sys


def _emit(data: bytes) -> None:
    remaining = memoryview(data)
    while remaining:
        try:
            remaining = remaining[os.write(1, remaining):]
        except BlockingIOError:
            # Rsync can make the inherited output pipe nonblocking.
            select.select([], [1], [])


def main(args: list[str]) -> int:
    if len(args) < 2 or args[0] != "dev-box":
        print("Use this transport with rsync and a dev-box: source.", file=sys.stderr)
        return 2

    process = subprocess.Popen(
        ["/bin/zsh", "-ic", 'dev-box "$@"', "dev-box", *args[1:]],
        stdout=subprocess.PIPE,
    )
    assert process.stdout is not None
    try:
        first = process.stdout.read(1)
        if first == b"A":
            first += process.stdout.readline(127)
        # Strip only the known shell startup line, never arbitrary banners.
        if not re.fullmatch(rb"Agent pid [0-9]+\r?\n", first):
            _emit(first)
        while chunk := process.stdout.read1(262144):
            _emit(chunk)
    except BrokenPipeError:
        process.terminate()
        process.wait()
        return 1
    finally:
        process.stdout.close()
    return process.wait()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

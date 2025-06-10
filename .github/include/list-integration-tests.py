#!/usr/bin/env python3

import itertools
import json
import os
import subprocess
import sys


def get_kernel_trailers_from_commits():
    """Get CI-Test-Kernel trailers from commits between current HEAD and base branch."""
    # In GitHub Actions, GITHUB_BASE_REF contains the target branch name for PRs
    # For push events, it's empty, so we need to determine the base differently
    base_ref = os.environ.get("GITHUB_BASE_REF")

    print(f"GITHUB_BASE_REF: {base_ref}", file=sys.stderr)

    if not base_ref:
        # Push event or other context without base ref
        print(
            "No GITHUB_BASE_REF found, using merge-base with origin/main",
            file=sys.stderr,
        )
        result = subprocess.run(
            ["git", "merge-base", "HEAD", "origin/main"],
            capture_output=True,
            text=True,
            check=True,
        )
        merge_base = result.stdout.strip()
        print(f"Merge base with origin/main: {merge_base}", file=sys.stderr)
    else:
        # PR or merge queue - use merge-base with the target branch
        print(f"Using merge-base with origin/{base_ref}", file=sys.stderr)
        result = subprocess.run(
            ["git", "merge-base", "HEAD", f"origin/{base_ref}"],
            capture_output=True,
            text=True,
            check=True,
        )
        merge_base = result.stdout.strip()
        print(f"Merge base with origin/{base_ref}: {merge_base}", file=sys.stderr)

    log_range = f"{merge_base}..HEAD"
    print(f"Searching for trailers in commit range: {log_range}", file=sys.stderr)

    result = subprocess.run(
        ["git", "log", "--format=%B%n---ENDOFCOMMIT---", log_range],
        capture_output=True,
        text=True,
        check=True,
    )

    if not result.stdout.strip():
        return set()

    kernels = set()

    commit_messages = result.stdout.split("---ENDOFCOMMIT---")
    print(
        f"Found {len([msg for msg in commit_messages if msg.strip()])} commits to search",
        file=sys.stderr,
    )

    for commit_message in commit_messages:
        commit_message = commit_message.strip()
        if not commit_message:
            continue

        lines = commit_message.split("\n")
        commit_subject = lines[0] if lines else "Unknown commit"

        # Start from the last line and work backwards, collecting trailers
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()

            if not line:
                continue

            if ":" not in line:
                break

            if line.startswith("CI-Test-Kernel:"):
                kernel = line.split(":", 1)[1].strip()
                kernels.add(kernel)
                print(
                    f"Found CI-Test-Kernel trailer '{kernel}' in commit: {commit_subject}",
                    file=sys.stderr,
                )

    print(f"Total kernels found from trailers: {kernels}", file=sys.stderr)
    return kernels


def main():
    if len(sys.argv) != 2:
        print("Usage: list-integration-tests.py <default-kernel>", file=sys.stderr)
        sys.exit(1)

    default_kernel = sys.argv[1]

    trailer_kernels = get_kernel_trailers_from_commits()

    kernels_to_test = {default_kernel}
    kernels_to_test.update(trailer_kernels)

    matrix = []

    for kernel in kernels_to_test:
        # use a blank kernel name for the default, as the common case is to have
        # no trailers and it makes the matrix names harder to read.
        kernel_name = "" if kernel == default_kernel else kernel

        for scheduler in [
            "scx_bpfland",
            "scx_chaos",
            "scx_lavd",
            "scx_rlfifo",
            "scx_rustland",
            "scx_rusty",
            "scx_tickless",
        ]:
            matrix.append({"name": scheduler, "flags": "", "kernel": kernel_name})

        # p2dq fails on 6.12, see https://github.com/sched-ext/scx/issues/2075 for more info
        if kernel != "stable/6_12":
            matrix.append({"name": "scx_p2dq", "flags": "", "kernel": kernel_name})

        for flags in itertools.product(
            ["--disable-topology=false", "--disable-topology=true"],
            ["", "--disable-antistall"],
        ):
            matrix.append(
                {"name": "scx_layered", "flags": " ".join(flags), "kernel": kernel_name}
            )

    print(f"matrix={json.dumps(matrix)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create or verify the remote SAR_ADC_T28 Virtuoso library."""

from __future__ import annotations

from virtuoso_bridge import VirtuosoClient


LIBRARY = "SAR_ADC_T28"
REMOTE_PATH = "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
TECHNOLOGY_LIBRARY = "tsmcN28"


def main() -> int:
    client = VirtuosoClient.from_env()

    if LIBRARY in client.library.list():
        info = client.library.get(LIBRARY)
        if info.path != REMOTE_PATH:
            raise RuntimeError(
                f"{LIBRARY} already exists at {info.path}, expected {REMOTE_PATH}"
            )
        if info.technology_library != TECHNOLOGY_LIBRARY:
            raise RuntimeError(
                f"{LIBRARY} is bound to {info.technology_library!r}, "
                f"expected {TECHNOLOGY_LIBRARY!r}"
            )
        print(f"verified existing library: {info.name}")
    else:
        info = client.library.create(
            LIBRARY,
            REMOTE_PATH,
            technology_library=TECHNOLOGY_LIBRARY,
        )
        print(f"created library: {info.name}")

    print(f"path: {info.path}")
    print(f"technology: {info.technology_library}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


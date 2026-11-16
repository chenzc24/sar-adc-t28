"""Derive a diagnostic stream by omitting one top-level fill reference.

No OA edit, layer filtering or flattening: every other GDS record is retained.
This stream is a causal experiment, not a density-qualified layout candidate.
"""
from __future__ import print_function
import os
import struct

FILL = {'metal': 'sar8_cdac_fill_metal', 'odpo': 'sar8_cdac_fill_odpo'}


def omit_fill(data, top, kind):
    if kind not in FILL:
        raise ValueError('Unknown fill group')
    chunks = []
    element = None
    structure = None
    target = None
    offset = 0
    found = {name: 0 for name in FILL.values()}
    removed = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError('Truncated GDS header')
        size, record, dtype = struct.unpack_from('>HBB', data, offset)
        if size < 4 or size % 2 or offset + size > len(data):
            raise ValueError('Invalid GDS record length')
        blob = data[offset:offset+size]
        offset += size
        if record == 6:  # STRNAME
            structure = blob[4:].rstrip(b'\0').decode('ascii')
        if structure == top and record == 10:  # SREF
            if element is not None:
                raise ValueError('Nested GDS element')
            element = []
            target = None
        if element is not None:
            element.append(blob)
            if record == 18:  # SNAME
                target = blob[4:].rstrip(b'\0').decode('ascii')
            if record == 17:  # ENDEL
                if target in found:
                    found[target] += 1
                if target == FILL[kind]:
                    removed += 1
                else:
                    chunks.extend(element)
                element = None
        else:
            chunks.append(blob)
        if record == 7:  # ENDSTR
            structure = None
        if record == 4:  # ENDLIB; preserve stream padding exactly
            chunks.append(data[offset:])
            offset = len(data)
    if element is not None or removed != 1 or any(n != 1 for n in found.values()):
        raise ValueError('Expected exactly one of each fixed top-level fill reference')
    return b''.join(chunks)


def derive(source, destination, top, kind):
    from run_physical import gds_identity, raw
    before = gds_identity(source)
    transformed = omit_fill(raw(source), top, kind)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(transformed)
    after = gds_identity(destination)
    expected = gds_identity(source, (FILL[kind],))
    if after['structural_sha256'] != expected['structural_sha256']:
        raise ValueError('Ablation changed more than the selected fill reference')
    before_functional = gds_identity(source, tuple(FILL.values()))
    after_functional = gds_identity(destination, tuple(FILL.values()))
    if before_functional['structural_sha256'][top] != after_functional['structural_sha256'][top]:
        raise ValueError('Functional geometry changed')
    if before['labels'][top] != after['labels'][top]:
        raise ValueError('Port labels changed')
    return dict(omitted_fill=kind, omitted_master=FILL[kind],
                source_gds_sha256=before['sha256'], derived_gds_sha256=after['sha256'],
                functional_top_sha256=after_functional['structural_sha256'][top],
                physical_signoff=False, oa_modified=False,
                scope='Stream-only fill ablation; DRC/LVS/PEX must be measured anew; not a layout candidate')

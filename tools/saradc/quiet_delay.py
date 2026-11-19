"""Derive the qualified QUIET-chain candidates from the nine-stage electrical reference."""

import re


REFERENCE = "xtor/clock/delays_std.scs"
QUIET = re.compile(rb"(?ms)^subckt sar8p_delay_quiet [^\n]*\n(.*?)^ends sar8p_delay_quiet\b")


def _quiet_source(reference, stages, final_delay_ps):
    if stages not in (5, 6, 9):
        raise ValueError("Expected a 5-, 6- or 9-stage QUIET chain")
    if final_delay_ps != 250 and (stages != 6 or final_delay_ps != 200):
        raise ValueError("The six-stage QUIET chain supports a final DEL200 or DEL250")
    (match,) = QUIET.finditer(reference)
    original = match[1]
    if re.findall(rb"(?m)^XD(\d+) ", original) != [str(i).encode() for i in range(1, 10)]:
        raise ValueError("The nine-stage QUIET reference has changed")
    if stages == 9:
        return REFERENCE, reference
    body = []
    for line in original.splitlines(keepends=True):
        device = re.match(rb"X(D|QUAL)(\d+) ", line)
        if not device or int(device[2]) > stages:
            continue
        if final_delay_ps != 250 and device[1] == b"D" and int(device[2]) == stages:
            if line.count(b"DEL250D1BWP12T30P140") != 1:
                raise ValueError("Unexpected final delay-cell master")
            line = line.replace(b"DEL250D1BWP12T30P140", b"DEL%dD1BWP12T30P140" % final_delay_ps)
        if device[1] == b"QUAL" and int(device[2]) == stages:
            line, n = re.subn(rb" Q\d+\) sar8p_and2", b" Y) sar8p_and2", line)
            if n != 1:
                raise ValueError("Bad last request qualifier")
        body.append(line)
    if stages % 2:
        end = b"\r\n" if original.endswith(b"\r\n") else b"\n"
        body.append(b"XQUAL%d (A D%d VDD VSS Y) sar8p_and2" % (stages, stages) + end)
    result = reference[:match.start(1)] + b"".join(body) + reference[match.end(1):]
    suffix = "" if final_delay_ps == 250 else "_del%d" % final_delay_ps
    return "xtor/clock/delays_std_q%d%s.scs" % (stages, suffix), result


def source_for_stages(reference, stages, final_delay_ps=250, *, sample_delay_ps=None):
    name, source = _quiet_source(reference, stages, final_delay_ps)
    if sample_delay_ps is None:
        return name, source
    if sample_delay_ps not in (75, 200):
        raise ValueError("Expected a single DEL075 or DEL200 for the qualified sample tap")
    sample, = re.finditer(rb"(?ms)^subckt sar8r_delay A VDD VSS Y\r?\n(.*?)^ends sar8r_delay\b", source)
    valid, = re.finditer(rb"(?ms)^subckt sar8p_delay_valid A VDD VSS Y\r?\n(.*?)^ends sar8p_delay_valid\b", source)
    if sample[1].count(b"DEL250D1") != 10 or sample[1].count(b"sar8p_and2") != 5:
        raise ValueError("The ten-cell sample reference changed")
    if valid[1].splitlines() != [b"XD1 (A D1 VDD VSS) DEL200D1BWP12T30P140",
                                b"XQUAL1 (A D1 VDD VSS Y) sar8p_and2"]:
        raise ValueError("The single-cell input qualifier changed")
    body = valid[1].replace(b"DEL200D1", b"DEL%03dD1" % sample_delay_ps)
    prefix = name.removesuffix(".scs") if stages != 9 else REFERENCE.removesuffix(".scs") + "_q9"
    return prefix + "_s%03d.scs" % sample_delay_ps, source[:sample.start(1)] + body + source[sample.end(1):]

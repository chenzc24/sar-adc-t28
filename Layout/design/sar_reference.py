"""Independent flat reference for the combined SAR, sequencer and timing macro."""

from Layout.design.sar_timing import CORE, PINS, SUFFIX, electrical

ARRAY_DECAPS = {
    "bits0_1": "DCAP8", "bits2_3": "DCAP8", "bits4_5": "DCAP8", "bits6_7": "DCAP8",
    "detect2": "DCAP16", "detect3": "DCAP4", "detect4": "DCAP4",
}


def source_cdl(*, array_decaps=False, standard_delays=False, static_latch=False, decaps=None, quiet_stages=None,
               quiet_final_ps=250, sample_delay_ps=None):
    parts, ports, hashes = electrical(standard_delays=standard_delays, static_latch=static_latch,
                                      quiet_stages=quiet_stages, quiet_final_ps=quiet_final_ps,
                                      sample_delay_ps=sample_delay_ps)
    lines = ["* " + name + " SHA256 " + val for name, val in sorted(hashes.items())]
    lines.append(".SUBCKT " + CORE + " " + " ".join(ports))
    for path, dev in parts.items():
        name = path.replace("/", "__")
        nets = " ".join(dev.pins[k] for k in PINS[dev.master].split())
        args = dev.parameters
        if dev.master.endswith(SUFFIX):
            lines.append(f"X{name} {nets} {dev.master}")
        elif dev.master == "cfmom_2t":
            geo = " ".join(k + "=" + args[k] for k in ("nr", "lr", "w", "s", "stm", "spm"))
            for n in range(int(args["multi"])):
                lines.append(f"X{name}_{n} {nets} {dev.master} {geo} multi=1")
        elif dev.master == "rupolym":
            lines.append(f"X{name} {nets} {dev.master} L={args['l']} W={args['w']} M=1")
        elif dev.master in {"nch_mac", "pch_mac"}:
            if args["nf"] != "1" or args["multi"] != "1":
                raise ValueError("Recheck width convention in " + name)
            lines.append(f"M{name} {nets} {dev.master} L={args['l']} W={args['w']} M=1")
        else:
            raise ValueError(dev.master)
    if decaps is None and array_decaps:
        decaps = ARRAY_DECAPS
    for name, master in (decaps or {}).items():
        lines.append(f"XDECAP_{name} VDD VSS {master}{SUFFIX}")
    return "\n".join(lines + [".ENDS " + CORE, ""])

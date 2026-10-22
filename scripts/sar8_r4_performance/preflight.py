"""Read-only source, simulator, remote resource and live OA verification."""
import contextlib
import dataclasses
import json
from common import OUT, SOURCE, blocks, dump, sha, verify_source


def main():
    from virtuoso_bridge import VirtuosoClient
    from virtuoso_bridge.spectre.runner import SpectreSimulator
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(source=verify_source(), remote_OA_mutations=False)
    with (OUT / "preflight.log").open("w", encoding="utf-8") as stream, contextlib.redirect_stdout(stream):
        sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT / "preflight", timeout=60)
        lic = sim.check_license()
        report["simulator"] = {k: lic.get(k) for k in ("ok", "spectre_path", "version")}
        c = VirtuosoClient.from_env(profile="t28_io", timeout=20, log_to_ciw=False)
        resource = c.ssh_runner.run_command("getconf _NPROCESSORS_ONLN; uptime; free -m; df -h /home/chenzc_intern25", timeout=30)
        report["resources"] = resource.stdout
        try:
            info = c.library.get("SAR_ADC_T28")
            assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
            assert info.technology_library == "tsmcN28"
            report["library"] = dataclasses.asdict(info)
            dump(OUT / "windows.json", c.list_windows())
            dest = OUT / "exports/live_r4"
            assert not dest.exists(), "Do not overwrite live export"
            receipt = c.schematic.export_netlist("SAR_ADC_T28", "tb_sar_adc8_join_r4", dest, simulator="spectre", timeout=300)
            dump(dest / "receipt.json", receipt)
            live = Path(receipt["input_file"])
            assert blocks(live.read_text()) == blocks((SOURCE / "dut.scs").read_text()), "Live R4 differs from frozen DUT"
            report["live_OA_DUT_matches"] = True
            report["live_export_sha256"] = sha(live)
        except AssertionError:
            raise
        except Exception as exc:
            report["live_OA_DUT_matches"] = None
            report["live_OA_error"] = str(exc)
    dump(OUT / "preflight.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    from pathlib import Path
    main()

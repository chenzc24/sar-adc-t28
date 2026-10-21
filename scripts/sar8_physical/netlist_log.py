"""Read only the candidate's native netlister diagnostics."""
from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False)
r = c.ssh_runner.run_command(
    "find /server_local_ssd/chenzc_intern25/simulation/tb_sar8p_unit/spectre/schematic "
    "-maxdepth 3 -type f -name '*.log' -exec tail -n 70 {} \\;", timeout=30)
print(r.stdout)
print(r.stderr)

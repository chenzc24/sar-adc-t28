"""Bounded read-only diagnostics for the owned device target (no stdlib shadow)."""
from common import OUT,LIB,dump
from virtuoso_bridge import VirtuosoClient

c=VirtuosoClient.from_env(profile="t28_io")
for cell in ("cdac8_controller","cdac8_device_sequence"):
    params=c.fetch(f'cdfGetCellCDF(ddGetObj("{LIB}" "{cell}"))~>parameters',["name","type","defValue","value"])
    dump(f"oa/{cell}_cdf_diagnostic.json",params)
    print(cell,params)
    for expression in (f'cdfGetBaseCellCDF(ddGetObj("{LIB}" "{cell}"))',
                       f'cdfGetBaseCellCDF(ddGetObj("{LIB}" "{cell}"))~>parameters~>name'):
        print(expression,c.execute_skill(expression),flush=True)
r=c.ssh_runner.run_command("tail -70 /home/chenzc_intern25/CDS.log",timeout=30)
dump("oa/ciw_diagnostic.txt",r.stdout)
print(r.stdout[-7000:])
c.screenshot(OUT/"oa/ciw_diagnostic.png",target="ciw")

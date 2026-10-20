"""Resolve native CDF API contracts before creating the owned VA cell CDF."""
from common import dump
from virtuoso_bridge import VirtuosoClient
c=VirtuosoClient.from_env(profile="t28_io")
for name in ("cdfCreateBaseCellCDF","cdfCreateParam","cdfSaveCDF","dbReplaceProp"):
    found=c.find_skill(name,mode="exact")
    dump(f"api/{name}_signature.json",found)
    print(name,found,flush=True)
    try:
        info=c.get_skill_more_info(name)
        dump(f"api/{name}_documentation.json",info)
        print(info.get("plain_text","")[:8000],flush=True)
    except FileExistsError as error:
        dump(f"api/{name}_documentation_unavailable.json",str(error))

"""Bounded two-process Spectre batch; stdout redirects stay process-local."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import subprocess
import sys
from oa import OUT, ROOT, dump


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="simple_v2")
    ap.add_argument("--cases", nargs="+", default=["pattern_0", "pattern_255", "pattern_85", "pattern_170", "fast", "slow", "ss", "ff", "recovery", "strongarm"])
    args = ap.parse_args()
    def run(case):
        print("START", case, flush=True)
        result = subprocess.run([sys.executable, "-u", "scripts/sar8_simple/simulate.py", case, "--tag", args.tag],
                                cwd=ROOT, capture_output=True, text=True)
        dump("batch/" + case + "_" + args.tag + ".json", dict(exit_code=result.returncode,
             stdout=result.stdout, stderr=result.stderr))
        print("FINISH", case, result.returncode, flush=True)
        return dict(case=case, exit_code=result.returncode)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(run, case) for case in args.cases]
        rows = [job.result() for job in as_completed(jobs)]
    dump("batch/summary_" + args.tag + ".json", rows)
    raise SystemExit(0 if all(row["exit_code"] == 0 for row in rows) else 1)


if __name__ == "__main__":
    main()

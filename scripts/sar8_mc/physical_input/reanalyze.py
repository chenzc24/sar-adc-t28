"""Source-bound reanalysis; original simulation and failed attempt are read-only."""
from __future__ import print_function
import argparse,sys
import reduce_source
def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--source-run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    sys.argv=[sys.argv[0],'--run-dir',a.source_run_dir,'--output-dir',a.output_dir]
    reduce_source.main()
if __name__=='__main__':main()

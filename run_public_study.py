#!/usr/bin/env python3
"""Run the frozen dependency-free public-source adapter study."""
from __future__ import annotations
import argparse,csv,json,os,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
resource.setrlimit(resource.RLIMIT_CPU,(105,110))
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
from semantic_contract.public_adapters import ADAPTERS,verify_adapter,mutation_study

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/public-study.json');ap.add_argument('--corpus',type=Path,default=ROOT/'data/public-corpus.csv');ap.add_argument('--budget',type=int,default=64);ap.add_argument('--seed',type=int,default=20260915);args=ap.parse_args()
 start=time.process_time();wall=time.perf_counter()
 corpus_path=args.corpus if args.corpus.is_absolute() else ROOT/args.corpus
 corpus=list(csv.DictReader(corpus_path.open()))
 adapter_results=[verify_adapter(a) for a in ADAPTERS]
 mutations=mutation_study(args.budget,args.seed)
 errors=[]
 if any(x['mismatch_count'] for x in adapter_results):errors.append('adapter mismatch')
 admitted=[x for x in corpus if x['decision']=='admitted']
 if sorted(x['adapter_id'] for x in admitted)!=sorted(ADAPTERS):errors.append('corpus/adapter mismatch')
 report={
  'study':'frozen public-source adapter coverage and synthetic negative controls',
  'repository':'bobbyyyan/scorch','corpus_count':len(corpus),
  'development_count':sum(x['split']=='development' for x in corpus),
  'held_out_count':sum(x['split']=='held-out' for x in corpus),
  'admitted_count':len(admitted),'abstained_count':sum(x['decision']=='abstained' for x in corpus),
  'coverage':len(admitted)/len(corpus),
  'development_admitted':sum(x['split']=='development' and x['decision']=='admitted' for x in corpus),
  'held_out_admitted':sum(x['split']=='held-out' and x['decision']=='admitted' for x in corpus),
  'corpus':corpus,'adapter_results':adapter_results,'mutation_study':mutations,
  'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,
  'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'errors':errors,
  'interpretation':('Admitted means the entire production diff was mapped to a declared source adapter and its '
   'adapter equivalence was checked on the retained bounded domain, backed by a separate prose universal proof. '
   'It is not an execution of upstream Scorch or an independent proof review. Abstentions remain in the denominator. '
   'Mutants are synthetic negative controls, not historical Scorch defects.')}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('corpus','adapter_results','mutation_study')},indent=2))
 return bool(errors)
if __name__=='__main__':raise SystemExit(main())

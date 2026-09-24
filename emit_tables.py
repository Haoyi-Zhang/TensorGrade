#!/usr/bin/env python3
"""Regenerate paper-side tables from retained raw scientific results."""
from pathlib import Path
import argparse,csv,json
from summarize import summarize,grade_name

def escape(text):
    out=str(text)
    for old,new in [('\\',r'\textbackslash{}'),('&',r'\&'),('_',r'\_'),('%',r'\%'),('#',r'\#')]:out=out.replace(old,new)
    return out

def outcome(grade):
    if grade['admission']!='admitted':return grade['admission']
    if not grade.get('complete_grade'):return 'partial'
    label=grade_name(grade)
    return r'$\varnothing$' if label=='empty' else '$'+label+'$'

def catalog(path,caption,label,entries):
    lines=[r'\begin{longtable}{@{}p{0.09\linewidth}p{0.54\linewidth}p{0.25\linewidth}@{}}',
      r'\caption{'+caption+r'}\label{'+label+r'}\\',
      r'\toprule Case & Retained case name & Outcome\\\midrule\endfirsthead',
      r'\toprule Case & Retained case name & Outcome\\\midrule\endhead',r'\bottomrule\endfoot']
    lines.extend(escape(tag)+' & '+escape(name)+' & '+answer+r'\\' for tag,name,answer in entries)
    lines.append(r'\end{longtable}');path.write_text('\n'.join(lines)+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=Path('results/current'))
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    s=summarize(args.directory);p=json.loads((args.directory/'pilot.json').read_text());d=json.loads((args.directory/'diagnostics.json').read_text());u=json.loads((args.directory/'public-study.json').read_text())
    corpus=list(csv.DictReader((Path(__file__).resolve().parent/'data/public-corpus.csv').open()))
    args.output.mkdir(parents=True,exist_ok=True)
    rows=[('Pilot finite-read program pairs',s['pilot_ir_cases']),('Pilot consumer descriptions',s['pilot_consumer_cases']),
      ('Additional frozen generated pairs',s['diagnostic_ir_cases']),('Coefficient-row pairs in exact enumeration',s['algebra_row_pairs']),
      ('Vector evaluations for those row pairs',s['algebra_vector_evaluations']),
      ('Main runner solver queries',s['pilot_query_count']+s['diagnostic_query_count']),
      ('Fixed-shape all-rational oracle checks',s['finite_shape_oracle_checks']),
      ('Internal fixed-shape oracle obligations',s['finite_shape_oracle_obligations']),
      ('Successful finite refutation replays',s['successful_refutation_replays']),
      ('Compact finite-read certificates',s['small_ir_certificates']),
      ('Public commits in fixed denominator',s['public_corpus_commits']),
      ('Public source adapters admitted',s['public_adapter_admissions']),
      ('Public adapter bounded cases',s['public_adapter_bounded_cases'])]
    v=[r'\begin{table}[t]',r'\caption{Retained validation units. Rows deliberately count different objects and must not be summed.}\label{tab:validation}',r'\centering',r'\begin{tabular}{lr}',r'\toprule',r'Unit & Count\\\midrule']
    v.extend(escape(a)+' & '+format(b,',')+r'\\' for a,b in rows)
    v.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}']);(args.output/'validation.tex').write_text('\n'.join(v)+'\n')
    g=[r'\begin{table}[t]',r'\caption{Greatest declared grades for the 22 admitted pilot pairs. The other six program-pair inputs are not assigned complete grades.}\label{tab:grades}',r'\centering',r'\begin{tabular}{lr}',r'\toprule Grade & Pilot pairs\\\midrule']
    for label in ['empty','S','SM','SZ','SZM','SZV','SZVM','SZVO','SZVOM']:
        g.append((r'$\varnothing$' if label=='empty' else '$'+label+'$')+' & '+str(s['realized_complete_grades'].get(label,0))+r'\\')
    g.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}']);(args.output/'grades.tex').write_text('\n'.join(g)+'\n')
    catalog(args.output/'pilot-catalog.tex','All 28 pilot finite-read inputs, including nonadmitted cases. Case names resolve directly to retained JSON files.','tab:pilot-catalog',[(f'P{k+1:02}',r['case']['id'],outcome(r['grade'])) for k,r in enumerate(p['records'])])
    catalog(args.output/'consumer-catalog.tex','All 16 consumer descriptions. Proved and refuted refer to the specified support-coherence condition.','tab:consumer-catalog',[(f'C{k+1:02}',r['case']['id'],escape(r['grade'].get('status',r['grade']['admission']))) for k,r in enumerate(p['consumer_records'])])
    catalog(args.output/'diagnostic-catalog.tex','All 64 frozen generated program pairs. Their common seed is 1729; the exact JSON inputs, rather than an external dataset, define these cases.','tab:diagnostic-catalog',[(f'G{k+1:02}',r['case']['id'],outcome(r['grade'])) for k,r in enumerate(d['records'])])

    pc=[r'\begin{longtable}{@{}p{0.055\linewidth}p{0.13\linewidth}p{0.13\linewidth}p{0.585\linewidth}@{}}',
        r"\caption{Frozen public-commit denominator. ``Held-out'' is a retrospective temporal split, not preregistration or blinded evaluation.}\label{tab:public-corpus}\\",
        r'\toprule ID & Split & Decision & Production-diff disposition\\\midrule\endfirsthead',
        r'\toprule ID & Split & Decision & Production-diff disposition\\\midrule\endhead',r'\bottomrule\endfoot']
    for row in corpus:
        pc.append(r"{} & {} & {} & {}\\".format(escape(row['id']),escape(row['split']),escape(row['decision']),escape(row['reason'])))
    pc.append(r'\end{longtable}');(args.output/'public-corpus.tex').write_text('\n'.join(pc)+'\n')

    summaries=u['mutation_study']['summary']
    mt=[r'\begin{table}[t]',r'\caption{Equal-budget synthetic negative-control detection. Mutants are not historical Scorch defects.}\label{tab:mutation}',r'\centering',r'\begin{tabular}{lrrr}',r'\toprule',r'Selection policy & Detected & Total & Rate\\\midrule']
    names=[('Developer examples','developer-examples'),('Seeded random','random'),('Stratified boundary','stratified-boundary')]
    for display,key in names:
        x=summaries[key];mt.append(f"{display} & {x['detected']} & {x['total']} & {100*x['detected']/x['total']:.0f}\\%"+r'\\')
    mt.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}']);(args.output/'mutation.tex').write_text('\n'.join(mt)+'\n')

    by_adapter={r['adapter']:r for r in u['adapter_results']}
    mut_rows=u['mutation_study']['rows']
    ad=[r'\begin{table}[t]',r'\caption{Bounded validation by admitted source adapter. Counts are retained model states, not upstream executions.}\label{tab:adapter-cases}',r'\centering',r'\begin{tabular}{lrrrr}',r'\toprule',r'Adapter & States & Mismatch & Dev. & Random / strat.\\\midrule']
    for key in ('P01','P04','P06','P08'):
        ar=by_adapter[key]; rows=[x for x in mut_rows if x['adapter']==key]
        det=lambda pol:sum(bool(x[pol]['detected']) for x in rows)
        label={'P01':'constructor','P04':'renderer','P06':'resolver','P08':'initialization'}[key]
        ad.append(f"{key} {label} & {ar['bounded_case_count']:,} & {ar['mismatch_count']} & {det('developer-examples')}/5 & {det('random')}/5, {det('stratified-boundary')}/5"+r"\\")
    ad.append(f"Total & {sum(x['bounded_case_count'] for x in u['adapter_results']):,} & {sum(x['mismatch_count'] for x in u['adapter_results'])} & {summaries['developer-examples']['detected']}/20 & {summaries['random']['detected']}/20, {summaries['stratified-boundary']['detected']}/20"+r"\\")
    ad.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}']);(args.output/'adapter-cases.tex').write_text('\n'.join(ad)+'\n')

    md=[r'\begin{longtable}{@{}p{0.09\linewidth}p{0.42\linewidth}rrr@{}}',r"\caption{First detection execution for all synthetic adapter mutants; an em dash denotes no detection within 64 executions.}\label{tab:mutation-detail}\\",r'\toprule Adapter & Mutant & Developer & Random & Stratified\\\midrule\endfirsthead',r'\toprule Adapter & Mutant & Developer & Random & Stratified\\\midrule\endhead',r'\bottomrule\endfoot']
    for x in mut_rows:
        def first(pol):
            v=x[pol]['first_detection_execution'];return str(v) if v is not None else r'\textemdash'
        md.append(f"{escape(x['adapter'])} & {escape(x['mutant'])} & {first('developer-examples')} & {first('random')} & {first('stratified-boundary')}"+r"\\")
    md.append(r'\end{longtable}');(args.output/'mutation-detail.tex').write_text('\n'.join(md)+'\n')
    print('Wrote nine data-derived TeX tables.')

if __name__=='__main__':main()

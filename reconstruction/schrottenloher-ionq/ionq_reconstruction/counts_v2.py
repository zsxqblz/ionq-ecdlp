"""Recount inclusive-carry replay and delayed LUTs, including 16-bit decoders."""
import json,random,pathlib
from .counts import run,metrics
from .point_add import IonQPointAdd
from .squaring import P
from qarton.circuit import UIntType,UInt,BoolType,QartonBool,AndFanoutResourceReporter
from qarton.data_structures.table_lookup_ip import IPTableLookup
from qarton.data_structures.select_swap_table_lookup import SelectSwapFwd
from qarton.elliptic_curve import EC,AffPointType
from math import log2,sqrt

def main():
    run();r=json.load(open('results/counts.json'));rng=random.Random(190201)
    r['lookup_scaling']=[]
    for w in (3,4,8,12,16):
        N=1<<w;tab=tuple(QartonBool(rng.randrange(2)) for _ in range(N));lam=max(2,1<<round(log2(sqrt(N/2))))
        fwd=IPTableLookup(tab,BoolType());phase=SelectSwapFwd(tab,BoolType(),l=lam)
        f=AndFanoutResourceReporter(fwd).ccx_count();c=AndFanoutResourceReporter(phase).ccx_count()+AndFanoutResourceReporter(phase.inverse()).ccx_count()
        assert f==N-2
        row={'address_bits':w,'entries':N,'lambda':lam,'forward_toffoli':f,'one_cleanup_toffoli':c,'separate_three_loads_and_cleanups':3*f+3*c,'merged_three_loads_one_cleanup':3*f+c}
        r['lookup_scaling'].append(row);print('LOOKUP',row,flush=True)
    random.seed(190202);ec=EC(P,0,7);G=AffPointType(ec).random_value();tab=tuple(G*i for i in range(7,15));mask=rng.randrange(1<<255,P)
    q=IonQPointAdd(tab,ec,mask,merged_lookup=True);r['merged_eight_entry_point']=metrics(q)
    arith=sum(r['new_per_addition_static_toffoli'].values());assert metrics(q)['static_toffoli']-arith==r['lookup_scaling'][0]['merged_three_loads_one_cleanup']
    L=r['lookup_scaling'][-1]
    r['explicit_lookup_total_expected']=28*(sum(r['new_per_addition_expected_toffoli'].values())+L['merged_three_loads_one_cleanup'])
    r['explicit_lookup_total_static']=28*(arith+L['merged_three_loads_one_cleanup'])
    r['baseline_with_separate_explicit_lookups']=28*(sum(r['baseline_per_addition'].values())+L['separate_three_loads_and_cleanups'])
    pathlib.Path('results/v2-counts.json').write_text(json.dumps(r,indent=2)+'\n')
    print('DONE',r['full_28_expected_toffoli'],r['explicit_lookup_total_expected'],metrics(q)['logical_qubits'],flush=True)
if __name__=='__main__':main()

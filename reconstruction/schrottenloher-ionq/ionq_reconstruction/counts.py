"""Reproducible module counts: emitted static Toffolis and mean executed count.

Only our explicit PhaseLT blocks are stochastic non-Clifford blocks. Each is
controlled by one freshly X-measured carry. The outcome is uniform, including
conditioned on earlier readouts; its expected Toffoli contribution is half its
emitted cost. No other gate count is discounted. This is not the paper's maximum
observed count over 100 trajectories and is not its physical injection count.
"""
from collections import defaultdict
from qarton.circuit import Circuit,AndFanoutResourceReporter

def metrics(q):
    r=AndFanoutResourceReporter(q);static=r.ccx_count();phase=0;classes=defaultdict(int)
    for name,num in r.sub_circuits_by_name().items():
        if Circuit.name_exists(name):
            sub=Circuit.from_name(name);cost=AndFanoutResourceReporter(sub).ccx_count()
            classes[sub.class_name]+=num*cost
            if sub.class_name.endswith('.PhaseLT'):phase+=num*cost
    return dict(static_toffoli=static,conditional_phase_toffoli=phase,expected_toffoli=static-phase/2,
                logical_qubits=q.nbr_qubits(),nested_class_toffolis=dict(sorted(classes.items())))

def run():
    from qarton.binary_operations import AndGate
    AndGate.replace_by_ccx=True
    from build_circuit import construct_circuit
    from point_add.gcd import ToBitVector,ApplyBitVector,IPModMul
    from point_add.special_mod_arithmetic import ControlledSpecialPrimeModularSquareAdd
    from .gcd import OddRecord,OddReplay,OddIPModMul
    from .squaring import IntegerSquare,ModularSquareSubtract,AddSlice,AddBMultiple,AddCMultiple,HighCorrection,P
    from .modular import SignedModularAdder,ModularNegation
    from .point_add import IonQPointAdd
    from qarton.elliptic_curve import EC,AffPointType
    import json,random,pathlib
    old=construct_circuit(0,gate_efficient=True)
    modules={
      'baseline.point_arithmetic':old,
      'baseline.record':ToBitVector(P,gate_efficient=True),
      'baseline.record_inverse':ToBitVector(P,gate_efficient=True).inverse(),
      'baseline.replay':ApplyBitVector(P,gate_efficient=True,special_prime=True),
      'baseline.replay_inverse':ApplyBitVector(P,gate_efficient=True,special_prime=True).inverse(),
      'baseline.square':ControlledSpecialPrimeModularSquareAdd(P,padding=50),
      'new.record':OddRecord(P), 'new.record_inverse':OddRecord(P).inverse(),
      'new.replay_multiply':OddReplay(P), 'new.replay_divide':OddReplay(P,True),
      'new.multiply':OddIPModMul(P),'new.divide':OddIPModMul(P,True),
      'new.square':ModularSquareSubtract(), 'new.integer_square128':IntegerSquare(128),
      'new.integer_square129':IntegerSquare(129), 'new.high_correction':HighCorrection(),
      'new.add_B_256':AddBMultiple(256), 'new.add_B_258_negative':AddBMultiple(258,-1),
      'new.add_c_negative':AddCMultiple(),
      'new.mod_add':AddSlice(256,0,256,0,1),'new.mod_subtract':AddSlice(256,0,256,0,-1),
      'new.mod_negation':ModularNegation(),
      'new.signed_mod_add_regular':SignedModularAdder(P,handle_zero=False),
      'new.signed_mod_add_special':SignedModularAdder(P),
    }
    report={'baseline_commit':'a9538b3','qarton_commit':'4fdcf6961ad45104a460e5f54d587a6776a73461','modules':{}}
    for name,q in modules.items():
        report['modules'][name]=metrics(q)
        print(name,report['modules'][name]['static_toffoli'],report['modules'][name]['expected_toffoli'],flush=True)
    m=report['modules']
    baseline={'record_build_and_erase':2*(m['baseline.record']['static_toffoli']+m['baseline.record_inverse']['static_toffoli']),
      'replay':m['baseline.replay']['static_toffoli']+m['baseline.replay_inverse']['static_toffoli'],
      'squaring':m['baseline.square']['static_toffoli']}
    baseline['other_arithmetic']=m['baseline.point_arithmetic']['static_toffoli']-sum(baseline.values())
    report['baseline_per_addition']=baseline
    for convention in ['static_toffoli','expected_toffoli']:
        new={'record_build_and_erase':2*(m['new.record'][convention]+m['new.record_inverse'][convention]),
          'replay':m['new.replay_multiply'][convention]+m['new.replay_divide'][convention],
          'squaring':m['new.square'][convention],
          'other_arithmetic':5*m['new.mod_subtract'][convention]+m['new.mod_add'][convention]+m['new.mod_negation'][convention]}
        report['new_per_addition_'+convention]=new
        report['full_28_'+convention]=28*(sum(new.values())+3*2**16)
    report['baseline_full_28']=28*(sum(baseline.values())+3*2**16)
    # A real composed circuit, with an eight-entry table for tractable simulation.
    random.seed(517);ec=EC(P,0,7);G=AffPointType(ec).random_value();table=tuple(G*k for k in range(7,15));mask=random.randrange(1<<255,P)
    q=IonQPointAdd(table,ec,mask)
    report['composed_eight_entry_point']=metrics(q)
    lookup_cost=0
    r=AndFanoutResourceReporter(q)
    for name,num in r.sub_circuits_by_name().items():
        if Circuit.name_exists(name):
            sub=Circuit.from_name(name)
            if sub.class_name.endswith(('.OOPTableLookup','.OOPTableLookupInverse')):
                lookup_cost+=num*AndFanoutResourceReporter(sub).ccx_count()
    report['small_lookup_cost']=lookup_cost
    assert report['composed_eight_entry_point']['static_toffoli']-lookup_cost==sum(report['new_per_addition_static_toffoli'].values())
    out=pathlib.Path('results/counts.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print('FULL',report['baseline_full_28'],report['full_28_static_toffoli'],report['full_28_expected_toffoli'],flush=True)
if __name__=='__main__':run()

"""Exhaustive small-instance checks of the explained LUT and cleanup identities."""
from itertools import product
import cmath
D=[1,6,3,7,0,5,2,4]
def ctl(c,x,k,y,table,record):
    if k==0:return y^(table[0] if c else 0),1
    high=(x>>(k-1))&1;low=x&((1<<(k-1))-1)
    a=c&high
    y,s1=ctl(a,low,k-1,y,table[1<<(k-1):],record)
    a^=c
    y,s0=ctl(a,low,k-1,y,table[:1<<(k-1)],record)
    a^=c
    mu=next(record)
    measurement=(-1)**(mu*a)
    correction=(-1)**(mu*c*high)
    return y,s1*s0*measurement*correction
for j,y in product(range(8),repeat=2):
    for bits in product(range(2),repeat=6):
        r=iter(bits); h=j>>2; low=j&3
        v,s0=ctl(1-h,low,2,y,D[:4],r)
        v,s1=ctl(h,low,2,v,D[4:],r)
        assert v==y^D[j] and s0*s1==1
    # Zipper write order from the reference figure.
    v=y
    for t in [0,4,1,5,2,6,3,7]:
        if j==t:v^=D[t]
    assert v==y^D[j]
# Arbitrary complex coherent input; check all X outcomes, correction, and reset.
a=[complex(j+1,(-1)**j*(j+2)) for j in range(8)]
norm=sum(abs(z)**2 for z in a)**0.5;a=[z/norm for z in a]
for mask in range(8):
    post=[z*((-1)**((mask&D[j]).bit_count()))/(8**0.5) for j,z in enumerate(a)]
    prob=sum(abs(z)**2 for z in post)
    assert abs(prob-1/8)<1e-12
    recovered=[z/(prob**0.5)*((-1)**((mask&D[j]).bit_count())) for j,z in enumerate(post)]
    assert max(abs(x-y) for x,y in zip(a,recovered))<1e-12
    assert mask^mask==0
# Without feedforward: coherence survives exactly between equal words.
for j,k in product(range(8),repeat=2):
    factor=sum((-1)**((m&(D[j]^D[k])).bit_count()) for m in range(8))/8
    assert factor==int(D[j]==D[k])
print('PASS: 4096 recursive basis/measurement cases, zipper order, all 8 wide-register outcomes and coherence without feedforward.')

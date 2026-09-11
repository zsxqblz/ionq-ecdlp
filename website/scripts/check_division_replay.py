"""Check the ordinary binary-gcd convention and modular replay used in the lesson."""
for p in [3,5,7,11,13,17,31]:
 for x in range(1,p):
  u,v=p,x;rec=[];states=[]
  while v:
   m=int(v%2==1 and v<u)
   if m:u,v=v,u
   a=v%2
   assert (v-a*u)%2==0
   v=(v-a*u)//2;rec.append((m,a));states.append((u,v))
  assert (u,v)==(1,0)
  for y in range(p):
   s,t=0,y;trace=[]
   for m,a in rec:
    if m:s,t=t,s
    t=(t-a*s)%p;t=(t+(t%2)*p)//2;trace.append((s,t))
   assert (s,t)==(y*pow(x,-1,p)%p,0)
   for m,a in reversed(rec):
    t=(2*t)%p;t=(t+a*s)%p
    if m:s,t=t,s
   assert (s,t)==(0,y)
   if (p,x,y)==(13,5,4):
    assert trace==[(4,11),(4,12),(4,6),(6,12),(6,6),(6,0)]
 for t in range(p):
  h=(t+(t%2)*p)//2
  assert (2*h)%p==t and int(h>=(p+1)//2)==t%2
print('PASS: division and inverse replay for all inputs over seven small prime fields; displayed trace and modular-halving cleanup.')

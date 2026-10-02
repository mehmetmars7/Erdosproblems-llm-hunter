#!/usr/bin/env python3
"""Finite checks supporting Ultra attempts 3104, 3106, 3115, 3116 and 3128.

Run from the repository root:
    python3 scripts/check_attempt_batch_graphs_2026_10_01.py

Python standard library only; no files are modified. These checks verify the
stated finite constructions and identities, not the full conjectures. The
universal restricted-case proofs are in the corresponding TeX attempts.
"""

from itertools import combinations,product,permutations
from collections import deque

# All 45 pairs in the explicit C7 squared code; cyclic differences include 6.
code = [(0, 0), (1, 2), (2, 0), (2, 4), (3, 2),
        (4, 4), (4, 6), (5, 1), (6, 3), (6, 5)]
assert len(set(code)) == 10
code_pairs = 0
for a, b in combinations(code, 2):
    assert any((x-y) % 7 not in (0, 1, 6) for x, y in zip(a, b))
    code_pairs += 1
print("C7 squared construction:", code_pairs, "codeword pairs checked")

# Switching identities and regular inverse, all 1024 labelled graphs on 5 vertices.
n=5; pairs=list(combinations(range(n),2)); graph_checks=regular_checks=0
for bits in range(1<<len(pairs)):
 E={p for j,p in enumerate(pairs) if bits>>j&1};m=len(E)
 deg=[sum(v in e for e in E) for v in range(n)]
 cards=[]
 for v in range(n):
  C=E.symmetric_difference({e for e in pairs if v in e});cards.append(C)
  assert len(C)==m+n-1-2*deg[v]
 assert sum(map(len,cards))==(n-4)*m+n*(n-1)
 assert sorted((m+n-1-len(C))//2 for C in cards)==sorted(deg)
 if len(set(deg))==1 and n not in (2*deg[0],2*deg[0]+2):
  d=deg[0]
  for C in cards:
   targets=[v for v in range(n) if sum(v in e for e in C)==n-1-d]
   assert len(targets)==1
   v=targets[0];assert C.symmetric_difference({e for e in pairs if v in e})==E
  regular_checks+=1
 if m>=4:
  W=sum(d*(d-1)//2 for d in deg)
  assert sum(sum(q*(q-1)//2 for q in [sum(v in x for x in E-{e}) for v in range(n)]) for e in E)==(m-2)*W
  if len(set(deg))==1:
   for e in E:
    C=E-{e}; deficit=[v for v in range(n) if sum(v in x for x in C)==deg[0]-1]
    assert len(deficit)==2 and tuple(sorted(deficit))==e
 graph_checks+=1
print('Graph identities:',graph_checks,'labelled order-five graphs;',regular_checks,'regular switching reconstructions')
# All labelled subcubic trees on 2..6 vertices, decoded from all Pruefer words.
trees=paths=0
for n in range(2,7):
 for word in product(range(n),repeat=n-2):
  degree=[1+word.count(v) for v in range(n)]
  if max(degree)>3:continue
  E=[]
  for v in word:
   leaf=next(i for i,d in enumerate(degree) if d==1)
   E.append((leaf,v));degree[leaf]-=1;degree[v]-=1
  rem=[i for i,d in enumerate(degree) if d==1];E.append(tuple(rem))
  adj=[[] for _ in range(n)]
  for u,v in E:adj[u].append(v);adj[v].append(u)
  root=next(v for v in range(n) if len(adj[v])==1)
  parent={root:None};depth={root:0};colour={};queue=deque([root])
  while queue:
   v=queue.popleft();children=sorted(u for u in adj[v] if u!=parent[v])
   for j,u in enumerate(children):
    parent[u]=v;depth[u]=depth[v]+1;colour[tuple(sorted((u,v)))]=2*(depth[u]%3)+j;queue.append(u)
  for v in range(n):assert len({colour[tuple(sorted((u,v)))] for u in adj[v]})==len(adj[v])
  def walk(P):
   global paths
   if len(P)==5:
    C=[colour[tuple(sorted(e))] for e in zip(P,P[1:])];assert len(set(C))>=3;paths+=1;return
   for u in adj[P[-1]]:
    if u not in P:walk(P+[u])
  for v in range(n):walk([v])
  trees+=1
print('Forest construction:',trees,'labelled subcubic trees;',paths,'oriented four-edge paths checked')
# Full additive colouring checks on the eight labels with three ternary digits.
A=[sum(e*3**j for j,e in enumerate(bits)) for bits in product((0,1),repeat=3)]
p4=c4=0
for P in permutations(A,5):
 assert len({P[j]+P[j+1] for j in range(4)})>=3;p4+=1
for P in permutations(A,4):
 assert len({P[j]+P[(j+1)%4] for j in range(4)})>=3;c4+=1
print('Additive construction:',p4,'oriented four-edge paths and',c4,'oriented four-cycles checked on K8')

import pandas as pd
from structure import load_operations, GRASPConstructor
rru = load_operations('data/Case 1.xlsx', 'RRU')
hql = load_operations('data/Case 1.xlsx', 'HQL')
itp = load_operations('data/Case 1.xlsx', 'ITP')
iss = load_operations('data/Case 1.xlsx', 'ISS')
tlu = load_operations('data/Case 1.xlsx', 'TLU')
operations = rru + hql + itp + iss + tlu

scheduled_ops = set()
def get_id(op): return (op.machine, op.task_id, op.op_id)

while True:
    eligible = []
    for op in operations:
        if get_id(op) not in scheduled_ops:
            if not op.predecessors_str:
                eligible.append(op)
            else:
                ok = True
                for p in op.predecessors_str:
                    # check if the predecessor is scheduled ANYWHERE on ANY machine.
                    if not any(s[2] == p and s[0] == op.machine for s in scheduled_ops):
                        ok = False
                        break
                if ok:
                    eligible.append(op)
    if not eligible:
        break
    for e in eligible:
        scheduled_ops.add(get_id(e))

print("Leftover:", len(operations) - len(scheduled_ops))
for op in operations:
    if get_id(op) not in scheduled_ops:
        print("Leftover op:", op.machine, op.task_id, op.op_id, op.predecessors_str)

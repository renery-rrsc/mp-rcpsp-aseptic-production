import re
with open("structure.py", "r") as f:
    text = f.read()

new_ssgs = """    def _check_predecessors_finished(self, op, current_time):
        \"\"\"
        Verify if all predecessors of a given operation are already finished.
        \"\"\"
        for pred_id in op.predecessors_str:
            pred_op = None
            for o in self.operations:
                if o.op_id == pred_id and o.machine == op.machine:
                    pred_op = o
                    break

            if pred_op is None:
                continue

            if pred_op.end_time is None or pred_op.end_time > current_time:
                return False
        return True"""

old_ssgs_re = r"    def _check_predecessors_finished\(self, op, current_time\):.*?return True"
text = re.sub(old_ssgs_re, new_ssgs, text, flags=re.DOTALL)

with open("structure.py", "w") as f:
    f.write(text)

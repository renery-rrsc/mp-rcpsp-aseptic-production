with open("structure.py", "r") as f:
    text = f.read()

new_grasp = """        def get_id(op):
            return (op.machine, op.task_id, op.op_id)

        total_ops = len(self.operations)

        while len(priority_list) < total_ops:
            # To find eligible operations, i.e. when all predecessors are already in the priority list
            eligible_ops = []

            for op in self.operations:
                # verify if predecessors IDs are already on the scheduled set
                if get_id(op) not in scheduled_ops:
                    if not op.predecessors_str:
                        predecessors_met = True
                    else:
                        predecessors_met = all(
                            any(
                                sched_mach == op.machine and sched_pred == pred_id
                                for (sched_mach, sched_task, sched_pred) in scheduled_ops
                            )
                            for pred_id in op.predecessors_str
                        )
                    if predecessors_met:
                        eligible_ops.append(op)"""

import re
old_grasp_re = r"        def get_id\(op\):.*?eligible_ops\.append\(op\)"
text = re.sub(old_grasp_re, new_grasp, text, flags=re.DOTALL)

with open("structure.py", "w") as f:
    f.write(text)

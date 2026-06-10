import pandas as pd
import numpy as np
import math
import random

# ====================================
# MODULE 1: DEFINING MODEL PARAMETERS
# ====================================

# nt: number of available technicians per specialty
TECHNICIANS_AVAILABLE = {
    'Mechanical': 8,
    'Electrical': 4,
    'Calibration': 2,
    'Lubrication': 1
}

# Mc: machine spatial capacity (number of technicians that can work on a machine simultaneously)
MACHINE_SPATIAL_CAPACITY = {
    'RRU': 3,
    'HQL': 2,
    'ITP': 6,
    'ISS': 1,
    'TLU': 2,
}

class Operation:
    def __init__(self, machine, task_id, op_id, duration_hrs, skill, n_workers, predecessors_str):
        self.machine = machine
        self.task_id = int(task_id)
        self.op_id = int(op_id)

        # Converting hours to minutes to avoid floating point issues
        self.duration = int(math.ceil(duration_hrs * 60))

        self.skill = skill
        self.n_workers = int(n_workers)

        # Converting predecessors string into a list of integers
        self.predecessors_str = self._parse_predecessors(predecessors_str)

        # Decision variables (Sm_ij and Em_ij)
        self.start_time = None
        self.end_time = None

    def _parse_predecessors(self, pred_str):
        pred_str = str(pred_str)
        if pd.isna(pred_str) or pred_str.strip() == '':
            return []
        pred_str = str(pred_str).replace(',', ';')
        
        return [int(x.strip()) for x in pred_str.split(';') if x.strip().isdigit()]
        
    def __repr__(self):
        return f"Operation(machine={self.machine}, task_id={self.task_id} - op_id={self.op_id} | duration={self.duration}, predecessors={self.predecessors_str})"
    
# =====================================
# MODULE 2: LOADING AND PREPARING DATA
# =====================================

def load_operations(file_path, sheet):
    """
    Loads operations data from an Excel file and returns a list of Operation instances.
    """
    df = pd.read_excel(file_path, sheet_name=sheet)

    operations = []
    for _, row in df.iterrows():
        if pd.isna(row['Task ID']) or pd.isna(row['Operation ID']):
            continue
        
        machine = sheet
        op = Operation(
            machine=machine,
            task_id=row['Task ID'],
            op_id=row['Operation ID'],
            duration_hrs=row['Task Duration'],
            skill=row['Skills Required'],
            n_workers=row['Num. Of Workers'],
            predecessors_str=row.get('Preceding Op', '') # Usa get para evitar erro se a coluna estiver vazia
        )
        operations.append(op)

    return operations

# =========================================================
# MODULE 3: IMPLEMENTING SERIAL SCHEDULE GENERATION SCHEME
# =========================================================

class SSGS:
    def __init__(self, operations, technicians_dict, machine_capacity_dict):
        """
        Initialize schedule generator with operations list and resource constraints.
        """
        self.operations = operations
        self.tech_limits = technicians_dict.copy()
        self.machine_limits = machine_capacity_dict.copy()

        # Storing allocation times to evaluate PLV
        self.tech_usage = {skill: 0 for skill in self.tech_limits.keys()}

        # Auxiliar dictionary to search operation by the tuple (task_id, op_id)
        self.op_dict = {(op.task_id, op.op_id): op for op in operations}

    def _check_predecessors_finished(self, op, current_time):
        """
        Verify if all predecessors of a given operation are already finished.
        """
        for pred_id in op.predecessors_str:
            pred_op = self.op_dict.get((op.task_id, pred_id))

            if pred_op is None:
                continue

            if pred_op.end_time is None or pred_op.end_time > current_time:
                return False
        return True
    
    def _get_active_operations(self, current_time):
        """
        Returns all operations being executed at current time.
        """
        return [op for op in self.operations if op.start_time is not None and op.start_time <= current_time < op.end_time]
    
    def _check_resources_availability(self, op, current_time):
        """
        Verify whether there are available technicians and free space on the machine at current time.
        """
        active_ops = self._get_active_operations(current_time)

        # Count ocuppied technicians
        tech_in_use = {skill: 0 for skill in self.tech_limits.keys()}
        for a_op in active_ops:
            if a_op.skill in tech_in_use:
                tech_in_use[a_op.skill] += a_op.n_workers

        # Check available technicians for a new operation
        if tech_in_use.get(op.skill, 0) + op.n_workers > self.tech_limits.get(op.skill, 0):
            return False
        
        # Count machine free spaces
        machine_in_use = sum(a_op.n_workers for a_op in active_ops if a_op.machine == op.machine)
        if machine_in_use + op.n_workers > self.machine_limits.get(op.machine, 999):
            return False
        
        return True
    
    def build_schedule(self, priority_list):
        """
        Generate the schedule based on priorities 
        priority_list: 'Operation' object list ordered by GRASP or ITLBO
        """

        # Reset times if runned multiple times
        for op in self.operations:
            op.start_time = None
            op.end_time = None
        
        self.tech_usage = {skill: 0 for skill in self.tech_limits.keys()}

        # Pending operations ordered by priority
        pending_ops = list(priority_list)

        current_time = 0

        while pending_ops:
            # To find when machines/technicians leaves free spaces
            # If current_time = 0 then try to start, otherwise it moves a step forward in time
            ops_started_this_tick = False

            for op in list(pending_ops):
                # Check precedence
                if not self._check_predecessors_finished(op, current_time):
                    continue
                
                # Check space and resource availability
                if self._check_resources_availability(op, current_time):
                    # Start operation
                    op.start_time = current_time
                    op.end_time = current_time + op.duration

                    # Register ocupation
                    self.tech_usage[op.skill] += (op.n_workers * op.duration)

                    pending_ops.remove(op)
                    ops_started_this_tick = True

            # If no one were able to start an operation in the current time, we advance to the time when the next operation ends
            if not ops_started_this_tick:
                # Search in current operations to find the earliest end time
                future_end_times = [op.end_time for op in self.operations if op.end_time is not None and op.end_time > current_time]

                if future_end_times:
                    current_time = min(future_end_times)
                else:
                    print("DEADLOCK ALERT! Check whether a task requires more resources than machine spatial capacity.")
                    break

        return self._calculate_objectives()
    
    def _calculate_objectives(self):
        """
        Evaluates Makespan and PLV of the generated schedule.
        """
        # Makespan
        makespan = max(op.end_time for op in self.operations if op.end_time is not None)

        # PLV
        total_workers = sum(self.tech_limits.values())
        if total_workers > 0:
            avg_workload = sum(self.tech_usage.values()) / total_workers

            variance_sum = 0
            for skill, total_time in self.tech_usage.items():
                num_techs = self.tech_limits.get(skill, 1)
                time_per_tech = total_time / num_techs if num_techs > 0 else 0
                variance_sum += num_techs * ((time_per_tech - avg_workload) **2)

            plv = variance_sum / total_workers
        else:
            plv = 0

        return makespan, plv
    
# =====================================================================
# MODULE 4: IMPLEMENTING GREEDY-RANDOMIZED ADAPTATIVE SEARCH PROCEDURE
# =====================================================================

class GRASPConstructor:
    def __init__(self, operations, alpha=0.3):
        """
        Initialize GRASP metaheuristic.
        alpha: randomness factor (0 = pure greed | 1 = pure randomized)
        """
        self.operations = operations
        self.alpha = alpha

    def generate_priority_list(self):
        """
        Generates a feasible and topologically ordered priority list.
        """
        priority_list = []
        scheduled_ops = set()

        def get_id(op):
            return (op.task_id, op.op_id)
        
        total_ops = len(self.operations)

        while len(priority_list) < total_ops:
            # To find eligible operations, i.e. when all predecessors are already in the priority list
            eligible_ops = []

            for op in self.operations:
                # verify if predecessors IDs are already on the scheduled set
                if get_id(op) not in scheduled_ops:
                    predecessors_met = all(
                        (op.task_id, pred_id) in scheduled_ops
                        for pred_id in op.predecessors_str
                    )
                if predecessors_met:
                    eligible_ops.append(op)
            
            if not eligible_ops:
                print("ERROR: deadlock on predecessors net. Please review the data.")

            # GREEDY EVALUATION (Heuristic: LPT - longest processing time)
            max_duration = max(op.duration for op in eligible_ops)
            min_duration = min(op.duration for op in eligible_ops)

            # RESTRICED CANDIDATE LIST (RCL) CONSTRUCTION
            threshold = max_duration - self.alpha * (max_duration - min_duration)
            rcl = [op for op in eligible_ops if op.duration >= threshold]

            # RANDOMIZED SELECTION FROM RCL
            chosen_op = random.choice(rcl)
            priority_list.append(chosen_op)
            scheduled_ops.add(get_id(chosen_op))

        return priority_list

# ===============================================
# MODULE 4: IMPLEMENTING LOCAL SEARCH WITH GRASP
# ===============================================

class GRASPLocalSearch:
    def __init__(self, ssgs_engine):
        self.ssgs = ssgs_engine

    def _is_valid_swap(self, op1, op2):
        """
        Verify whether is secure to change the operations order considering precedence order.
        """
        if op1.task_id == op2.task_id and op1.op_id in op2.predecessors_str:
            return False
        return True
    
    def optimize(self, initial_priority_list, current_makespan, current_plv):
        """
        Apply local search while iteractively refining the schedule
        """
        improved = True
        best_list = list(initial_priority_list)
        best_cmax = current_makespan
        best_plv = current_plv

        while improved:
            improved = False

            for i in range(len(best_list) - 1):
                op_atual = best_list[i]
                op_proxima = best_list[i+1]

                if self._is_valid_swap(op_atual, op_proxima):
                    # Create neighbour scenario (to change order of the operations pair)
                    neighbour_list = list(best_list)
                    neighbour_list[i], neighbour_list[i+1] = neighbour_list[i+1], neighbour_list[i]

                    # Evaluate new scenario with SSGS
                    makespan, plv = self.ssgs.build_schedule(neighbour_list)

                    # Acceptance criteria: (is Cmax smaller?) OR (is PLV samller?)
                    if makespan < best_cmax or (makespan == best_cmax and plv < best_plv):
                        best_cmax = makespan
                        best_plv = plv
                        best_list = neighbour_list
                        improved = True
                        break
        
        return best_list, best_cmax, best_plv
    
# ============================
# MODULE 6: EXECUTION PIPELIN
# ============================

if __name__ == '__main__':
    print(">>> INITIALIZING MAINTENANCE SCHEDULE OPTIMIZER WITH HI-ITLBO-GRASP-SSGS <<<")

    try:
        rru = load_operations('data/Case 1.xlsx', 'RRU')
        hql = load_operations('data/Case 1.xlsx', 'HQL')
        itp = load_operations('data/Case 1.xlsx', 'ITP')
        iss = load_operations('data/Case 1.xlsx', 'ISS')
        tlu = load_operations('data/Case 1.xlsx', 'TLU')
        operations = rru + hql + itp + iss + tlu

        print(f"[{len(operations)}] operations loaded successfull!")
    
    except Exception as e:
        print(f"Error: {e}")
        exit()

    # Configuring algorithm engines
    ssgs_engine = SSGS(operations, TECHNICIANS_AVAILABLE, MACHINE_SPATIAL_CAPACITY)
    grasp_constructor = GRASPConstructor(operations, alpha = 0.3)
    grasp_local_search = GRASPLocalSearch(ssgs_engine)

    # Storing variables for global optimal of all iterations
    global_best_makespan = float('inf')
    global_best_plv = float('inf')
    global_best_schedule = []

    # GRASP hyperparameter: how many initial solutions will we explore?
    GRASP_ITERATIONS = 50

    print("\nInitializing GRASP metaheuristic...")
    for iteration in range(GRASP_ITERATIONS):
        # STEP 1: CONSTRUCTION
        initial_list = grasp_constructor.generate_priority_list()
        initial_makespan, initial_plv = ssgs_engine.build_schedule(initial_list)

        # STEP 2: LOCAL SEARCH
        best_list, best_makespan, best_plv = grasp_local_search.optimize(initial_list, initial_makespan, initial_plv)

        # STEP 3: EVALUATION
        if best_makespan < global_best_makespan or (best_makespan == global_best_makespan and best_plv < global_best_plv):
            global_best_makespan = best_makespan
            global_best_plv = best_plv
            global_best_schedule = best_list
            print(f"Iteration {iteration+1:02d} | NEW GLOBAL OPTIMAL >>> Makespan: {global_best_makespan:.0f} | PLV: {global_best_plv:.2f}")

    print("\n=======================================================")
    print("                RESULTADO DA OTIMIZAÇÃO                ")
    print("=======================================================")
    print(f"Total downtime (Makespan): {global_best_makespan:.0f} minutes ({global_best_makespan/60:.2f} horas)")
    print(f"Personel Loading Variance (PLV): {global_best_plv:.2f}")
    print("=======================================================\n")
    
    # print chronological order of tasks
    print("Ordem Lógica das Tarefas no Cronograma Ótimo:")
    for op in global_best_schedule:
        print(f"-> Máquina: {op.machine} | Task: {op.task_id} | Op: {op.op_id} | Especialidade: {op.skill} ({op.n_workers} pax)")
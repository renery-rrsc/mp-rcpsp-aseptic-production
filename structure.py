import pandas as pd
import numpy as np
import math
import random
import time
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ====================================
# MODULE 1: DEFINING MODEL PARAMETERS
# ====================================

# nt: number of available technicians per specialty
TECHNICIANS_AVAILABLE = {
    'Mechanical': 8,
    'Electrical': 4,
    'Calibration': 2,
    'Lubrication': 1,
    'Automation': 2
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

class Technician:
    def __init__(self, tech_id, skills):
        self.tech_id = tech_id
        self.skills = skills # Ex: ['Mechanical', 'Electrical']
        self.worked_hours = 0.0
        self.available_from = 0.0

def create_technicians_list(technicians_available):
    """
    Creates a list of Technician objects based on the availability dictionary.
    """
    techs = []
    tech_id_counter = 1
    for skill, count in technicians_available.items():
        for _ in range(count):
            techs.append(Technician(f"T{tech_id_counter}", [skill]))
            tech_id_counter += 1
    return techs

# =====================================
# MODULE 2: LOADING AND PREPARING DATA
# =====================================

def load_all_operations(file_path, sheets=None):
    """
    Loads operations data from an Excel file for multiple sheets at once and returns a list of Operation instances.
    """
    all_sheets_df = pd.read_excel(file_path, sheet_name=None)
    if sheets is None:
        sheets = list(all_sheets_df.keys())

    operations = []
    for sheet in sheets:
        if sheet not in all_sheets_df:
            continue
        df = all_sheets_df[sheet]

        col_idx = {col: i for i, col in enumerate(df.columns)}
        task_id_idx = col_idx.get('Task ID')
        op_id_idx = col_idx.get('Operation ID')
        duration_idx = col_idx.get('Task Duration')
        skill_idx = col_idx.get('Skills Required')
        workers_idx = col_idx.get('Num. Of Workers')
        pred_idx = col_idx.get('Preceding Op')

        for row in df.itertuples(index=False, name=None):
            if pd.isna(row[task_id_idx]) or pd.isna(row[op_id_idx]):
                continue

            machine = sheet
            op = Operation(
                machine=machine,
                task_id=row[task_id_idx],
                op_id=row[op_id_idx],
                duration_hrs=row[duration_idx],
                skill=row[skill_idx],
                n_workers=row[workers_idx],
                predecessors_str=row[pred_idx] if pred_idx is not None else '' # Usa if para evitar erro se a coluna estiver vazia
            )
            operations.append(op)

    return operations

# =========================================================
# MODULE 3: IMPLEMENTING SERIAL SCHEDULE GENERATION SCHEME
# =========================================================

class SSGS:
    def __init__(self, operations, technicians_list, machine_capacity_dict):
        self.operations = operations
        self.technicians = technicians_list
        self.machine_limits = machine_capacity_dict.copy()
        # Pre-compute an O(1) lookup dictionary for operations
        self.op_lookup = {(op.machine, op.task_id, op.op_id): op for op in self.operations}

        # Pre-compute a dictionary mapping each skill to a list of capable technicians
        self.skill_to_techs = {}
        for tech in self.technicians:
            for skill in tech.skills:
                if skill not in self.skill_to_techs:
                    self.skill_to_techs[skill] = []
                self.skill_to_techs[skill].append(tech)

        # Pre-compute successors and predecessor counts for O(1) schedulable updates
        self.successors = { (op.machine, op.task_id, op.op_id): [] for op in self.operations }
        self.base_unscheduled_preds = { (op.machine, op.task_id, op.op_id): len(op.predecessors_str) for op in self.operations }
        self.initial_schedulable_ops = [op for op in self.operations if not op.predecessors_str]

        for op in self.operations:
            for pred_id in op.predecessors_str:
                pred_key = (op.machine, op.task_id, pred_id)
                if pred_key in self.successors:
                    self.successors[pred_key].append(op)

    def decode(self, priority_vector):
        """
        Generates the schedule by decoding the priority vector.
        Priority vector should be a list of dicts or objects having a 'priority' value,
        or just an ordered list of operations based on continuous priority values.
        Actually, we can pass a dictionary mapping operation objects to their priority.
        """
        # Reset operations
        for op in self.operations:
            op.start_time = None
            op.end_time = None
            op.allocated_technicians = [] # Keep track for debugging/output

        # Reset technicians
        for tech in self.technicians:
            tech.worked_hours = 0.0
            tech.available_from = 0.0

        D_g = set(self.initial_schedulable_ops)
        unscheduled_preds = self.base_unscheduled_preds.copy()

        schedule = []
        self.scheduled_operations = []

        while D_g:
            best_op = self._select_best_operation(D_g, priority_vector)

            start_time = self._find_earliest_start_time(best_op)

            allocated_techs = self._allocate_technicians(best_op, start_time)

            if len(allocated_techs) < best_op.n_workers:
                start_time = self._find_earliest_start_time_with_resources(best_op, start_time)
                allocated_techs = self._allocate_technicians(best_op, start_time)

            finish_time = start_time + best_op.duration

            best_op.start_time = start_time
            best_op.end_time = finish_time
            best_op.allocated_technicians = [t.tech_id for t in allocated_techs]

            schedule.append({
                'operation': best_op,
                'start': start_time,
                'finish': finish_time,
                'technicians': best_op.allocated_technicians
            })
            self.scheduled_operations.append(best_op)

            for tech in allocated_techs:
                tech.available_from = finish_time
                tech.worked_hours += best_op.duration

            op_key = (best_op.machine, best_op.task_id, best_op.op_id)
            D_g.remove(best_op)

            for succ_op in self.successors.get(op_key, []):
                succ_key = (succ_op.machine, succ_op.task_id, succ_op.op_id)
                unscheduled_preds[succ_key] -= 1
                if unscheduled_preds[succ_key] == 0:
                    D_g.add(succ_op)

        makespan = max([op['finish'] for op in schedule]) if schedule else 0
        plv = self._calculate_plv()

        return makespan, plv, schedule

    def _select_best_operation(self, D_g, priority_vector):
        # We assume priority_vector is a dict {op: priority_value}
        # The smaller the value (or higher depending on definition), the better. Let's say higher is better priority.
        # However, RK usually has lower values = higher priority if sorting ascending. We will assume ascending sort (lower is better).
        best_op = min(D_g, key=lambda op: priority_vector.get(op, float('inf')))
        return best_op

    def _find_earliest_start_time(self, op):
        # 1. Start after all predecessors are finished
        max_pred_end = 0
        for pred_id in op.predecessors_str:
            pred_op = self.op_lookup.get((op.machine, op.task_id, pred_id))
            if pred_op and pred_op.end_time is not None:
                max_pred_end = max(max_pred_end, pred_op.end_time)

        return max_pred_end

    def _find_earliest_start_time_with_resources(self, op, current_time):
        machine_ops = [o for o in self.scheduled_operations if o.machine == op.machine]
        skilled_techs = self.skill_to_techs.get(op.skill, [])
        machine_limit = self.machine_limits.get(op.machine, 999)

        while True:
            # Check machine capacity
            machine_in_use = sum(o.n_workers for o in machine_ops if o.start_time <= current_time < o.end_time)

            if machine_in_use + op.n_workers <= machine_limit:
                # Check technicians availability
                eligible_techs = [t for t in skilled_techs if t.available_from <= current_time]
                if len(eligible_techs) >= op.n_workers:
                    return current_time

            future_times = [o.end_time for o in machine_ops if o.end_time > current_time] + \
                           [t.available_from for t in skilled_techs if t.available_from > current_time]

            if not future_times:
                return current_time + 1

            next_time = min(future_times)
            if next_time == current_time:
                current_time += 1
            else:
                current_time = next_time


    def _allocate_technicians(self, operation, start_time):
        eligible_techs = [
            t for t in self.technicians
            if operation.skill in t.skills and t.available_from <= start_time
        ]

        # 1st criteria: len(t.skills) -> Ascending (Specialist rule)
        # 2nd criteria: t.worked_hours -> Ascending (Load balancing rule)
        eligible_techs.sort(key=lambda t: (len(t.skills), t.worked_hours))

        return eligible_techs[:operation.n_workers]

    def _calculate_plv(self):
        if not self.technicians:
            return 0
        mean_hours = sum(t.worked_hours for t in self.technicians) / len(self.technicians)
        variance = sum((t.worked_hours - mean_hours)**2 for t in self.technicians) / len(self.technicians)
        return variance

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

    def generate_priority_vector(self):
        """
        Generates a continuous priority vector instead of an ordered list.
        It uses the topological construction logic but assigns continuous values [0, 1]
        where lower values denote higher priority, maintaining topological order.
        """
        priority_list = []
        scheduled_ops = set()

        def get_id(op):
            return (op.machine, op.task_id, op.op_id)

        total_ops = len(self.operations)

        while len(priority_list) < total_ops:
            eligible_ops = []

            for op in self.operations:
                if get_id(op) not in scheduled_ops:
                    predecessors_met = all(
                        (op.machine, op.task_id, pred_id) in scheduled_ops
                        for pred_id in op.predecessors_str
                    )
                    if predecessors_met:
                        eligible_ops.append(op)

            if not eligible_ops:
                print("ERROR: deadlock on predecessors net. Please review the data.")

            # GREEDY EVALUATION (Heuristic: LPT - longest processing time)
            max_duration = max(op.duration for op in eligible_ops)
            min_duration = min(op.duration for op in eligible_ops)

            # RESTRICTED CANDIDATE LIST (RCL) CONSTRUCTION
            threshold = max_duration - self.alpha * (max_duration - min_duration)
            rcl = [op for op in eligible_ops if op.duration >= threshold]

            # RANDOMIZED SELECTION FROM RCL
            chosen_op = random.choice(rcl)
            priority_list.append(chosen_op)
            scheduled_ops.add(get_id(chosen_op))

        # Convert the ordered list into a continuous priority vector
        # by assigning equally spaced values from 0 to 1 based on their order.
        priority_vector = {}
        n = len(priority_list)
        for idx, op in enumerate(priority_list):
            priority_vector[op] = idx / max(1, n - 1)

        return priority_vector

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
        if op1.machine == op2.machine and op1.task_id == op2.task_id and op1.op_id in op2.predecessors_str:
            return False
        return True

    def optimize(self, priority_vector, current_makespan, current_plv):
        """
        Apply local search while iteractively refining the schedule.
        Works with priority vectors instead of ordered lists.
        """
        improved = True

        # Sort operations by priority
        best_ordered_ops = sorted(priority_vector.keys(), key=lambda op: priority_vector[op])

        best_cmax = current_makespan
        best_plv = current_plv

        while improved:
            improved = False

            for i in range(len(best_ordered_ops) - 1):
                op_atual = best_ordered_ops[i]
                op_proxima = best_ordered_ops[i+1]

                if self._is_valid_swap(op_atual, op_proxima):
                    # Swap priorities slightly to swap their order
                    neighbour_ordered_ops = list(best_ordered_ops)
                    neighbour_ordered_ops[i], neighbour_ordered_ops[i+1] = neighbour_ordered_ops[i+1], neighbour_ordered_ops[i]

                    # Create a new priority vector
                    neighbour_vector = {}
                    n = len(neighbour_ordered_ops)
                    for idx, op in enumerate(neighbour_ordered_ops):
                        neighbour_vector[op] = idx / max(1, n - 1)

                    # Evaluate new scenario with SSGS
                    makespan, plv, _ = self.ssgs.decode(neighbour_vector)

                    # Acceptance criteria: (is Cmax smaller?) OR (is PLV samller?)
                    if makespan < best_cmax or (makespan == best_cmax and plv < best_plv):
                        best_cmax = makespan
                        best_plv = plv
                        best_ordered_ops = neighbour_ordered_ops
                        improved = True
                        break

        # Re-generate the final priority vector based on the best ordered ops
        best_vector = {}
        n = len(best_ordered_ops)
        for idx, op in enumerate(best_ordered_ops):
            best_vector[op] = idx / max(1, n - 1)

        return best_vector, best_cmax, best_plv

# ====================================================
# MODULE 6: VISUALIZATION
# ====================================================

def generate_gantt_chart(schedule, filename='gantt_chart.png'):
    """
    Generates a Gantt chart from the scheduled operations.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    # Get distinct machines and assign them y-positions
    machines = list(set([entry['operation'].machine for entry in schedule]))
    machines.sort(reverse=True) # So the first machine is at the top
    machine_y_map = {m: i for i, m in enumerate(machines)}

    # Define colors
    colors = list(mcolors.TABLEAU_COLORS.values())
    task_colors = {}

    for entry in schedule:
        op = entry['operation']
        start = entry['start']
        finish = entry['finish']
        duration = finish - start
        machine = op.machine
        task_id = op.task_id

        y_pos = machine_y_map[machine]

        if task_id not in task_colors:
            task_colors[task_id] = colors[len(task_colors) % len(colors)]

        color = task_colors[task_id]

        ax.barh(y_pos, duration, left=start, height=0.5, color=color, edgecolor='black', alpha=0.8)

        # Add a text label inside the bar
        label = f"T{task_id}-O{op.op_id}"
        ax.text(start + duration/2, y_pos, label, ha='center', va='center', color='white', fontsize=8, fontweight='bold')

    # Formatting the chart
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel('Time (minutes)')
    ax.set_ylabel('Machines')
    ax.set_title('Optimal Schedule Gantt Chart')
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"Gantt chart successfully saved to {filename}")

# ====================================================
# MODULE 7: HYBRID ITLBO-GRASP OPTIMIZER AND PIPELINE
# ====================================================

class Hybrid_ITLBO_GRASP:
    def __init__(self, operations, pop_size=30, max_generations=50, alpha=0.3):
        self.operations = operations
        self.pop_size = pop_size
        self.max_generations = max_generations

        self.techs = create_technicians_list(TECHNICIANS_AVAILABLE)
        self.ssgs = SSGS(operations, self.techs, MACHINE_SPATIAL_CAPACITY)
        self.grasp_constructor = GRASPConstructor(operations, alpha=alpha)
        self.grasp_local_search = GRASPLocalSearch(self.ssgs)

        self.population = []
        self.fitness = []
        self.makespans = []
        self.plvs = []

        # Weights for the penalty linear equation (Fitness)
        self.w1 = 1.0 # makespan weight
        self.w2 = 1.0 # plv weight

    def _eval(self, vector):
        mk, plv, schedule = self.ssgs.decode(vector)
        return mk * self.w1 + plv * self.w2, mk, plv, schedule

    def _eval_and_update(self, i, new_learner, current_learner):
        fit, mk, plv, _ = self._eval(new_learner)
        if fit < self.fitness[i]:
            self.population[i] = new_learner
            self.fitness[i] = fit
            self.makespans[i] = mk
            self.plvs[i] = plv
            return new_learner
        return current_learner

    def initialize_population(self):
        print(f"Initializing Population (Size: {self.pop_size}) with GRASP Constructor...")
        for _ in range(self.pop_size):
            vector = self.grasp_constructor.generate_priority_vector()
            fit, mk, plv, _ = self._eval(vector)

            self.population.append(vector)
            self.fitness.append(fit)
            self.makespans.append(mk)
            self.plvs.append(plv)

    def optimize(self):
        history = []

        start_time_gen0 = time.time()
        self.initialize_population()
        end_time_gen0 = time.time()

        best_fit = min(self.fitness)
        best_idx = self.fitness.index(best_fit)

        global_best_vector = self.population[best_idx].copy()
        global_best_mk = self.makespans[best_idx]
        global_best_plv = self.plvs[best_idx]

        history.append({
            'generation': 0,
            'time': end_time_gen0 - start_time_gen0,
            'best_makespan': self.makespans[best_idx],
            'best_plv': self.plvs[best_idx],
            'best_fitness': self.fitness[best_idx],
            'global_best_makespan': global_best_mk,
            'global_best_plv': global_best_plv,
            'global_best_fitness': best_fit
        })

        for gen in range(self.max_generations):
            start_time_gen = time.time()
            # Sort population to rank
            ranked_indices = np.argsort(self.fitness)
            teacher_idx = ranked_indices[0]
            teacher = self.population[teacher_idx]

            # Calculate Mean Vector
            mean_vector = {}
            for op in self.operations:
                mean_vector[op] = np.mean([ind[op] for ind in self.population])

            # Calculate Fitness-Distance Ratio to find Assistant Teacher
            # F_n = rank (1 is best). D_n = spatial distance from teacher rank (1 is closest)
            distances = []
            for i in range(self.pop_size):
                if i == teacher_idx:
                    distances.append(0.0)
                else:
                    dist = np.sqrt(sum((self.population[i][op] - teacher[op])**2 for op in self.operations))
                    distances.append(dist)

            dist_ranked_indices = np.argsort(distances)

            fd_ratios = []
            for i in range(self.pop_size):
                if i == teacher_idx:
                    fd_ratios.append(float('inf')) # Teacher cannot be assistant
                    continue
                f_n = np.where(ranked_indices == i)[0][0] + 1
                d_n = np.where(dist_ranked_indices == i)[0][0] + 1
                fd_ratios.append(f_n / d_n)

            assistant_idx = np.argmin(fd_ratios)
            assistant = self.population[assistant_idx]

            for i in range(self.pop_size):
                learner = self.population[i]

                # FASE 1: TEACHING
                r = random.random()
                T_F = random.randint(1, 2)
                new_learner_1 = {}
                for op in self.operations:
                    new_learner_1[op] = learner[op] + r * (teacher[op] - T_F * mean_vector[op])
                    new_learner_1[op] = max(0.0, min(1.0, new_learner_1[op])) # bound

                learner = self._eval_and_update(i, new_learner_1, learner)

                # FASE 2: ASSISTANT TEACHING
                r1 = random.random()
                r2 = random.random()
                new_learner_2 = {}
                for op in self.operations:
                    new_learner_2[op] = learner[op] + r1 * (teacher[op] - learner[op]) + r2 * (assistant[op] - learner[op])
                    new_learner_2[op] = max(0.0, min(1.0, new_learner_2[op]))

                learner = self._eval_and_update(i, new_learner_2, learner)

                # FASE 3: LEARNING
                partner_idx = random.choice([x for x in range(self.pop_size) if x != i])
                partner = self.population[partner_idx]
                new_learner_3 = {}
                r3 = random.random()

                for op in self.operations:
                    if self.fitness[i] < self.fitness[partner_idx]:
                        new_learner_3[op] = learner[op] + r3 * (learner[op] - partner[op])
                    else:
                        new_learner_3[op] = learner[op] + r3 * (partner[op] - learner[op])
                    new_learner_3[op] = max(0.0, min(1.0, new_learner_3[op]))

                learner = self._eval_and_update(i, new_learner_3, learner)

            # FASE 4: INTENSIFICAÇÃO COM BUSCA LOCAL GRASP (Top 5%)
            top_n = max(1, int(0.05 * self.pop_size))
            elite_indices = np.argsort(self.fitness)[:top_n]

            for idx in elite_indices:
                refined_vector, ref_mk, ref_plv = self.grasp_local_search.optimize(
                    self.population[idx], self.makespans[idx], self.plvs[idx]
                )
                ref_fit = ref_mk * self.w1 + ref_plv * self.w2

                if ref_fit < self.fitness[idx]:
                    self.population[idx] = refined_vector
                    self.fitness[idx] = ref_fit
                    self.makespans[idx] = ref_mk
                    self.plvs[idx] = ref_plv

            # Update Global Best
            gen_best_idx = np.argmin(self.fitness)
            gen_best_mk = self.makespans[gen_best_idx]
            gen_best_plv = self.plvs[gen_best_idx]
            gen_best_fit = self.fitness[gen_best_idx]

            if self.fitness[gen_best_idx] < best_fit:
                best_fit = self.fitness[gen_best_idx]
                global_best_vector = self.population[gen_best_idx].copy()
                global_best_mk = self.makespans[gen_best_idx]
                global_best_plv = self.plvs[gen_best_idx]
                print(f"Gen {gen+1:02d} | NEW OPTIMAL >>> Makespan: {global_best_mk:.0f} | PLV: {global_best_plv:.2f}")

            end_time_gen = time.time()
            history.append({
                'generation': gen + 1,
                'time': end_time_gen - start_time_gen,
                'best_makespan': gen_best_mk,
                'best_plv': gen_best_plv,
                'best_fitness': gen_best_fit,
                'global_best_makespan': global_best_mk,
                'global_best_plv': global_best_plv,
                'global_best_fitness': best_fit
            })

        # Final decode for the best schedule
        _, _, best_schedule = self.ssgs.decode(global_best_vector)
        return global_best_mk, global_best_plv, best_schedule, history

if __name__ == '__main__':
    print(">>> INITIALIZING MAINTENANCE SCHEDULE OPTIMIZER WITH HI-ITLBO-GRASP-SSGS <<<")

    try:
        # NOTE: Make sure the file actually exists and paths are correct.
        operations = load_all_operations('data/Case 1.xlsx', ['RRU', 'HQL', 'ITP', 'ISS', 'TLU'])

        print(f"[{len(operations)}] operations loaded successfull!")

    except Exception as e:
        print(f"Error: {e}")
        # exit() is generally fine, but we'll print and continue if operations were not found.
        # This will fail fast anyway below if operations is not defined.
        exit()

    print("\nRunning Hybrid ITLBO-GRASP Optimizer...")
    # Parameters can be adjusted as needed
    # Using smaller population and generations for quick testing, but functionally robust.
    optimizer = Hybrid_ITLBO_GRASP(operations, pop_size=10, max_generations=50, alpha=0.3)
    best_makespan, best_plv, best_schedule, history = optimizer.optimize()

    # Save optimization metrics history
    history_df = pd.DataFrame(history)
    history_df.to_csv("optimization_history.csv", index=False)
    print(f"\nOptimization history saved to 'optimization_history.csv' with {len(history_df)} generations recorded.")

    print("\n=======================================================")
    print("                RESULTADO DA OTIMIZAÇÃO                ")
    print("=======================================================")
    print(f"Total downtime (Makespan): {best_makespan:.0f} minutes ({best_makespan/60:.2f} horas)")
    print(f"Personel Loading Variance (PLV): {best_plv:.2f}")
    print("=======================================================\n")

    print("Ordem Lógica das Tarefas no Cronograma Ótimo:")
    # sort the schedule chronologically by start time
    best_schedule.sort(key=lambda x: x['start'])
    for entry in best_schedule:
        op = entry['operation']
        techs = ", ".join(entry['technicians'])
        print(f"-> Máquina: {op.machine} | Task: {op.task_id} | Op: {op.op_id} | Start: {entry['start']} | Finish: {entry['finish']} | Techs: [{techs}]")

    print("\nGenerating Gantt Chart...")
    generate_gantt_chart(best_schedule)
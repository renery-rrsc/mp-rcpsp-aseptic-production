import time
from structure import SSGS, Operation, Technician

def run_benchmark():
    # Setup dummy data with many technicians to show the O(N) impact clearly
    techs = [Technician(f"T{i}", ["S1", "S2", "S3"] if i % 2 == 0 else ["S2", "S4"]) for i in range(5000)]
    ops = [Operation("M1", 1, i, 1, "S2", 1, []) for i in range(1000)]
    machine_limits = {"M1": 10}

    ssgs = SSGS(ops, techs, machine_limits)
    ssgs.scheduled_operations = []

    start_time = time.time()

    for i in range(5000):
        op = ops[i % len(ops)]
        ssgs._find_earliest_start_time_with_resources(op, 0)

    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    run_benchmark()

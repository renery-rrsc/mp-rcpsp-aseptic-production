import time
import numpy as np

def original(pop_size, ranked_indices, dist_ranked_indices, teacher_idx):
    fd_ratios = []
    for i in range(pop_size):
        if i == teacher_idx:
            fd_ratios.append(float('inf'))
            continue
        f_n = np.where(ranked_indices == i)[0][0] + 1
        d_n = np.where(dist_ranked_indices == i)[0][0] + 1
        fd_ratios.append(f_n / d_n)
    return fd_ratios

def optimized(pop_size, ranked_indices, dist_ranked_indices, teacher_idx):
    f_n_lookup = np.argsort(ranked_indices) + 1
    d_n_lookup = np.argsort(dist_ranked_indices) + 1

    fd_ratios = []
    for i in range(pop_size):
        if i == teacher_idx:
            fd_ratios.append(float('inf'))
            continue
        f_n = f_n_lookup[i]
        d_n = d_n_lookup[i]
        fd_ratios.append(f_n / d_n)
    return fd_ratios

pop_size = 1000
np.random.seed(42)
fitness = np.random.rand(pop_size)
distances = np.random.rand(pop_size)

ranked_indices = np.argsort(fitness)
dist_ranked_indices = np.argsort(distances)
teacher_idx = ranked_indices[0]

# warmup
original(pop_size, ranked_indices, dist_ranked_indices, teacher_idx)
optimized(pop_size, ranked_indices, dist_ranked_indices, teacher_idx)

# Verify correctness
res1 = original(pop_size, ranked_indices, dist_ranked_indices, teacher_idx)
res2 = optimized(pop_size, ranked_indices, dist_ranked_indices, teacher_idx)
assert res1 == res2, "Results do not match!"

start = time.perf_counter()
for _ in range(100):
    original(pop_size, ranked_indices, dist_ranked_indices, teacher_idx)
original_time = time.perf_counter() - start

start = time.perf_counter()
for _ in range(100):
    optimized(pop_size, ranked_indices, dist_ranked_indices, teacher_idx)
optimized_time = time.perf_counter() - start

print(f"Original: {original_time:.4f}s")
print(f"Optimized: {optimized_time:.4f}s")
print(f"Speedup: {original_time / optimized_time:.2f}x")

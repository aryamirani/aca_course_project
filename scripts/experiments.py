"""Experiment definitions for the TAGE study.

Every configuration is (name, group, binary, env) where env holds the predictor's run-time
parameters (see predictors/tage/tage.h). A configuration may belong to several groups,
it is only simulated once.
"""

TRACES = [
    "600.perlbench_s-210B",
    "602.gcc_s-734B",
    "605.mcf_s-665B",
    "623.xalancbmk_s-700B",
    "625.x264_s-18B",
    "631.deepsjeng_s-928B",
    "641.leela_s-800B",
    "657.xz_s-3167B",
]

# default simplified TAGE: bimodal base (8K entries) + 4 tagged tables (1K entries, 9-bit tags), L = 5..130
TAGE_DEFAULT = {"TAGE_NUM_TABLES": "4", "TAGE_MIN_HIST": "5", "TAGE_MAX_HIST": "130",
                "TAGE_LOG_BASE": "13", "TAGE_LOG_TAGGED": "10", "TAGE_TAG_BITS": "9"}


def tage(**overrides):
    env = dict(TAGE_DEFAULT)
    env.update({k: str(v) for k, v in overrides.items()})
    return env


CONFIGS = {}  # name -> (binary, env)
GROUPS = {}   # group -> [config names]


def add(group, name, binary, env=None):
    CONFIGS.setdefault(name, (binary, env or {}))
    GROUPS.setdefault(group, []).append(name)


# 1. headline comparison: stock ChampSim baselines (4 KB each) vs default TAGE
add("baseline", "bimodal", "champsim_bimodal")
add("baseline", "gshare", "champsim_gshare")
add("baseline", "tage", "champsim_tage", tage())

# 2. storage budget: TAGE (4 tables) vs gshare vs bimodal at matched sizes
for lt, lb in [(8, 11), (9, 12), (10, 13), (11, 14), (12, 15), (13, 16)]:
    name = "tage" if lt == 10 else f"tage_lt{lt}"
    add("storage", name, "champsim_tage", tage(TAGE_LOG_TAGGED=lt, TAGE_LOG_BASE=lb))
for log_size in range(13, 19):
    add("storage", f"gshare_l{log_size}", "champsim_gshare_param", {"GSHARE_LOG_SIZE": str(log_size)})
    add("storage", f"bimodal_l{log_size}", "champsim_bimodal_param", {"BIMODAL_LOG_SIZE": str(log_size)})

# 3a. number of tagged tables, fixed table size (storage grows with N)
for n in [1, 2, 3, 4, 6, 8]:
    add("tables_fixed_size", "tage" if n == 4 else f"tage_n{n}", "champsim_tage", tage(TAGE_NUM_TABLES=n))

# 3b. number of tagged tables at a fixed 16 KB budget (fewer, bigger tables vs more, smaller ones)
for n, lt in [(1, 13), (2, 12), (4, 11), (8, 10), (16, 9)]:
    add("tables_fixed_budget", f"tage_16k_n{n}", "champsim_tage", tage(TAGE_NUM_TABLES=n, TAGE_LOG_TAGGED=lt))

# 4a. longest history length Lmax (Lmin = 5, 4 tables)
for lmax in [16, 32, 64, 130, 256, 512, 1024]:
    add("max_hist", "tage" if lmax == 130 else f"tage_lmax{lmax}", "champsim_tage", tage(TAGE_MAX_HIST=lmax))

# 4b. shortest history length Lmin (Lmax = 130)
for lmin in [2, 5, 10, 20]:
    add("min_hist", "tage" if lmin == 5 else f"tage_lmin{lmin}", "champsim_tage", tage(TAGE_MIN_HIST=lmin))

# 4c. geometric vs linear spacing of the same range
add("spacing", "tage", "champsim_tage", tage())
add("spacing", "tage_linear", "champsim_tage", tage(TAGE_HIST_LIST="5,47,88,130"))

# 5. partial tag width
for bits in [4, 6, 8, 9, 11, 13]:
    add("tag_bits", "tage" if bits == 9 else f"tage_tag{bits}", "champsim_tage", tage(TAGE_TAG_BITS=bits))

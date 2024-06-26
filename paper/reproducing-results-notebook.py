# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
#   language_info:
#     name: python
#     nbconvert_exporter: python
#     pygments_lexer: ipython3
# ---

# %% [markdown]
# # how to reproduce the results in the paper
#
# **NOTE** you may need to `pip install jupytext` in order to open this file as a notebook in Jupyter
#
# this Jupyter notebook uses the file `timings/timings.csv`, as shipped with the paper repo  
# it allows to reproduce the same runs locally, and to gather your own performance measurements
#
# it stores its own results in a file named `timings/user_timings.csv`  
# these are used as a cache - i.e. not re-run if already present; you can simply delete or move this file if you want to re-start from scratch

# %%
# this one must not change
REF_TIMINGS = "timings/timings.csv"

# default - see next cell for how to change it
OUR_TIMINGS = "timings/user_timings.csv"

# speed mode: run only short runs
SKIP_LONG_RUNS = False

# by default, only on CPU
RUN_ON_GPUS = False

# 
DRY_RUN = False


# %%
# provide a way to choose the output from the command line
# but argparse won't work from Jupyter, so:

try:
    # this is defined in a Jupyter / IPython environment
    # in this case just change OUR_TIMINGS above
    get_ipython()
except:
    # not in IPython/notebook - so we run from the command line
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-o", "--output", default=OUR_TIMINGS, 
                        help="filename for the csv output")
    parser.add_argument("-s", "--speed", default=SKIP_LONG_RUNS, 
                        action="store_true",
                        help="speed up: skip runs that had taken > 30s")
    parser.add_argument("-g", "--gpu", default=RUN_ON_GPUS,
                        action="store_true",
                        help="enable runs that require a GPU")
    parser.add_argument("-d", "--dry-run", default=DRY_RUN,
                        action="store_true",
                        help="just show the commands to run, do not actually trigger them")
    args = parser.parse_args()
    OUR_TIMINGS = args.output
    SKIP_LONG_RUNS = args.speed
    RUN_RUN_ON_GPUS = args.gpu
    DRY_RUN = args.dry_run

print(f"using {OUR_TIMINGS=} {SKIP_LONG_RUNS=} {RUN_ON_GPUS=} {DRY_RUN=}")

# %% [markdown]
# ## loading the paper timings
#
# to get a list of what would need to be done; the reference file here comes with the paper

# %%
import pandas as pd

# %%
paper = pd.read_csv(REF_TIMINGS)
paper.shape

# %%
paper.head(3)

# %%
total = len(paper)

# %% [markdown]
# ### dropping the njobs column
#
# we won't need this

# %%
paper[paper.inferred.notna() & paper.njobs.notna()]

# %%
paper.drop(columns=['njobs'], inplace=True)
paper.shape

# %% [markdown]
# ## loading previous runs
#
# to avoid re-running them if already done; here we load our local file, the one that contains **OUR** previous runs

# %%
try:
    previous = (
        pd.read_csv(OUR_TIMINGS)
        .rename(columns={'time': 'previous'})
        # this is unchanged between paper and previous
        # so avoid duplication in the merge below
        .drop(columns=['inferred'])
    )
except:
    previous = pd.DataFrame()

if len(previous):
    print(f"we have {len(previous)} previous runs already")
else:
    print(f"restarting from scratch")

# %% [markdown]
# ### compute todo runs: merge both tables
#
# and ignore entries with a previous time

# %%
# what to join on
KEYS = "model|n_components|n_splits|n|k|m".split("|")

if not len(previous):
    todo = paper.copy()
else:
    join = pd.merge(paper, previous, on=KEYS, how='left')
    todo = join[join.previous.isna()]


# %%
def status(message):
    print(f"{message:>30}: we still have {len(todo):3} runs out of a {total} total")

status("from previous runs")

# %%
todo

# %% [markdown]
# ## filtering

# %% [markdown]
# ### isolating lines doable on a CPU (optional)

# %%
if not RUN_ON_GPUS:
    todo = todo[ ~ todo.model.str.contains('jax')]
status("removed GPU-only runs")

# %% [markdown]
# ### ignore long runs

# %%
if SKIP_LONG_RUNS:
    todo = todo[todo.time < 30]
    status("keeping only short runs")

# %% [markdown]
# ### ignore entries whose estimation cannot be automated

# %%
# normalize .inferred to make it a bool

todo.loc[:, 'inferred'] = todo.inferred.notna()

# %%
ESTIMABLE = ['sk', 'np1', 'np2']

# %%
# keep only the ones that are
# - either not inferred in the paper
# - or that are estimable

todo = todo[ (todo.inferred != True) | todo.model.isin(ESTIMABLE)]

status("keeping only estimable")

# %% [markdown]
# ## actually running the selected runs

# %%
todo[~todo.inferred | todo.model.isin(ESTIMABLE)]

# %%
import subprocess
import numpy as np

remains = len(todo)

try:
    for index, t in enumerate(todo.itertuples()):
        print(f"# {index+1}/{remains}: ({t.model} x {t.n_components} x {t.n_splits} x {t.n} - {t.inferred}) - expect {t.time:.2f}")
        estimate = "" if not t.inferred else "--estimate"
        command = (f"python3 time_pls.py -o {OUR_TIMINGS}"
                   f" -model {t.model} -n_components {t.n_components}" 
                   f" -n_splits {t.n_splits} -n {t.n} -k{t.k} -m {t.m} -n_jobs -1"
                   f" {estimate}")
        print(command)
        if DRY_RUN:
            continue
        subprocess.run(command, shell=True)
except KeyboardInterrupt:
    print("Bye")

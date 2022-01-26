# Value-guided construal

This repository contains code for
the paper
**People construct simplified models to plan**
by Ho, Abel, Correa, Littman, Cohen, and Griffiths.
It is organized into the following
subdirectories:
- `experiment.psiturkapp` contains
code for running the experiments using the
psiturk framework (see [here](https://psiturk.org/)).
- `experiments` includes data and code for generating experimental
trials
- `analyses` includes notebooks and scripts for analyses in the paper
- `vgc_project` is a python package that
`analyses` and `modeling` depend on
- `modeling` includes modeling code that is not directly
related to the experiments

## Set up
The project uses Python 3 (3.7 definitely works, other versions may or may not work).
One way to use it is by setting up a virtualenv:
```
$ virtualenv -p python3 env
$ source env/bin/activate
(env)$ env/bin/pip install -r requirements.txt
```

You need to also install the `vgc_project` package
into the virtual environment
(the `-e` flag installs it in editable mode):
```
(env)$ env/bin/pip install -e ./vgc_project
```

## Running analyses

Once you have a python environment set up,
the `projects.py` script can be used to run
various analysis scripts and notebooks for the experiments.

First, unzip all the datafiles:
```
$ python project.py unzip_files
```

Then, run the analysis notebooks (this could take awhile the first time
but afterwards various computations will be cached):
```
$ python project.py run_analysis_notebooks
```

The analysis notebooks are all included in `analyses/`.

### Replicability
You may have to set the `PYTHONHASHSEED` variable
to 0 to replicate certain analyses. See
[here](https://stackoverflow.com/questions/58067359/is-there-a-way-to-set-pythonhashseed-for-a-jupyter-notebook-session).

### Analyses with `lmer`
Some of the hierarchical generalized linear regression analyses
are done using the `lmer` package in R.
The `vgc_project.r` module provides wrappers that
interface with R using the `rpy2` package
(see [here](https://rpy2.github.io/)). 
This requires installing R.

Note: I have found that rpy2 will not install on python 3.9 on OSX.

## Code for models

All the code for the value-guided construal model
and alternative models is organized in the `vgc_project`
package folder. 
Several of the models rely on code from the `msdm` (version 0.6)
python package, which is automatically installed via pip using
the instructions above.

## Running/demoing experiments
### Testing locally
You can run the code in `experiment.psiturkapp` as a psiturk experiment by doing the following:
```
$ cd experiment.psiturkapp
$ make dev
```

This creates a server at [http://localhost:22362](http://localhost:22362).
Specific experiments can be demoed at the following links:
- [Initial experiment (Exp 1)](http://localhost:22362/testexperiment?CONFIG_FILE=exp1.0-config.json.zip)
- [Up-front planning experiment (Exp 2)](http://localhost:22362/testexperiment?CONFIG_FILE=exp2.0-config.json.zip)
- [Critical maze experiment with awareness probes (Exp 3)](http://localhost:22362/testexperiment?CONFIG_FILE=exp3.0-config.json.zip&condition=0)
- [Critical maze experiment with recall probes (Exp 3)](http://localhost:22362/testexperiment?CONFIG_FILE=exp3.0-config.json.zip&condition=1)
- [Process-tracing experiment with initial mazes (Exp 4a)](http://localhost:22362/testexperiment?CONFIG_FILE=config-4a.json.zip&page=3)
- [Process-tracing experiment with critical mazes (Exp 4b)](http://localhost:22362/testexperiment?CONFIG_FILE=config-4b.json.zip&page=3)
- [Perceptual control with initial mazes (Exp 5a)](http://localhost:22362/testexperiment?CONFIG_FILE=config-5a.json.zip&page=2)
- [Perceptual control with critial mazes and awareness probes (Exp 5b)](http://localhost:22362/testexperiment?CONFIG_FILE=config-5b.json.zip&page=2&condition=0)
- [Perceptual control with critial mazes and recall probes (Exp 5b)](http://localhost:22362/testexperiment?CONFIG_FILE=config-5b.json.zip&page=2&condition=3)
- [Execution control with initial mazes (Exp 6a)](http://localhost:22362/testexperiment?CONFIG_FILE=config-6a.json.zip&page=2)
- [Execution control with initial mazes and awareness probes (Exp 6b)](http://localhost:22362/testexperiment?CONFIG_FILE=config-6b.json.zip&page=2&condition=0)
- [Execution control with initial mazes and recall probes (Exp 6b)](http://localhost:22362/testexperiment?CONFIG_FILE=config-6b.json.zip&page=2&condition=3)


import fire
import zipfile
import os
import subprocess

def __run_cmd(cmd_list, cwd='.'):
    print(" ".join(cmd_list))
    process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, cwd=cwd)
    output, error = process.communicate()
    if output:
        print(output.decode("UTF-8"))
    if error:
        print(error)

files_to_zip = [
    # analyzed datafiles
    "experiments/exp1/data/navtrials.json",
    "experiments/exp1/data/participantdata.json",
    "experiments/exp1/data/attentiontrials.json",
    "experiments/exp2/data/navtrials.json",
    "experiments/exp2/data/participantdata.json",
    "experiments/exp2/data/attentiontrials.json",
    "experiments/exp3/data/navtrials.json",
    "experiments/exp3/data/participantdata.json",
    "experiments/exp3/data/memorytrials.json",
    "experiments/exp3/data/attentiontrials.json",
    "experiments/exp4a/data/hovering-data-trials.json",
    "experiments/exp4a/data/all-navigation-trials.json",
    "experiments/exp4a/data/participantdata.json",
    "experiments/exp4b/data/hovering-data-trials.json",
    "experiments/exp4b/data/all-navigation-trials.json",
    "experiments/exp4b/data/participantdata.json",
    "experiments/exp5a/data/all-attention-trials.json",
    "experiments/exp5a/data/all-dot-trials.json",
    "experiments/exp5a/data/all-survey-trials.json",
    "experiments/exp5b/data/all-attention-trials.json",
    "experiments/exp5b/data/all-dot-trials.json",
    "experiments/exp5b/data/all-memory-trials.json",
    "experiments/exp5b/data/all-survey-trials.json",
    "experiments/exp6a/data/all-attention-trials.json",
    "experiments/exp6a/data/all-nav-trials.json",
    "experiments/exp6a/data/all-survey-trials.json",
    "experiments/exp6b/data/all-attention-trials.json",
    "experiments/exp6b/data/all-nav-trials.json",
    "experiments/exp6b/data/all-memory-trials.json",
    "experiments/exp6b/data/all-survey-trials.json",

    #config files
    "experiments/exp1/exp1.0-config.json",
    "experiments/exp2/exp2.0-config.json",
    "experiments/exp3/exp3.0-config.json",
    "experiments/exp4a/config.json",
    "experiments/exp4b/config.json",
    "experiments/exp5a/config.json",
    "experiments/exp5b/config.json",
    "experiments/exp6a/config.json",
    "experiments/exp6b/config.json",
]

def zip_files():
    for dirfile in files_to_zip:
        dir, file = os.path.split(dirfile)
        with zipfile.ZipFile(dirfile+".zip", mode="w") as zipper:
            zipper.write(
                dirfile,
                arcname=file,
                compress_type=zipfile.ZIP_DEFLATED
            )
        print(f"Zipped {dirfile} to {dirfile+'.zip'}")

def unzip_files():
    for dirfile in files_to_zip:
        dir, file = os.path.split(dirfile)
        with zipfile.ZipFile(dirfile+".zip", "r") as unzipper:
            unzipper.extractall(dir)
        print(f"Unzipped {dirfile+'.zip'} to {dirfile}")

notebooks = [
    "exp-1.ipynb",
    "exp-2.ipynb",
    "exp-3.ipynb",
    "exp-4.ipynb",
    "exp-controls.ipynb",
    "plot-grid-measure-figs.ipynb",
    "plot-critical-mazes.ipynb",
    "plot-pairwise-analyses.ipynb",
    "plot-fitted-vgc.ipynb",
    "plot-qbin-figure.ipynb",
    "plot-global-lesion-tables.ipynb",
]
ANALYSIS_DIR = "./analyses"

def run_analysis_notebooks():
    for notebook in notebooks:
        notebook_path = os.path.join(ANALYSIS_DIR, notebook)
        toprint = f"Running {notebook_path}"
        print("="*len(toprint))
        print(toprint)
        print("="*len(toprint))

        __run_cmd(
            cmd_list=[
                "ipython",
                notebook,
            ],
            cwd=ANALYSIS_DIR
        )
        print("-------------------------------------------")
    print("SUCCESS")

if __name__ == "__main__":
    fire.Fire()

import subprocess
import numpy as np
import itertools
import os
from mpi4py import MPI
import logging
import shutil
import glob
import pandas as pd

def run_command(exec_path, *args):
    """Run an executable with command-line arguments and return the output as a string."""
    command = [exec_path] + list(args)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout

def replace_x_values(file_path, new_values, line_number):
    # Open the file in read mode and read the contents
    logging.debug(os.getcwd())
    print(os.getcwd())
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Replace the values in line 78 with the new values
    line_index = line_number  # line numbering starts from 0
    line = lines[line_index]
    values = line.split()[5:]  # get the values from line 78
    new_values_str = "".join([v for v in new_values])  # format new values to one decimal place
    new_line = line[:line.index(values[0])][:-1]+ new_values_str+ "\n"  # create new line with original spaces intact
    
    # Write the modified contents back into the file
    with open(file_path, 'w') as f:
        lines[line_index] = new_line
        f.writelines(lines)
        
def pad_nums(num, required_length = 6):
    num_str = str(num)
    while len(num_str) < required_length: num_str = " "+num_str
    return num_str

def gib_new_vals(parameters_list = []): 
    return list(itertools.product(*[[parameter] 
                                    if type(parameter) == str 
                                    else [str(round(n,2)) for n in parameter] for parameter in parameters_list]))

def replace_x_values_ECO(file_path, new_value, line_number):
    new_value=round(new_value,2)
    # Open the file in read mode and read the contents
    with open(file_path, 'r') as f:
        lines = f.readlines()
    # Replace the RUE value for specific line number
    line = lines[line_number - 1]     # indexing starts at 0
    values = line.split()[2:]  # get the values from the current line, ignoring the beginning part
    values[4] = str(new_value) # change RUE value to passed in value
    new_values_str = "" + values[0]
    for i in range(1, len(values)): # for each value after the first, add correct spacing
        temp_str = str(values[i])
        while len(temp_str) < 6: temp_str = " " + temp_str
        new_values_str = new_values_str + temp_str
    new_line = line[:line.index(values[0])] + new_values_str + "\n"  # merge beginning values with new string
    # Write the modified contents back into the file
    with open("SGCER048.ECO", 'w') as f:
        lines[line_number] = new_line
        f.writelines(lines)

def replace_x_values_SPE(file_path, new_value):
    # Open the file in read mode and read the contents
    with open(file_path, 'r') as f:
        lines = f.readlines()
    # Replace the RLWR value for specific line number
    line = lines[38]  # Always removing line 38
    change_val = line[10:14]
    new_line = line.replace(change_val, str(new_value))
    # Write the modified contents back into the file
    with open("SGCER048.SPE", 'w') as f:
        lines[38] = new_line
        f.writelines(lines)

def run_simulation(all_value_permutations_cul, all_value_permutations_eco,all_value_permutations_spe, i,n_permutations):
    new_values_cul=all_value_permutations_cul[i%len(all_value_permutations_cul)]
    new_values_eco=all_value_permutations_eco[i%len(all_value_permutations_eco)]
    new_values_spe=all_value_permutations_spe[i%len(all_value_permutations_spe)]
    cwd = os.getcwd()
    new_dir_name = "output_"+str(i)
    new_dir_path = os.path.join(cwd, new_dir_name)
    if os.path.exists(new_dir_path):
        if os.path.isdir(new_dir_path):
            shutil.rmtree(new_dir_path, ignore_errors=True)
    os.mkdir(new_dir_path)
    file_list = [ "CLKS0023.WTH","UFKS2323.SNX", "SGCER048.CUL", "SGCER048.ECO", "SGCER048.SPE","SOIL.SOL"]
    for filename in file_list:
        src_path = os.path.join(cwd, filename)
        dst_path = os.path.join(new_dir_path, filename)
        shutil.copy(src_path, dst_path)
    os.chdir(new_dir_path)
    replace_x_values("SGCER048.CUL", [pad_nums(num) for num in new_values_cul], 77)
    replace_x_values_ECO("SGCER048.ECO", new_values_eco, 20)
    replace_x_values_SPE("SGCER048.SPE", new_values_spe)
    output = run_command('PATHTO/dscsm048', 'A', 'UFKS2323.SNX')
    os.chdir("..")

def combine_csvs():
    cwd = os.getcwd()
    output_dirs = glob.glob(os.path.join(cwd, "output_*"))

    df_list = []
    header=[]
    for dir_path in output_dirs:
        summary_path = os.path.join(dir_path, "summary.csv")
        if os.path.exists(summary_path):
            df = pd.read_csv(summary_path,index_col=False)
            if len(header)==0:
                header = df.columns.tolist()
            df_list.append(df)
    concat_df = pd.concat(df_list ,ignore_index=True)
    concat_df.to_csv('output.csv', columns=header, index=False)

def remove_ouput_directories():
    cwd = os.getcwd()
    output_dirs = glob.glob(os.path.join(cwd, "output_*"))
    for directory in output_dirs:
        if os.path.exists(directory):
            if os.path.isdir(directory):
                shutil.rmtree(directory)

if __name__ == '__main__':
    file_path = "SGCER048.CUL"
    new_values_cul = ["325.0", "102.0", "15.50", np.arange(1,320,50) , "617.5", "152.5", "81.5", np.arange(300,701,50),"49.00", "11.0", np.arange(2,6.5,1)]
    new_values_eco= np.arange(1.2,1.41,0.1)
    new_values_spe= np.arange(0.1,1.1,0.3)
    line_number_cul = 77

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    all_value_permutations_cul = gib_new_vals(new_values_cul)
    all_value_permutations_eco = new_values_eco
    all_value_permutations_spe = new_values_spe

    n_permutations = len(all_value_permutations_cul)*len(all_value_permutations_eco)*len(all_value_permutations_spe)

    # Distribute the work among processes
    for i in range(rank, n_permutations, size):
        # permutation = all_value_permutations[i]
        run_simulation(all_value_permutations_cul,all_value_permutations_eco,all_value_permutations_spe,i,n_permutations)
    #combine_csvs()

    
    
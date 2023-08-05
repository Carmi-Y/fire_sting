import os
import glob
import pathlib
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import scienceplots

def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--input_path', help='The input directory path containing raw text files to be processed', required=True)
    parser.add_argument('-o', '--output_path', help='The output directory', required=True)
    
    args = parser.parse_args()
    input_path = os.path.normpath(args.input_path)
    output_path = os.path.normpath(args.output_path)

    # Grab all txt files in the directory
    files = glob.glob(f"{input_path}/*.txt")
    
    raw_data_all_files_df = []

    for file in files:
        file_path = os.path.normpath(file)
        # Get the file name without the extension
        file_name = pathlib.Path(file_path).stem
        
        # Read the content of the file
        content = read_data(file_path)
        
        # This isn't the best way to do this, but it works. Maybe fix later (TODO)
        write_content(content, f"{output_path}/raw_{file_name}.txt", file_name)

        # Read content to pandas dataframe
        data = pd.read_csv(f"{output_path}/raw_{file_name}.txt")

        # Remove the saved text files from the output directory
        os.remove(f"{output_path}/raw_{file_name}.txt")

        # Remove the last columns, they have no useful data
        data = data.iloc[:, :-19]
        # Also remove the "Comment" column, it has no useful data
        data = data.drop(columns=["Comment"])

        data.columns = ["file_name", "date", "time", "elapsed_time(s)", 1, 2, 3, 4, "Ch1_temperature", "Ch2_temperature", "Ch3_temperature", "Ch4_temperature"]
        raw_data_all_files_df.append(data)


    # Add files data to a dataframe containing all the data
    raw_data_all_files_df = pd.concat(raw_data_all_files_df, ignore_index=True)

    merged_data = flatten_data(raw_data_all_files_df)

    # # Save the data from all files to an excel file
    merged_data.to_excel(f"{output_path}/oxygen_data.xlsx", index=False)


    # Graph the data
    # styles = ['notebook', 'grid']
    # plt.style.use(styles)


def find_data_start_index(content, search_string):
    '''
    Find the index of the row that contains the search string

    Parameters
    ----------
    content : str
        The content of the file
    search_string : str
        The string to search for
    
    Returns
    -------
    index : int
        The index of the row that contains the search string
    '''
    indexes = []

    for index, row in enumerate(content.split("\n")):
        if search_string in row:
            indexes.append(index)

    if len(indexes) != 1:
        raise ValueError(f"Found more than one data start index. Indexes: {indexes}")
    return indexes[0]


def read_data(file_path):
    '''
    Read data from a file
    
    Parameters
    ----------
    file_path : str
        The path to the file
    
    Returns
    -------
    content : str
        The content of the file
    '''
    with open(file_path, "r") as file:
        content = file.read()

    data_start_index = find_data_start_index(content, "Date\tTime (HH:MM:SS)\tTime (s)\tComment\tCh1\tCh2\tCh3\tCh4")

    # Trim the content to only contain the data
    content = content.split("\n")[data_start_index:]
    # Remove the last row, it's empty
    content = content[:-1]
    # Replace tabs with commas
    return [row.replace("\t", ",") for row in content]


def write_content(content, path, file_name):
    '''
    Write content to a file

    Parameters
    ----------
    content : str
        The content to write to the file
    paht : str
        The path to the file
    
    Returns
    -------
    None
    '''
    path = os.path.normpath(path)
    with open(path, "w") as output_file:
        for i, item in enumerate(content):
            if i == 0:
                output_file.write(f'file_name,{item} \n')
            else:
                output_file.write(f'{file_name},{item} \n')


def flatten_data(raw_data_all_files_df):
    '''
    Description
    ------------
    Flatten the data from all files into a single dataframe

    Parameters
    ----------
    raw_data_all_files_df : pandas.DataFrame
        The dataframe containing the data from all files

    Returns
    -------
    merged_data : pandas.DataFrame
        The flattened dataframe
    '''
    # Flatten the dataframe in two steps, first melt the oxygen data, then melt the temperature data
    id_vars = ['file_name', 'date', 'time', 'elapsed_time(s)', "Ch1_temperature", "Ch2_temperature", "Ch3_temperature", "Ch4_temperature"]
    value_vars = [1, 2, 3, 4]
    oxygen_data_df = raw_data_all_files_df.melt(id_vars=id_vars, value_vars=value_vars, var_name='channel', value_name='[O2]')

    # Melt the temperature fields
    id_vars = ['file_name', 'date', 'time', 'elapsed_time(s)', "[O2]", "channel"]
    value_vars = ["Ch1_temperature", "Ch2_temperature", "Ch3_temperature", "Ch4_temperature"]
    merged_data = oxygen_data_df.melt(id_vars=id_vars, value_vars=value_vars, value_name='temperature')

    # Remove rows with no data, they contain "---"
    merged_data = merged_data[merged_data['[O2]'] != "---"]

    # Remove the "variable" column, it has no useful data
    merged_data = merged_data.drop(columns=["variable"])

    return merged_data


def plot_data(time, oxygen_concentration, title, save_dir):
    '''
    Plot the data

    Parameters
    ----------
    time : array-like
        The time data in seconds
    oxygen_concentration : array-like
        The oxygen concentration data in µM
    title : str
        The title of the plot
    save_dir : str
        The directory to save the plot to
    
    Returns
    -------
    None
    '''
    fig, ax = plt.subplots()
    ax.plot(time, oxygen_concentration)
    ax.set_xlabel("Elapsed Time (s)")
    ax.set_ylabel("$[O_{2}] µM$")
    ax.set_title(title)
    # Remove ticks from Y axis
    ax.yaxis.set_ticks_position('none')
    # Remove ticks from X axis top
    ax.xaxis.set_ticks_position('bottom')
    plt.savefig(f"{save_dir}/{title}.png")
    plt.close("all")


if __name__ == "__main__":
    main()
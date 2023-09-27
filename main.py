import os
import glob
import scipy
import pathlib
import argparse
import numpy as np
import pandas as pd
import seaborn as sns
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

    # Get the needed data from each file
    for file in files:
        file_path = os.path.normpath(file)
        # Get the file name without the extension
        file_name = pathlib.Path(file_path).stem
        
        # Read the content of the file
        content = read_data(file_path)
        
        # This isn't the best way to do this as it saves a text file to be read into memory again.
        # But it works and isn't slow so maybe fix it later
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

    oxygen_data = flatten_data(raw_data_all_files_df)

    # Make sure the numaric fields are actually numeric
    oxygen_data["elapsed_time(s)"] = pd.to_numeric(oxygen_data["elapsed_time(s)"])
    oxygen_data["[O2]"] = pd.to_numeric(oxygen_data["[O2]"])

    # Save the data from all files to an excel file
    oxygen_data.to_excel(f"{output_path}/oxygen_data.xlsx", index=False)
    
    # Index merged_data by file_name
    oxygen_data = oxygen_data.set_index("file_name")

    # Get the reaction rates for each file
    reaction_rates = get_reaction_rates_df(oxygen_data)

    # Save the reaction rates to an excel file
    reaction_rates.to_excel(f"{output_path}/reaction_rates.xlsx", index=False)

    # Create a dir for the graphs
    graphs_dir = create_directory(output_path, "graphs")

    # Graph the data
    styles = ['notebook', 'grid']
    plt.style.use(styles)

    # Iterate the rows of reaction_rates dataframe and plot the data with it's reaction rate
    for index, row in reaction_rates.iterrows():
        file_name = row["file_name"]
        channel = row["chanel"]

        # Get the oxygen data rows where the file name and channel match the values from reaction_rates
        oxygen_data_rows = oxygen_data.loc[(oxygen_data.index == file_name) & (oxygen_data["channel"] == channel)]
        
        make_single_exp_plots(oxygen_data_rows["elapsed_time(s)"], oxygen_data_rows["[O2]"], row, f"{file_name}_{channel}", graphs_dir) 
    
    # Plot the reaction rates
    make_reaction_rate_plots(reaction_rates, graphs_dir)

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


def get_exp_conditions_from_file_name(file_name):
    '''
    Description
    ------------
    Get the growth and measurement conditions from the file name

    Parameters
    ----------
    file_name : str
        The name of the file

    Returns
    -------
    expreriment_date : str
        The date of the experiment
    growth_irradiance : int
        The growth irradiance in µmol photons m-2 s-1
    measurement_irradiance : int
        The measurement irradiance in µmol photons m-2 s-1
    growth_phase : int
        The number of the growth phase (1 or 2)
    '''
    split_file_name = file_name.split(" ")
    
    growth_irradiance = int(split_file_name[0])

    measurement_irradiance_str = split_file_name[1]
    if measurement_irradiance_str == "invivo":
        measurement_irradiance = 100
    elif measurement_irradiance_str == "max":
        measurement_irradiance = 3000
    else:
        raise ValueError(f"Invalid measurement irradiance: {measurement_irradiance_str}")
    
    growth_phase = int(split_file_name[2][1])

    expreriment_date = split_file_name[3]

    return expreriment_date, growth_irradiance, measurement_irradiance, growth_phase


def add_to_lists(file_names, file_name,
                 expreriment_dates, expreriment_date,
                 growth_irradiances, growth_irradiance,
                 measurement_irradiances, measurement_irradiance,
                 growth_phases, growth_phase,
                 chanels, channel,
                 reaction_rates, reaction_rate,
                 intercepts, intercept,
                 r_values, r_value,
                 p_values, p_value,
                 std_errs, std_err,
                 is_in_lights, is_in_light):
    '''
    Description
    ------------
    Add the values to all the lists

    Parameters
    ----------
    file_names : list
        The list of file names
    file_name : str
        The file name to add to the list
    expreriment_dates : list
        The list of experiment dates
    expreriment_date : str
        The experiment date to add to the list
    growth_irradiances : list
        The list of growth irradiances
    growth_irradiance : int
        The growth irradiance to add to the list
    measurement_irradiances : list
        The list of measurement irradiances
    measurement_irradiance : int
        The measurement irradiance to add to the list
    growth_phases : list
        The list of growth phases
    growth_phase : int
        The growth phase to add to the list
    chanels : list
        The list of channels
    channel : int
        The channel to add to the list
    reaction_rates : list
        The list of reaction rates
    reaction_rate : float
        The reaction rate to add to the list
    intercepts : list
        The list of intercepts
    intercept : float
        The intercept to add to the list
    r_values : list
        The list of r values
    r_value : float
        The r value to add to the list
    p_values : list
        The list of p values
    p_value : float
        The p value to add to the list
    std_errs : list
        The list of std_errs
    std_err : float
        The std_err to add to the list

    Returns
    -------
    None
    '''
    file_names.append(file_name)
    expreriment_dates.append(expreriment_date)
    growth_irradiances.append(growth_irradiance)
    measurement_irradiances.append(measurement_irradiance)
    growth_phases.append(growth_phase)
    chanels.append(channel)
    reaction_rates.append(reaction_rate)
    intercepts.append(intercept)
    r_values.append(r_value)
    p_values.append(p_value)
    std_errs.append(std_err)
    is_in_lights.append(is_in_light)
    

def get_reaction_rates_df(merged_data):
    '''
    Description
    ------------
    Calculate the reaction rates for each file. The first minute of measurement is done is light and the last 3 minutes are done in the dark

    Parameters
    ----------
    merged_data : pandas.DataFrame
        The flattened dataframe containing the data from all files, indexed by file_name
    
    Returns
    -------
    reaction_rates : pandas.DataFrame
        The dataframe containing the reaction rates for each file
    '''
    # Get the file names
    unique_file_names = merged_data.index.unique()

    # Initialize lists to store the data
    file_names = []
    expreriment_dates = []
    growth_irradiances = []
    measurement_irradiances = []
    growth_phases = []
    chanels = []
    reaction_rates = []
    intercepts = []
    r_values = []
    p_values = []
    std_errs = []
    is_in_lights = []

    # Calculate the reaction rates for each file in light and dark
    for file_name in unique_file_names:
        file_data = merged_data.xs(file_name)

        # Get the unique channels - as they need to have their own reaction rate entry
        unique_channels = file_data["channel"].unique()

        #get the experiment conditions from the file name
        expreriment_date, growth_irradiance, measurement_irradiance, growth_phase = get_exp_conditions_from_file_name(file_name)

        # Itarate over them as well
        for channel in unique_channels:
            channel_data = file_data[file_data["channel"] == channel]

            # Get the data between 10 and 50 seconds
            light_data = channel_data[(channel_data["elapsed_time(s)"] >= 10) & (channel_data["elapsed_time(s)"] <= 50)]
            # Get the data between 70 and 230 seconds
            dark_data = channel_data[(channel_data["elapsed_time(s)"] >= 70) & (channel_data["elapsed_time(s)"] <= 230)]

            # Get the light phase data
            slope_light, intercept_light, r_value_light, p_value_light, std_err_light = scipy.stats.linregress(list(light_data["elapsed_time(s)"]), list(light_data["[O2]"]))
            # Get the dark phase data
            slope_dark, intercept_dark, r_value_dark, p_value_dark, std_err_dark = scipy.stats.linregress(list(dark_data["elapsed_time(s)"]), list(dark_data["[O2]"]))

            # Append the data to the lists - first row row light, second row for dark
            add_to_lists(file_names, file_name,
                         expreriment_dates, expreriment_date,
                         growth_irradiances, growth_irradiance,
                         measurement_irradiances, measurement_irradiance,
                         growth_phases, growth_phase,
                         chanels, channel,
                         reaction_rates, slope_light,
                         intercepts, intercept_light,
                         r_values, r_value_light,
                         p_values, p_value_light,
                         std_errs, std_err_light,
                         is_in_lights, "Yes")
            
            add_to_lists(file_names, file_name,
                         expreriment_dates, expreriment_date,
                         growth_irradiances, growth_irradiance,
                         measurement_irradiances, measurement_irradiance,
                         growth_phases, growth_phase,
                         chanels, channel,
                         reaction_rates, slope_dark,
                         intercepts, intercept_dark,
                         r_values, r_value_dark,
                         p_values, p_value_dark,
                         std_errs, std_err_dark,
                         is_in_lights, "No")


    reaction_rates_df = pd.DataFrame({ "file_name": file_names, "date": expreriment_dates, "is_in_light": is_in_lights, "growth_phase": growth_phases,
                                    "growth_irradiance": growth_irradiances, "measurement_irradiance": measurement_irradiances,
                                    "chanel": chanels, "reaction_rate": reaction_rates, "intercept": intercepts,
                                    "r_value": r_values, "p_value": p_values, "std_err": std_errs })
    
    return reaction_rates_df


def make_single_exp_plots(times, oxygen_concentrations, reaction_rate_row ,title, save_dir):
    '''
    Plot the data

    Parameters
    ----------
    times : array-like
        The time data in seconds
    oxygen_concentrations : array-like
        The oxygen concentration data in µM
    reaction_rate_row : pandas.Series
        The relevant row from the reaction rates dataframe
    title : str
        The title of the plot
    save_dir : str
        The directory to save the plot to
    
    Returns
    -------
    None
    '''
    fig, ax = plt.subplots()
    ax.scatter(times, oxygen_concentrations)
    ax.set_xlabel("Elapsed Time (s)")
    ax.set_ylabel("$[O_{2}] µmol$")
    ax.set_title(title)
    
    # Remove ticks from Y axis
    ax.yaxis.set_ticks_position('none')
    # Remove ticks from X axis top
    ax.xaxis.set_ticks_position('bottom')
        
    plt.savefig(f"{save_dir}/{title}.png")
    plt.close("all")


def add_growth_iriadiance_measurement_irradiance_column(reaction_rates):
    '''
    Description
    ------------
    Add a column to the reaction rates dataframe containing the measurement irradiance saparated by comma from the growth irradiance

    Parameters
    ----------
    reaction_rates : pandas.DataFrame
        The dataframe containing the reaction rates

    Returns
    -------
    reaction_rates : pandas.DataFrame
        The dataframe containing the reaction rates with the added column
    '''
    reaction_rates["growth_iriadiance_measurement_irradiance"] = "g" + reaction_rates["growth_irradiance"].astype(str) + ",m" + reaction_rates["measurement_irradiance"].astype(str) + "  "
    return reaction_rates


def make_reaction_rate_plots(reaction_rates, save_dir):
    '''
    Plot the reaction rates and save to files
    
    Parameters
    ----------
    reaction_rates : pandas.DataFrame
        The dataframe containing the reaction rates
    save_dir : str
        The directory to save the plot to

    Returns
    -------
    None   
    '''
    reaction_rates_for_graphs = add_growth_iriadiance_measurement_irradiance_column(reaction_rates)
    clrs = ["#B2F0E8", "#117C6F"]

    phase_1_data = reaction_rates_for_graphs[reaction_rates_for_graphs["growth_phase"] == 1]

    # Make the box plot for phase 1 reaction rates
    fig, ax = plt.subplots(figsize=(12, 10))
    fig.suptitle("Reaction Rates for phase 1 smaples", fontsize=20)
    sns.boxplot(x="growth_iriadiance_measurement_irradiance", y="reaction_rate", hue="is_in_light", data=phase_1_data, ax=ax, palette=clrs)

    ax.set_xlabel(r"Growth Irradiance, Measurement Irradiance (photons $\frac{%s}{%s}$)" % ("µmol", "m^2s"))
    ax.set_ylabel(r"Reaction Rate (Δ$[O_{2}]$ $\frac{%s}{%s}$)" % ("µmol", "s"))
    plt.savefig(f"{save_dir}/reaction_rates_phase_1.png")
    plt.close("all")


    # Get all the phase 2 data
    phase_2_data = reaction_rates_for_graphs[reaction_rates_for_graphs["growth_phase"] == 2]

    # Make the box plot for phase 2 reaction rates
    fig, ax = plt.subplots(figsize=(12, 10))
    fig.suptitle("Reaction Rates for phase 2 smaples", fontsize=20)
    sns.boxplot(x="growth_iriadiance_measurement_irradiance", y="reaction_rate", hue="is_in_light", data=phase_2_data, ax=ax, palette=clrs)

    ax.set_xlabel(r"Growth Irradiance, Measurement Irradiance (photons $\frac{%s}{%s}$)" % ("µmol", "m^2s"))
    ax.set_ylabel(r"Reaction Rate (Δ$[O_{2}]$ $\frac{%s}{%s}$)" % ("µmol", "s"))
    plt.savefig(f"{save_dir}/reaction_rates_phase_2.png")
    plt.close("all")


def create_directory(parent_directory, nested_directory_name):
    '''
    Description
    -----------
    Create a directory if it does not exist
    
    Parameters
    ----------
    parent_directory : str
        The path to the directory under which the new directory will be created
    nested_directory_name : str
        The name of the nested directory to be created
    '''
    # Create the output directory path
    new_dir_path = os.path.join(parent_directory, nested_directory_name)
    # Create the directory if it does not exist
    if not os.path.isdir(new_dir_path):
        os.mkdir(new_dir_path)
    return new_dir_path


if __name__ == "__main__":
    main()
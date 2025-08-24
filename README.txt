Tested in python 3.11 for linux and windows. Written by Carmi Yeffet.

Environment setup:
Python v 3.11, with the following packages in the environment:
    * scipy
    * pandas
    * matplotlib
    * seaborn
Also, make sure your python distribuition comes with argparse. It should come installed.

Running the analysis:
Activate the created environment, move to the program folder and run the following command:
python main.py -p {/Data/fire_sting/in} -o {/Data/fire_sting/out}
(As an example, on my machine the values of the flags were : -p C:/Data/fire_sting/in -o C:/Data/fire_sting/out)

Output:
The extracted data, now in an easy to work with format is saved directly to the output path provided.
Oxygen_data.csv contains the raw data while reaction rates contains the reaction rates as calculated.

Figures are saved into a program-created subdirectory called 'graphs', nested in the output folder.
For each input file a scatter plot with the oxygen concentration at time t is plotted.
Second, two figures for the two growth phases reaction rates, for easy comparison.
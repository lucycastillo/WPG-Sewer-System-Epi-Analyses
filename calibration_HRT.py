
import pandas as pd
import networkx as nx
import numpy as np
import shutil
import swmmio
from pyswmm import Simulation, Links, Nodes, Subcatchments
from swmmio import Model
from swmmio.utils.modify_model import replace_inp_section
from calibration_HRT_utils import calculate_HRT, calibrate_HRT, create_graph, replace_inp_section

# inp_file_path = 'HRT_calibration_files/wpg_cm.inp'
inp_file_path = 'HRT_calibration_files/wpg_concp.inp'

# Read the CSV file
# median_sc_df = pd.read_csv("HRT_calibration_files/iw-Subcat-HRT.csv")
median_sc_df = pd.read_csv("HRT_calibration_files/update_iw-Subcat-HRT.csv")

# Format df
med_sc_df = median_sc_df.drop(median_sc_df.columns[0:1], axis=1)
# drop_scs = ['sc_1', 'sc_10', 'sc_8']
# drop_scs = ['sc_13', 'sc_16', 'sc_20']
# filtered_med_scs = med_sc_df[~med_sc_df['sc.id'].isin(drop_scs)]
# print(filtered_med_scs)
filtered_med_scs = median_sc_df

# Initialize variables to store values and correct target hrts
sc_5_hrt = None
sc_8_hrt = None
sc_13_hrt = None
sc_2_hrt = None
sc_21_hrt = None

# Loop to get the HRT values
for index, row in filtered_med_scs.iterrows():
    if row['sc.id'] == 'sc_5':
        sc_5_hrt = row['sc_median_hrt']
    elif row['sc.id'] == 'sc_8':
        sc_8_hrt = row['sc_median_hrt']
    elif row['sc.id'] == 'sc_13':
        sc_13_hrt = row['sc_median_hrt']
    elif row['sc.id'] == 'sc_2':
        sc_2_hrt = row['sc_median_hrt']
    elif row['sc.id'] == 'sc_21':
        sc_21_hrt = row['sc_median_hrt']


# loop to update the HRT values for sc_4 and sc_0 based on sc_20 and sc_16
for index, row in filtered_med_scs.iterrows():
    if row['sc.id'] == 'sc_14' and sc_5_hrt is not None:
        filtered_med_scs.at[index, 'sc_median_hrt'] = sc_5_hrt + 0.25
    elif row['sc.id'] == 'sc_4' and sc_8_hrt is not None:
        filtered_med_scs.at[index, 'sc_median_hrt'] = sc_8_hrt + 0.25
    elif row['sc.id'] == 'sc_6' and sc_13_hrt is not None:
        filtered_med_scs.at[index, 'sc_median_hrt'] = sc_13_hrt + 0.25
    elif row['sc.id'] == 'sc_11' and sc_2_hrt is not None:
        filtered_med_scs.at[index, 'sc_median_hrt'] = sc_2_hrt + 0.25
    elif row['sc.id'] == 'sc_3' and sc_21_hrt is not None:
        filtered_med_scs.at[index, 'sc_median_hrt'] = sc_21_hrt + 0.25
    elif row['sc.id'] == 'sc_18' and sc_21_hrt is not None:
        filtered_med_scs.at[index, 'sc_median_hrt'] = sc_21_hrt + 0.25


# Initialize empty df
cond_df = pd.DataFrame(columns = ["cond_name", "mean_flow", "mean_depth"])

# Run simulation and loop through conduits
with Simulation(inp_file_path) as sim:
    link_obj = Links(sim)
    conduit_data = {f"ct_{num}": {'flows': [], 'depths': []} for num in range(0, 22)}
    
    for step in sim:
        for num in range(0, 22):
            cond_name = f"ct_{num}"
            curr = link_obj[cond_name]
            # Append flows and depths to conduit_data
            conduit_data[cond_name]['flows'].append(curr.flow)
            conduit_data[cond_name]['depths'].append(curr.depth)

# Calculate mean flow and depth for each conduit
for cond_name, data in conduit_data.items():
    # loop through conduit_data and calculate mean depth and flow rate
    mean_flow = sum(data['flows']) / len(data['flows']) if data['flows'] else 0
    mean_depth = sum(data['depths']) / len(data['depths']) if data['depths'] else 0
    
    # Append the results to the main df
    cond_df = pd.concat([cond_df, pd.DataFrame({"cond_name": [cond_name], "mean_flow": [mean_flow], "mean_depth": [mean_depth]})], ignore_index=True)

# Extract link properties from .inp file
m = Model(inp_file_path)
cond_summary = m.links.dataframe[['InletNode', 'OutletNode', 'Length']]
cond_summary.rename(columns={'InletNode': 'Inlet_Node', 'OutletNode': 'Outlet_Node', 'Length': 'cond_length'}, inplace=True)

# Merge to main df
cond_df_merged = pd.merge(cond_df, cond_summary, left_on='cond_name', right_on='Name', how='left')

# Call function from utils
HRT = calculate_HRT(cond_df_merged)

# Merge HRT results to main df
merged_df = pd.concat([cond_df_merged, HRT], axis = 1)
merged_df.set_index(['cond_name', 'Inlet_Node', 'Outlet_Node'], inplace = True)
print(merged_df)

# Define outfalls and calculate current path hrts
outfalls = ['node_4', 'node_24', 'node_14']
new_df = merged_df.reset_index()
path_hrt_df = create_graph(new_df, merged_df, inp_file_path, outfalls)
path_hrt_df['Total_HRT'] = pd.to_numeric(path_hrt_df['Total_HRT'], errors='coerce')

# check if 'Subcatchments' column exists
if 'Subcatchments' not in path_hrt_df.columns:
    path_hrt_df['Subcatchments'] = ''

# Run simulation to extract sc names
with Simulation(inp_file_path) as sim:
    for index, row in path_hrt_df.iterrows():
        sc_name = f"sc_{index}"
        curr = Subcatchments(sim)[sc_name]
        outlet_node = curr.connection
        matching_rows = path_hrt_df[path_hrt_df['Start_Node'] == outlet_node]

        for matching_index in matching_rows.index:
            if pd.notna(path_hrt_df.at[matching_index, 'Subcatchments']):
                path_hrt_df.at[matching_index, 'Subcatchments'] += f"{sc_name}"
            else:
                path_hrt_df.at[matching_index, 'Subcatchments'] = sc_name

# Manual assignments because the simulation method didn't work for these?
manual_assignments = {
    'node_15': 'sc_14',
    'node_18': 'sc_15',
    'node_3': 'sc_16',
    'node_21': 'sc_17',
    'node_10': 'sc_18',
    'node_0': 'sc_19',
    'node_13': 'sc_20',
    'node_17': 'sc_21',
}

# Manual assignment
for node, sc_name in manual_assignments.items():
    path_hrt_df.loc[path_hrt_df['Start_Node'] == node, 'Subcatchments'] = sc_name

# Add WWTP column based on nearest outfall
for index, row in path_hrt_df.iterrows():
    if row['End_Node'] == 'node_4':
        path_hrt_df.loc[index, 'WWTP'] = 'North'

    elif row['End_Node'] == 'node_14':
        path_hrt_df.loc[index, 'WWTP'] = 'South'
    
    else:
        path_hrt_df.loc[index, 'WWTP'] = 'West'

print(path_hrt_df)
subcatchments_data = path_hrt_df[['Start_Node', 'Subcatchments']].copy()
north_df = path_hrt_df[path_hrt_df['WWTP'] == 'North'].sort_values(by='Total_HRT', ascending=True)
south_df = path_hrt_df[path_hrt_df['WWTP'] == 'South'].sort_values(by='Total_HRT', ascending=True)
west_df = path_hrt_df[path_hrt_df['WWTP'] == 'West'].sort_values(by='Total_HRT', ascending=True)

# Ensure values are numeric and format df before calibration
path_hrt_df['Total_HRT'] = pd.to_numeric(path_hrt_df['Total_HRT'], errors='coerce')
new_df = merged_df.reset_index()


# # Initialize progress_tracker 
progress_tracker = None

# tolerance = 0.5
# iteration_counter = 0

# Initialize progress tracker before the loop
# progress_tracker = {wwtp: 0 for wwtp in path_hrt_df['WWTP'].unique()}

# Sort the DataFrames by WWTP and Total_HRT (done once before the loop)
# south_df = path_hrt_df[path_hrt_df['WWTP'] == 'South'].sort_values(by='Total_HRT', ascending=True)
# west_df = path_hrt_df[path_hrt_df['WWTP'] == 'West'].sort_values(by='Total_HRT', ascending=True)
# north_df = path_hrt_df[path_hrt_df['WWTP'] == 'North'].sort_values(by='Total_HRT', ascending=True)

# for iteration_counter in range(3):
#     print(f"Iteration {iteration_counter}:")
#     print("Path HRT before calibration:")
#     print(path_hrt_df[['Total_HRT', 'Subcatchments', 'WWTP']])

#     Process each WWTP one at a time
#     for wwtp, wwtp_df in [('South', south_df), ('West', west_df), ('North', north_df)]:
#         updated_df, updated_tot_hrt, progress_tracker = calibrate_HRT(new_df, wwtp_df, filtered_med_scs, progress_tracker)

#         Update the DataFrame after calibration
#         updated_df.set_index(['cond_name', 'Inlet_Node', 'Outlet_Node'], inplace=True)
#         df = updated_df.reset_index()

#         print(f"Updated conduit summary after calibration for {wwtp}:")
#         print(updated_df)

#         Calculate all path HRTs again using the updated data
#         print("Calculating all path HRTs again")
#         updated_tot_hrt = create_graph(df, updated_df, inp_file_path, outfalls)
        
#         print("Updated Total HRT df after create graph")
#         print(updated_tot_hrt)

#         Merge subcatchments_data to updated_tot_hrt
#         updated_tot_hrt = pd.merge(updated_tot_hrt, subcatchments_data, on='Start_Node', how='left')
#         print("Updated total HRT df:")
#         print(updated_tot_hrt)

#         Update the WWTPs in the DataFrame based on End_Node
#         for index, row in updated_tot_hrt.iterrows():
#             if row['End_Node'] == 'node_3':
#                 updated_tot_hrt.loc[index, 'WWTP'] = 'North'
#             elif row['End_Node'] == 'node_12':
#                 updated_tot_hrt.loc[index, 'WWTP'] = 'South'
#             else:
#                 updated_tot_hrt.loc[index, 'WWTP'] = 'West'

#         print(f"Updated Total HRT df for {wwtp}:")
#         print(updated_tot_hrt[['Subcatchments', 'Total_HRT']])

#         Update the main DataFrame with the updated results for this WWTP
#         path_hrt_df.update(updated_tot_hrt)
#         print("what this looks like")
#         print(path_hrt_df)

#         Check if calibration is done for this WWTP by comparing to tolerance
#         if all(abs(updated_tot_hrt['Total_HRT'].values - filtered_med_scs['sc_median_hrt'].values[:len(updated_tot_hrt)]) <= tolerance):
#             print(f"{wwtp} Calibration done for this WWTP.")
#             progress_tracker[wwtp] = len(wwtp_df)  # Mark this WWTP as fully calibrated

#     Break the loop if all WWTPs are calibrated
#     if all(progress_tracker[wwtp] == len(path_hrt_df[path_hrt_df['WWTP'] == wwtp]) for wwtp in progress_tracker):
#         print("All WWTPs have been calibrated.")
#         break

#     Update variables for the next iteration
#     new_df = updated_df.reset_index()
#     print("Calibrating again.")


tolerance = 0.5
# Initialize progress tracker before the loop
progress_tracker = {wwtp: 0 for wwtp in path_hrt_df['WWTP'].unique()}

for iteration_counter in range(22):
    print(f"Iteration {iteration_counter}:")
    print("Path HRT before calibration:")
    print(path_hrt_df[['Total_HRT', 'Subcatchments', 'WWTP']])

    # Calibrate HRT for the current WWTP (one row at a time)
    updated_df, updated_tot_hrt, progress_tracker = calibrate_HRT(new_df, path_hrt_df, filtered_med_scs, progress_tracker)
    
    # Update the DataFrame after calibration
    updated_df.set_index(['cond_name', 'Inlet_Node', 'Outlet_Node'], inplace=True)
    df = updated_df.reset_index()

    print("Updated conduit summary after calibration:")
    print(updated_df)

    # Calculate all path HRTs again using the updated data
    print("Calculating all path HRTs again")
    updated_tot_hrt = create_graph(df, updated_df, inp_file_path, outfalls)
    
    print("Updated Total HRT df after create graph")
    print(updated_tot_hrt)

    # Merge subcatchments_data to updated_tot_hrt
    updated_tot_hrt = pd.merge(updated_tot_hrt, subcatchments_data, on='Start_Node', how='left')
    print("Updated total HRT df:")
    print(updated_tot_hrt)

    # Update the WWTPs in the DataFrame based on End_Node
    for index, row in updated_tot_hrt.iterrows():
        if row['End_Node'] == 'node_4':
            updated_tot_hrt.loc[index, 'WWTP'] = 'North'
        elif row['End_Node'] == 'node_14':
            updated_tot_hrt.loc[index, 'WWTP'] = 'South'
        else:
            updated_tot_hrt.loc[index, 'WWTP'] = 'West'

    print("Updated Total HRT df")
    print(updated_tot_hrt[['Subcatchments', 'Total_HRT']])

    # Check if calibration is done by comparing to tolerance
    if all(abs(updated_tot_hrt['Total_HRT'].values - filtered_med_scs['sc_median_hrt'].values[:len(updated_tot_hrt)]) <= tolerance):
        print("Calibration done.")
        break

    # Update variables for the next iteration
    path_hrt_df = updated_tot_hrt
    new_df = updated_df.reset_index()
    print("Calibrating again.")


# Paths
copied_inp_file_path = 'copy_wpg_cm.inp'

# Step 1: Create a copy of the original .inp file
shutil.copy(inp_file_path, copied_inp_file_path)

# Load the copied .inp file
model = swmmio.Model(copied_inp_file_path)

# Extract the conduit section
conduits_df = model.inp.conduits

# Ensure updated_df is correctly aligned and rename column to match
updated_df = updated_df.rename(columns={'cond_length': 'Length'})  # Rename column
updated_df = updated_df.reset_index()  # Reset index to ensure correct alignment
updated_df.set_index('cond_name', inplace=True)  # Set index as 'cond_name'

# Check conduits_df structure
print("Conduits DataFrame columns:", conduits_df.columns)
print("Updated DataFrame head:", updated_df.head())

# Loop through updated_df and update the conduit lengths
for cond_name, row in updated_df.iterrows():
    if cond_name in conduits_df.index:
        if 'Length' in row:
            conduits_df.at[cond_name, 'Length'] = row['Length']
        else:
            print(f"Column 'Length' not found in row: {row}")

# Replace the Conduits section in the copied .inp file
replace_inp_section(copied_inp_file_path, conduits_df, 'CONDUITS')
print(conduits_df)
print(updated_df)
   

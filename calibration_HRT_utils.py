import numpy as np
import pandas as pd
import networkx as nx
import swmmio
from pyswmm import Simulation, Nodes
from swmmio import Model

# from pyswmm import Simulation, Nodes

def calculate_HRT(conduit_summary):
    radius = 1.5

    theta_df = pd.Series(index = conduit_summary.index, dtype = float)
    flow_area_df = pd.Series(index = conduit_summary.index, dtype = float)
    flow_volume_df = pd.Series(index = conduit_summary.index, dtype = float)
    HRT_df = pd.Series(index = conduit_summary.index, dtype = float)
    
    for index, row in conduit_summary.iterrows():
        try:
            theta_df.loc[index] = 2*np.arccos(((radius - (conduit_summary['mean_depth'][index]))) / radius)
            
            flow_area_df.loc[index] = (radius**2 * (theta_df.loc[index] - np.sin(theta_df.loc[index]))) / 2
    
            flow_volume_df.loc[index] = flow_area_df.loc[index] * (conduit_summary['cond_length'][index])

            HRT_df.loc[index] = (flow_volume_df.loc[index] / conduit_summary['mean_flow'][index]) / 3600

        except Exception as e:
            print(f"An error occured at index {index}: {e}")

        continue
    HRT = pd.DataFrame(HRT_df, columns= ['Conduit HRT (HRS)'])
    # theta = pd.DataFrame(theta_df, columns= ['Theta Values'])
    # flow_area = pd.DataFrame(flow_area_df, columns=['Flow Area'])
    # flow_vol = pd.DataFrame(flow_volume_df, columns=['flow volume'])
    # print(theta)
    # print(flow_area)
    # print(flow_vol)

    return HRT

def create_graph(conduit_summary, new_df, inp_file_path, outfalls):

    G = nx.DiGraph()
    results = []

    with Simulation(inp_file_path) as sim:
        nodes = Nodes(sim)
        for node in nodes:
                G.add_node(node.nodeid)

        # Add conduits to the graph with lengths as weights
    for index, row in conduit_summary.iterrows():
        G.add_edge(row['Inlet_Node'], row['Outlet_Node'], weight=row['cond_length'])

    for node in G.nodes:
        for outfall in outfalls:
            if node != outfall:
                try:
                    # maybe should be in main
                    shortest_path = nx.dijkstra_path(G, node, outfall, weight='weight')
                    path_hrt = calculate_path_HRT(new_df, shortest_path)
                    results.append({
                        'Start_Node': node,
                        'End_Node': outfall,
                        'Path': shortest_path,
                        'Total_HRT': path_hrt,
                    })
                except nx.NetworkXNoPath:
                    continue
    
    results_df = pd.DataFrame(results)
    return results_df

def calculate_path_HRT(conduit_summary, shortest_path):

    conduit_dict = conduit_summary['Conduit HRT (HRS)']. to_dict()
    total_hrt = 0
    keys = [key for key in conduit_dict if (key[1] in shortest_path and key[2] in shortest_path)]
        
    for key in keys:
        hrt_value = conduit_dict[key]
        total_hrt += hrt_value

    return total_hrt

def calibrate_HRT(conduit_summary, Total_HRT_df, median_HRT_df, progress_tracker=None):

    if progress_tracker is None:
        progress_tracker = {wwtp: 0 for wwtp in Total_HRT_df['WWTP'].unique()}
    
    updated_conduit_summary = conduit_summary.copy()
    updated_tot_HRT_df = Total_HRT_df.copy()
    conduit_summary['cond_length'] = conduit_summary['cond_length'].astype(float)

    if 'Subcatchments' not in updated_tot_HRT_df.columns:
        raise KeyError("Col subcatchments not found")
    
    if 'WWTP' not in updated_tot_HRT_df.columns:
        print("Columns 'WWTP' not found. Skipping WWTP-based processing")
        print("Calibration complete")
        return updated_conduit_summary, updated_tot_HRT_df

    # Initialize dictionary to track sorting status and save sorting order
    wwtps = updated_tot_HRT_df['WWTP'].unique()
    sorting_status = {wwtp: False for wwtp in wwtps}
    saved_sorting_order = {wwtp: None for wwtp in wwtps}
    calibration_status = {wwtp: 'Not Calibrated' for wwtp in wwtps}

    for wwtp in wwtps:
        if calibration_status[wwtp] == 'Not Calibrated':
            if not sorting_status[wwtp]:
                # Sort by 'Total_HRT' in ascending order
                wwtp_df = updated_tot_HRT_df[updated_tot_HRT_df['WWTP'] == wwtp].sort_values(by='Total_HRT', ascending=True)
                # Save the order of indices
                saved_sorting_order[wwtp] = wwtp_df.index.tolist()
                sorting_status[wwtp] = True  # Mark as sorted
                print("THIS IS SORTING STATUS")
                print(sorting_status[wwtp])
                print("THIS IS SAVED SORTING ORDER")
                print(saved_sorting_order[wwtp])
            else:
                # Use the saved sorting order
                wwtp_df = updated_tot_HRT_df.loc[saved_sorting_order[wwtp]]
                print("THIS IS WWTP DF")
                print(wwtp_df)

            start_index = progress_tracker[wwtp]

            if start_index < len(wwtp_df):
                row = wwtp_df.iloc[start_index]
                print(f"Processing row {start_index} for WWTP: {wwtp}")

                if pd.isna(row['Subcatchments']):
                    print(f"Skipping row {start_index} due to NaN in subcatchments")
                    start_index += 1
                    progress_tracker[wwtp] = start_index
                    return updated_conduit_summary, updated_tot_HRT_df, progress_tracker
                else:
                    subs = row['Subcatchments']
                    if subs in median_HRT_df['sc.id'].values:
                        median_row = median_HRT_df[median_HRT_df['sc.id'] == subs].iloc[0]
                        final_path_hrt = median_row['sc_median_hrt']
                        start_node = row['Start_Node']
                        print(f"Final path HRT for {subs}: {final_path_hrt}")
                        row_processed = False

                        for j, conduit_row in updated_conduit_summary.iterrows():
                            inlet_node = conduit_row['Inlet_Node']
                            if inlet_node == start_node:
                                curr_cond_length = conduit_row['cond_length']
                                curr_mean_flow = conduit_row['mean_flow']
                                curr_mean_depth = conduit_row['mean_depth']
                                curr_cond_hrt = conduit_row['Conduit HRT (HRS)']
                                tot_path_hrt = row['Total_HRT']
                                print(f"Current conduit length: {curr_cond_length}")
                                print(f"Current HRT: {curr_cond_hrt}")
                                print(f"current path HRT = {tot_path_hrt}")

                                updated_conduit_summary, updated_tot_HRT_df = find_x(
                                    updated_conduit_summary, updated_tot_HRT_df, final_path_hrt, 
                                    curr_mean_flow, curr_mean_depth, tot_path_hrt, 
                                    curr_cond_hrt, curr_cond_length, start_node
                                )
                                print(f"Updated conduit summary and total HRT df")
                                print(updated_tot_HRT_df.loc[updated_tot_HRT_df['Start_Node'] == start_node])
                                row_processed = True
                                break

                        if row_processed:
                            progress_tracker[wwtp] = start_index + 1
                            if progress_tracker[wwtp] >= len(wwtp_df):
                                print(f"{wwtp} WWTP is fully calibrated")
                                calibration_status[wwtp] = 'Calibrated'
                            return updated_conduit_summary, updated_tot_HRT_df, progress_tracker
                        else:
                            print(f"No matching conduit found for row {start_index}")
                            return updated_conduit_summary, updated_tot_HRT_df, progress_tracker
                    else:
                        progress_tracker[wwtp] = start_index + 1
                        return updated_conduit_summary, updated_tot_HRT_df, progress_tracker
    return updated_conduit_summary, updated_tot_HRT_df, progress_tracker
                  
def find_x(conduit_summary, Total_HRT_df, final_path_hrt, curr_mean_flow, curr_mean_depth, tot_path_hrt, curr_cond_hrt, curr_cond_length, start_node):
    
    updated_conduit_summary = conduit_summary.copy()
    updated_tot_HRT_df = Total_HRT_df.copy()
    radius = 1.5   
    print('Columns in Total_HRT_DF before update:', updated_tot_HRT_df.columns)

    if tot_path_hrt > final_path_hrt:
        target_hrt = (final_path_hrt) - (tot_path_hrt - curr_cond_hrt)
        theta = 2*np.arccos((radius - curr_mean_depth) / radius)
        flow_area = (radius**2 * (theta - np.sin(theta))) / 2

        flow_vol = target_hrt*3600*curr_mean_flow 
        new_length = (flow_vol/flow_area)
        new_v = curr_mean_flow/flow_area
                    
        print(f"new conduit flow velocity assuming depth remains the same :{new_v} ")
        print(f"new length = {new_length}")
        updated_cond_summary, updated_Tot_df = update_conduit_length(updated_conduit_summary, updated_tot_HRT_df, new_length, curr_cond_length, target_hrt, final_path_hrt, start_node)
        print("Columns in updated_tot_HRT_df after update:", updated_tot_HRT_df.columns)

    else:
        target_hrt = (final_path_hrt) - (tot_path_hrt- curr_cond_hrt)
        theta = 2*np.arccos(((radius - (curr_mean_depth))) / radius)
        flow_area = (radius**2 * (theta - np.sin(theta))) / 2

        # if target_hrt > 0:
        flow_vol = target_hrt*3600*curr_mean_flow 
        new_length = (flow_vol/flow_area)
        new_v = curr_mean_flow/flow_area
                    
        print(f"new conduit flow velocity assuming depth remains the same :{new_v} ")
        print(f"new length = {new_length}")
        updated_cond_summary, updated_Tot_df = update_conduit_length(updated_conduit_summary, updated_tot_HRT_df, new_length, curr_cond_length, target_hrt, final_path_hrt, start_node)
        print("Columns in updated_tot_HRT_df after update:", updated_tot_HRT_df.columns)

    return updated_cond_summary, updated_Tot_df

def update_conduit_length(conduit_summary, Total_HRT_df, new_length, curr_cond_length, target_hrt, final_path_hrt, start_node):
    updated_conduit_summary = conduit_summary.copy()
    updated_tot_HRT_df = Total_HRT_df.copy()
    updated = False 
    for index, row in updated_conduit_summary.iterrows():

        if curr_cond_length == updated_conduit_summary.at[index, 'cond_length']:
            updated_conduit_summary.loc[index, 'cond_length'] = new_length
            inlet_node = updated_conduit_summary.at[index, 'Inlet_Node']

            if inlet_node == start_node:
                updated_conduit_summary.at[index, 'Conduit HRT (HRS)'] = target_hrt
                updated_tot_HRT_df.at[index, 'Total_HRT'] = final_path_hrt
                print(f'Updated length of conduit, from {curr_cond_length} to new length of: {new_length}')
                updated = True
                break
        
    if not updated:
        print(f"Warning: No update perofrm for conduit with length : {curr_cond_length}")
                
    return updated_conduit_summary, updated_tot_HRT_df

def replace_inp_section(inp_file_path, conduits_df, section_name):
    # Load the model
    model = swmmio.Model(inp_file_path)
    
    # Get the existing section
    section = getattr(model.inp, section_name.lower())
    
    # Ensure section is a DataFrame
    if not isinstance(section, pd.DataFrame):
        raise TypeError(f"The section '{section_name}' is not a DataFrame.")
    
    # Print existing section for debugging
    print(f"Existing section columns: {section.columns}")
    print(f"Existing section head:\n{section.head()}")
    
    # Convert the DataFrame to the format required by swmmio
    new_section = section.copy()
    
    # Print columns of new_section
    print(f"New section columns before update: {new_section.columns}")
    
    for index, row in conduits_df.iterrows():
        if index in new_section.index:
            if 'Length' in row:
                new_section.at[index, 'Length'] = row['Length']
            else:
                print(f"Column 'Length' not found in row: {row}")
    
    # Print new_section to check if it has been updated
    print(f"New section after updates:\n{new_section.head()}")
    
    # Update the model's section with the new data
    setattr(model.inp, section_name.lower(), new_section)
    
    # Save the updated model to a new file
    new_file_path = inp_file_path.replace('.inp', '_updated.inp')
    model.inp.save(new_file_path)
    print(f"Updated model saved to {new_file_path}")

# import os
# import shutil
import numpy as np
import pandas as pd
import networkx as nx
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
            # index = 0

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
                        'Total_HRT': path_hrt
                    })
                except nx.NetworkXNoPath:
                    continue
    
    results_df = pd.DataFrame(results)
    return results_df

def calculate_path_HRT(conduit_summary, shortest_path):
# add create path and conduit_dict in this function
# conduit dict is wrong
    conduit_dict = conduit_summary['Conduit HRT (HRS)']. to_dict()
    total_hrt = 0
    # conduit dict is different
    keys = [key for key in conduit_dict if (key[1] in shortest_path and key[2] in shortest_path)]
        
    for key in keys:
        hrt_value = conduit_dict[key]
        total_hrt += hrt_value

    return total_hrt

def calibrate_HRT(conduit_summary, Total_HRT_df, median_HRT_df):
        # why does this iterate only once
        # upstream to downstream
        # change cond length of first
        # use value for each subcatchment
        # interquartile range half an hour
        # calculate HRT again and recalibrate if necessary

        subs = Total_HRT_df['Subcatchments']
        tot_hrt = Total_HRT_df['Total_HRT']
        first_node = Total_HRT_df['Start_Node']
        in_node = conduit_summary['Inlet_Node']
        cond_length = conduit_summary['cond_length']
        mean_flow = conduit_summary['mean_flow']
        mean_depth = conduit_summary['mean_depth']
        cond_hrt = conduit_summary['Conduit HRT (HRS)']
        med_df = median_HRT_df['sc_median_hrt']

        for index, row in Total_HRT_df.iterrows():
            if subs[index] in median_HRT_df['sc.id'].values:
                # median_row = median_HRT_df[median_HRT_df['sc.id'] == subs[index]].iloc[0]
                
                for ii, row in median_HRT_df.iterrows():

                    if tot_hrt[index] != med_df[ii]:
                        final_path_hrt = med_df[ii]
                        start_node = in_node[index]

                        for j, conduit_row in conduit_summary.iterrows():
                            inlet_node = first_node[j]

                            if inlet_node == start_node:
                                curr_cond_length = cond_length[j]
                                curr_mean_flow = mean_flow[j]
                                curr_mean_depth = mean_depth[j]
                                curr_cond_hrt = cond_hrt[j]
                                tot_path_hrt = tot_hrt[index]

                                print(f"Current conduit length is {curr_cond_length}.")
                                print(f" Current conduit HRT: {curr_cond_hrt}. ")
                                print(f"Current path HRT is {tot_path_hrt}.")
                                print(f"Final HRT as per csv file should be {final_path_hrt}.")
                                print(f"finally : {curr_mean_depth}")
                                print(f"and mean flow rate: {curr_mean_flow}")
                            
                            # pass total_HRT_df not conduit summary but also update length in cond sum
                            updated_conduit_sum = find_x(conduit_summary, Total_HRT_df, final_path_hrt, curr_mean_flow, curr_mean_depth, tot_path_hrt, 
                            curr_cond_hrt, curr_cond_length)
                        
                        else:
                            return updated_conduit_sum
                            # return final_path_hrt
                    
def find_x(conduit_summary, Total_HRT_df, final_path_hrt, curr_mean_flow, curr_mean_depth, tot_path_hrt, curr_cond_hrt, curr_cond_length):
    # add that the total hrt should add up to final_path_hrt not JUST the one conduit
    radius = 1.5
    
    target_hrt = final_path_hrt - tot_path_hrt - curr_cond_hrt
    theta = 2*np.arccos(((radius - (curr_mean_depth))) / radius)
    flow_area = (radius**2 * (theta - np.sin(theta))) / 2
    flow_vol = target_hrt*3600*curr_mean_flow 
    x = flow_vol/flow_area
    new_v = curr_mean_flow/flow_area
    
    print(f"new conduit flow velocity assuming depth remains the same :{new_v} ")
    print(f"new length = {x}")
    updated_vals = update_conduit_length(conduit_summary, Total_HRT_df, x, curr_cond_length, target_hrt, final_path_hrt)
    
    return updated_vals

def update_conduit_length(conduit_summary, Total_HRT_df, new_length, curr_cond_length, target_hrt, final_path_hrt):
        
        # Total_HRT_df = Total_HRT_df.set_index(['cond_name', 'Inlet_Node', 'Outlet_Node'], inplace = True)
        for index, row in conduit_summary.iterrows():

            if curr_cond_length == conduit_summary.at[index, 'cond_length']:
                conduit_summary.at[index, 'cond_length'] = new_length
                inlet_node = conduit_summary['Inlet_Node'][index]
                start_node = Total_HRT_df['Start_Node'][index]
                #update total hrt AND individual cond hrt

                if inlet_node == start_node:
                    conduit_summary.at[index, 'Conduit HRT (HRS)'] = target_hrt
                    Total_HRT_df.at[index, 'Total_HRT'] = final_path_hrt
                    
                print(f'Updated length of conduit, from {curr_cond_length} to new length of: {new_length}')
                print(conduit_summary)
                print(Total_HRT_df)

                # call create_graph again!
                # make while loop in main to automate

        return new_length

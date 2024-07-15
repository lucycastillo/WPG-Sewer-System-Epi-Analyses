import os
import shutil
import numpy as np
import pandas as pd
import networkx as nx

def calculate_HRT(conduit_summary):
    radius = 1.5

    theta_df = pd.Series(index=conduit_summary.index, dtype=float)
    flow_area_df = pd.Series(index=conduit_summary.index, dtype=float)
    flow_volume_df = pd.Series(index=conduit_summary.index, dtype=float)
    HRT_df = pd.Series(index=conduit_summary.index, dtype=float)
    
    for index, row in conduit_summary.iterrows():
        try:

            theta_df.loc[index] = 2*np.arccos(((radius - row['mean_depth'])) / radius)
    
            flow_area_df.loc[index] = (radius**2 * (theta_df.loc[index] - np.sin(theta_df.loc[index]))) / 2
    
            flow_volume_df.loc[index] = flow_area_df.loc[index] * (row['cond_length'])

            HRT_df.loc[index] = (flow_volume_df.loc[index] / row['mean_flow']) / 3600

        except Exception as e:
            print(f"An error occured at index {index}: {e}")

        continue
    HRT = pd.DataFrame(HRT_df, columns= ['Conduit HRT (HRS)'])

    return HRT


# Sample data
data = {
    'mean_depth': [0.265454, 0.462340, 0.252310, 0.140396, 0.289859],
    'mean_flow': [0.223589, 0.703011, 0.201230, 0.055859, 0.266972],
    'cond_length': [839.4065, 4137.0618, 495.5659, 473.4282, 3715.5304]
}

# df for testing
conduit_summary = pd.DataFrame(data)

#HRT_result = calculate_HRT(conduit_summary)
#print(HRT_result)

def calculate_path_HRT(graph, conduits, path):
    total_HRT = 0
    for i in range(len(path) - 1):
        start_node = path[i]
        end_node = path[i + 1]
        conduit = conduits[start_node][end_node]
        conduit_HRT = calculate_HRT(conduit_summary)
        total_HRT += conduit_HRT
    return total_HRT

def calculate_node_to_pathway(g, source, target, conduit_states):

    path_nodes = nx.dijkstra_path(g, source, target)
    source = 0
    path_conduits = [node for node in path_nodes if node in conduit_states.index]
    path_edges = [(path_nodes[ii],path_nodes[ii+1]) for ii, _ in enumerate(path_nodes[:-1])]
    path_reference_ids = [g.edges()[edge]['id'] for edge in path_edges]
    path_reference_ids =[id for id in path_reference_ids if id in conduit_states.index]
    path_hrt = conduit_states.loc[path_reference_ids,'conduit_hrt'].sum()
    path_length = conduit_states.loc[path_reference_ids,'conduit_length'].sum()/1000

    if len(path_reference_ids) > 0:
        path['reference_id'] = path_reference_ids[0]
        path['path_source'] = source
        path['path_target'] = target
        path['nodes'] = path_nodes
        path['edges'] = path_edges
        path['reference_ids'] = path_reference_ids
        path['path_hrt'] = path_hrt
        path['path_length'] = path_length
    return path 

   
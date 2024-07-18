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
    theta = pd.DataFrame(theta_df, columns= ['Theta Values'])
    flow_area = pd.DataFrame(flow_area_df, columns=['Flow Area'])
    flow_vol = pd.DataFrame(flow_volume_df, columns=['flow volume'])
    print(theta)
    print(flow_area)
    print(flow_vol)

    return HRT

def calculate_path_HRT(path, conduit_dict):

    total_hrt = 0

    # for i in range(len(path) - 1):
        # start_node = path[i]
        # end_node = path[i + 1]
        
        # key = ('ct_' + str(i), start_node, end_node)
        # print([key for key in conduit_dict])
        # print(path)
    keys = [key for key in conduit_dict if (key[1] in path and key[2] in path)]
    print(keys)
        
    for key in keys:

        # if key in conduit_dict:
        hrt_value = conduit_dict[key]
        #print(f"Conduit ID FOUND for nodes: {start_node}, {end_node}")
        total_hrt += hrt_value

    # else:
        #print(f"Conduit ID not found for nodes: {start_node}, {end_node}")

        # pass
    #total_path_HRT['Total_HRT'] = total_hrt

    return total_hrt
   


import pandas as pd
import networkx as nx
import numpy as np
from pyswmm import Simulation, Links, Nodes, Subcatchments
#from swmm.toolkit.shared_enum import ObjectType
from swmmio import Model
from calibration_HRT_utils import calculate_HRT, calculate_path_HRT, calibrate_HRT, create_graph

inp_file_path = 'HRT_calibration_files/wpg_cm.inp'

# Initialize an empty df
cond_df = pd.DataFrame(columns=["cond_name", "mean_flow", "mean_depth"])

# Run simulation and loop through conduits
with Simulation(inp_file_path) as sim:
    link_obj = Links(sim)
    conduit_data = {f"ct_{num}": {'flows': [], 'depths': []} for num in range(0, 19)}
    
    for step in sim:
        for num in range(0, 19):
            cond_name = f"ct_{num}"
            curr = link_obj[cond_name]
            # append flows and flow depth data to conduit data
            conduit_data[cond_name]['flows'].append(curr.flow)
            conduit_data[cond_name]['depths'].append(curr.depth)

# Calculate mean flow and depth for each conduit
for cond_name, data in conduit_data.items():
    # loop through conduit_data and calculate mean depth and flow rate
    mean_flow = sum(data['flows']) / len(data['flows']) if data['flows'] else 0
    mean_depth = sum(data['depths']) / len(data['depths']) if data['depths'] else 0
    
    # Append the results to the main df
    cond_df = pd.concat([cond_df, pd.DataFrame({"cond_name": [cond_name], "mean_flow": [mean_flow], "mean_depth": [mean_depth]})], ignore_index=True)

m = Model(inp_file_path)
# Extract link properties from .inp file
cond_summary = m.links.dataframe[['InletNode', 'OutletNode', 'Length']]
cond_summary.rename(columns={'InletNode': 'Inlet_Node', 'OutletNode': 'Outlet_Node', 'Length': 'cond_length'}, inplace=True)
# Merge to main df
cond_df_merged = pd.merge(cond_df, cond_summary, left_on='cond_name', right_on='Name', how='left')

# Call function from utils
HRT = calculate_HRT(cond_df_merged)

# Merge HRT results to main df
merged_df = pd.concat([cond_df_merged, HRT], axis = 1)
merged_df.set_index(['cond_name', 'Inlet_Node', 'Outlet_Node'], inplace = True)
# merged_df.set_index(['cond_name'], inplace = True)

# # Created directed graph
# G = nx.DiGraph()
# # Define outfall
# outfalls = ['node_21', 'node_3', 'node_12']

# with Simulation(inp_file_path) as sim:
#     nodes = Nodes(sim)
#     for node in nodes:
#             G.add_node(node.nodeid)

#     # Add conduits to the graph with lengths as weights
#     for index, row in cond_summary.iterrows():
#         G.add_edge(row['Inlet_Node'], row['Outlet_Node'], weight=row['cond_length'])

# results = []

# for node in G.nodes:
#     for outfall in outfalls:
#             if node != outfall:
#                 try:
#                     shortest_path = nx.dijkstra_path(G, node, outfall, weight='weight')
#                     path_hrt = calculate_path_HRT(merged_df, shortest_path)
#                     #print(shortest_path)
#                     results.append({
#                         'Start_Node': node,
#                         'End_Node': outfall,
#                         'Path': shortest_path,
#                         'Total_HRT': path_hrt
#                     })
#                 except nx.NetworkXNoPath:
#                     # print(f"ERROR on {node} and {outfall}")
#                     continue

outfalls = ['node_21', 'node_3', 'node_12']
new_df = merged_df.reset_index()
# this works now!
path_hrt_df = create_graph(new_df, merged_df, inp_file_path, outfalls)


# this works but missing three sub ids
with Simulation(inp_file_path) as sim:
    
    if 'Subcatchments' not in path_hrt_df.columns:
        path_hrt_df['Subcatchments'] = ''

    index = 0
    for index, row in path_hrt_df.iterrows():
        sc_name = f"sc_{index}"
        curr = Subcatchments(sim)[sc_name]
        outlet_node = curr.connection
        matching_rows = path_hrt_df[path_hrt_df['Start_Node'] == outlet_node]

        for matching_index in matching_rows.index:
            if path_hrt_df.at[matching_index, 'Subcatchments']:
                path_hrt_df.at[matching_index, 'Subcatchments'] += f", {sc_name}"
            else:
                path_hrt_df.at[matching_index, 'Subcatchments'] = sc_name

# Create empty dfs
north_df = pd.DataFrame(columns=['Total_HRT'], dtype=float)
south_df = pd.DataFrame(columns=['Total_HRT'], dtype=float)
west_df = pd.DataFrame(columns=['Total_HRT'], dtype=float)

for index, row in path_hrt_df.iterrows():
    if row['End_Node'] == 'node_3':
        path_hrt_df.loc[index, 'WWTP'] = 'North'
        north_df.loc[index] = row['Total_HRT']
        mean_north = np.mean(north_df)
        med_north = north_df['Total_HRT'].median()

    elif row['End_Node'] == 'node_12':
        path_hrt_df.loc[index, 'WWTP'] = 'South'
        south_df.loc[index] = row['Total_HRT']
        mean_south = np.mean(south_df)
        med_south = south_df['Total_HRT'].median()
    
    else:
        path_hrt_df.loc[index, 'WWTP'] = 'West'
        west_df.loc[index] = row['Total_HRT']
        med_west = west_df['Total_HRT'].median()
        mean_west = np.mean(west_df)

# Calculate median HRT by WWTP
med_north = north_df['Total_HRT'].median() if not north_df.empty else 0
med_south = south_df['Total_HRT'].median() if not south_df.empty else 0
med_west = west_df['Total_HRT'].median() if not west_df.empty else 0
medians = [med_north, med_south, med_west]

# Create df containing median results
median_HRT_df = pd.DataFrame({
    'WWTP': ['North', 'South', 'West'],
    'Median_HRT': [med_north, med_south, med_west]
})

# Create df containing mean results
mean_HRT_df = pd.DataFrame({
    'WWTP': ['North', 'South', 'West'],
    'Mean_HRT': [mean_north, mean_south, mean_west]
})

median_sc_df = pd.read_csv("HRT_calibration_files/iw-Subcat-HRT.csv")
# Call calibration function
med_sc_df = median_sc_df.drop(median_sc_df.columns[0:1], axis= 1)
# print(med_sc_df)
# print(path_hrt_df)

# while loop here
print(new_df)
updated_df = calibrate_HRT(new_df, path_hrt_df, med_sc_df)
print(updated_df)

# while updated_dfs['Total_HRT'] != med_sc_df['sc_median_hrt']:
#     updated_dfs = calibrate_HRT(new_df, path_hrt_df, med_sc_df)
# print(updated_dfs)


   

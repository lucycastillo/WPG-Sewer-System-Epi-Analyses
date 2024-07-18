
import pandas as pd
import networkx as nx
from pyswmm import Simulation, Links, Nodes
from swmmio import Model
from calibration_HRT_utils import calculate_HRT, calculate_path_HRT

inp_file_path = 'wpg_cm.inp'

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
            conduit_data[cond_name]['flows'].append(curr.flow)
            conduit_data[cond_name]['depths'].append(curr.depth)
            

# Calculate mean flow and depth for each conduit
for cond_name, data in conduit_data.items():
    mean_flow = sum(data['flows']) / len(data['flows']) if data['flows'] else 0
    mean_depth = sum(data['depths']) / len(data['depths']) if data['depths'] else 0
    
    # Append the results to the main df
    cond_df = pd.concat([cond_df, pd.DataFrame({"cond_name": [cond_name], "mean_flow": [mean_flow], "mean_depth": [mean_depth]})], ignore_index=True)

m = Model(inp_file_path)
# Extract link summary and format df
cond_summary = m.links.dataframe[['InletNode', 'OutletNode', 'Length']]
cond_summary.rename(columns={'InletNode': 'Inlet_Node', 'OutletNode': 'Outlet_Node', 'Length': 'cond_length'}, inplace=True)
cond_df_merged = pd.merge(cond_df, cond_summary, left_on='cond_name', right_on='Name', how='left')

# Call function from utils
HRT = calculate_HRT(cond_df_merged)
merged_df = pd.concat([cond_df_merged, HRT], axis = 1)
merged_df.set_index(['cond_name', 'Inlet_Node', 'Outlet_Node'], inplace = True)
# print(merged_df)

G = nx.DiGraph()
outfalls = ['node_21', 'node_3', 'node_12']

with Simulation(inp_file_path) as sim:
    nodes = Nodes(sim)
    for node in nodes:
            G.add_node(node.nodeid)

    # Add conduits to the graph with lengths as weights
    for index, row in cond_summary.iterrows():
        G.add_edge(row['Inlet_Node'], row['Outlet_Node'], weight=row['cond_length'])

results = []

conduit_dict = merged_df['Conduit HRT (HRS)']. to_dict()

for node in G.nodes:
    for outfall in outfalls:
            if node != outfall:
                try:
                    shortest_path = nx.dijkstra_path(G, node, outfall, weight='weight')
                    path_hrt = calculate_path_HRT(shortest_path, conduit_dict)
                    #print(shortest_path)
                    results.append({
                        'Start_Node': node,
                        'End_Node': outfall,
                        'Path': shortest_path,
                        'Total_HRT': path_hrt
                    })
                except nx.NetworkXNoPath:
                    # print(f"ERROR on {node} and {outfall}")
                    continue

results_df = pd.DataFrame(results)
total_N = 0
total_S = 0
total_W = 0

for index, row in results_df.iterrows():
    if row['End_Node'] == 'node_3':
        results_df.loc[index, 'WWTP'] = 'North'
        total_N += row['Total_HRT']
        mean_north_HRT = total_N / len(results_df[results_df['WWTP'] == 'North']) if len(results_df[results_df['WWTP'] == 'North']) > 0 else 0

    elif row['End_Node'] == 'node_12':
        results_df.loc[index, 'WWTP'] = 'South'
        total_S += row['Total_HRT']
        mean_south_HRT = total_S / len(results_df[results_df['WWTP'] == 'South']) if len(results_df[results_df['WWTP'] == 'South']) > 0 else 0
    
    else:
        results_df.loc[index, 'WWTP'] = 'West'
        total_W += row['Total_HRT']
        mean_west_HRT = total_W / len(results_df[results_df['WWTP'] == 'West']) if len(results_df[results_df['WWTP'] == 'West']) > 0 else 0

print(f"Mean North HRT: {mean_north_HRT}")
print(f"Mean South HRT: {mean_south_HRT}")
print(f"Mean West HRT: {mean_west_HRT}")
print(results_df)

   

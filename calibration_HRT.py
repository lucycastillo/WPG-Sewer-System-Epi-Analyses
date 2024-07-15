
import pandas as pd
import networkx as nx
from pyswmm import Simulation, Links
from calibration_HRT_utils import calculate_HRT, calculate_node_to_pathway

with Simulation(r"./wpg_cm.inp") as sim:
    for link in Links(sim):

    # Initialize an empty df
        cond_df = pd.DataFrame(columns=["cond_name", "mean_flow", "mean_depth"])

# Run the simulation and loop through conduits
for num in range(0, 19):
    with Simulation(r"./wpg_cm.inp") as sim:
        link_obj = Links(sim)
        
        # Construct link names
        cond_name = f"ct_{num}"
        curr = link_obj[cond_name]
        
        # Temporary lists
        flows = []
        depths = []
        
        # Step through the simulation
        for step in sim:
            flows.append(curr.flow)
            depths.append(curr.depth)

        # Calculate mean flow and depth
        mean_flow = sum(flows) / len(flows) if flows else 0
        mean_depth = sum(depths) / len(depths) if depths else 0
        
        # Append the results to the main df
        cond_df = pd.concat([cond_df, pd.DataFrame({"cond_name": [cond_name], "mean_flow": [mean_flow], "mean_depth": [mean_depth]})], ignore_index=True)


from swmmio import Model, Links
m = Model("wpg_cm.inp")

# Extract link summary and format df
cond_summary = m.links.dataframe
cond_summary = cond_summary.iloc[:, 0:3]
cond_summary.rename(columns={'InletNode': 'Inlet_Node', 'OutletNode':'Outlet_Node', 'Length':'cond_length'}, inplace = True)
cond_df_merged = pd.merge(cond_df, cond_summary, left_on='cond_name', right_on='Name', how='left')

# Call function from utils
HRT = calculate_HRT(cond_df_merged)

# Create tmp col to merge dfs
HRT['tmp'] = 2
cond_df_merged['tmp'] = 2
merged_df = pd.merge(cond_df_merged, HRT, on =['tmp'])
merged_df = merged_df.drop('tmp', axis =1)

# Determine HRT paths
#with Simulation(r"./wpg_cm.inp") as sim:
 #   nodes = sim.nodes
  #  conduits = sim.conduits

G = nx.Digraph()
#for node in nodes:
 #   G.add_node(node.nodeid)

#for conduit in conduits:
 #   G.add_edge(conduit.inlet_node.nodeid, conduit.outlet_node.nodeid, weight = conduit.length)

target = 'node_21'
#shortest_path = nx.dijkstra_path(G, start_node, )

paths = calculate_node_to_pathway(G, source, target)
print(paths)
   
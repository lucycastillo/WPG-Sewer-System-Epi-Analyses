# ========================================
#
# PURPOSE: This script processes Hydraulic Residence Time data from txt files (from concp_WPG__model.inp)
# and outputs a comprehensive table, bar plot and box plot.
#
# AUTHOR: LUCY CASTILLO
#
# =========================================
# format mean_conduit_Depth, flow_area, mean flow rate, conduit HRT to 2 dec places

# Load libraries

library(tidyr)
library(dplyr)
library(ggplot2)
library(stringr)
library(patchwork)
library(data.table)
library(tibble)
library(RColorBrewer)

workspace.name=choose.dir(default = "")

wd=setwd(workspace.name)

conduit_col_names <- c("ct_0", "ct_1", "ct_2", "ct_3", "ct_4", "ct_5",
                       "ct_6", "ct_7", "ct_8", "ct_9", "ct_10", "ct_11",
                       "ct_12", "ct_13", "ct_14", "ct_15", "ct_16", "ct_17",
                       "ct_18")

subcatchment_row_names <- c("sc_0", "sc_1", "sc_2", "sc_3", "sc_4", "sc_5",
                            "sc_6", "sc_7", "sc_8", "sc_9", "sc_10", "sc_11",
                            "sc_12","sc_13","sc_14","sc_15","sc_16", "sc_17",
                            "sc_18","sc_19","sc_20","sc_21")

## Detailed model results
detailed_model_HRT <- read.csv(file = "iw-Subcat-HRT.csv", header = FALSE, skip = 1 )
detailed_model_HRT_df <- detailed_model_HRT[, -c(1)]
colnames(detailed_model_HRT_df) <- c("WWTP", "Subcatchment ID", "HRT")

### Subcatchment Summary
# Rename columns and shift over cols 

subcatchment_summary <- read.table(file = "subcatchment_summary_wpg_cm.txt", fill = TRUE)

subcatchment_summary_df <- subcatchment_summary[-(1:5), (-8)]

colnames(subcatchment_summary_df) <- c("Subcatchment ID", "Subcatchment Area", 
                                        "Subcatchment Width", "%Imperv", "%Slope", 
                                        "Rain_Gage", "Inlet")

### Link Summary
link_column_names <- c("Conduit", "Inlet", "Outlet", "Type", "Length", 
                       "Slope", "Roughness")

link_summary <- read.table(file = "link_summary_wpg_cm.txt",  fill = TRUE)
link_summary_df <- link_summary[-(1:5),-(8:9) ]
colnames(link_summary_df) <- link_column_names

### Cross Section Summary
xsection_column_names <- c("Conduit", "Shape", "Full Depth", "Full Area", 
                           "Hyd Rad", "Max Width","No of Barrels", "Full Flow")

xsection_summary <- read.table(file = "xsection_summary_wpg_cm.txt", 
                                  col.names = xsection_column_names, fill = TRUE)

xsection_summary_df <- xsection_summary %>% 
                       filter(Conduit != "") %>%
                       .[-(1:6), ]


### Node Summary
node_column_names <- c("Name", "Type", "Invert Elev", "Max Depth", 
                       "Ponded Area", "External Inflow")

node_summary <- read.table("node_summary_wpg_cm.txt", 
                           col.names = node_column_names, fill = TRUE)

node_summary_df <- node_summary[-(1:6), ]

### Depth Summary
cond_depth1_column_names <- c("Date", "Time", "ct_0", "ct_1", "ct_2", "ct_3", 
                              "ct_4", "ct_5", "ct_6", "ct_7", "ct_8")

cond_depth2_column_names <- c("Date", "Time", "ct_9", "ct_10", "ct_11", "ct_12", 
                              "ct_13","ct_14","ct_15","ct_16", "ct_17", "ct_18")

# Read txt files and rename cols - 
cond_depth_df1 <- read.table(file = "link_depth1_wpg_cm.txt", 
                             col.names = cond_depth1_column_names, fill = TRUE)

cond_depth_df2 <- read.table(file = "link_depth2_wpg_cm.txt", 
                             col.names = cond_depth2_column_names, fill = TRUE)

# Delete first 4 rows
conduit_dep_df1 <- cond_depth_df1[-(1:4),]
conduit_dep_df2 <- cond_depth_df2[-(1:4),]

# Merge data frames 
merged_conduit_depth <- conduit_dep_df1 %>%
                    left_join(conduit_dep_df2, by = c("Date", "Time")) 

### Flow data - same thing here, merge tog then name cols conduit_col_names
link_flow1 <- read.table(file = "link_flow1_wpg_cm.txt", fill = TRUE)
link_flow_df1 <- link_flow1[-(1:4), ]

colnames(link_flow_df1) <- cond_depth1_column_names

link_flow2 <- read.table(file = "link_flow2_wpg_cm.txt", fill = TRUE)
link_flow_df2 <- link_flow2[-(1:4), ]

colnames(link_flow_df2) <- cond_depth2_column_names

# Merge flow data txt files
merged_flow_data <- link_flow_df1 %>%
  left_join(link_flow_df2, by = c("Date", "Time"))

### Mean simulated flow

# Make all cols numeric
for (col in colnames(merged_flow_data) [-c(1,2)]) 
  {
    merged_flow_data[[col]] <- as.numeric(merged_flow_data[[col]])
  }

# Calculate mean for each columns starting from 3
mean_flow_df <- colMeans(merged_flow_data[ , -c(1,2)], na.rm = TRUE)

# Make df
mean_flow_df <- as.data.frame(t(mean_flow_df))

### Mean Depth of flow

# Make all cols numeric
for (col in colnames(merged_conduit_depth) [-c(1,2)]) 
  {
    merged_conduit_depth[[col]] <- as.numeric(merged_conduit_depth[[col]])
  }

# Calculate mean for each columns starting from 3
mean_conduit_depth <- as.data.frame(colMeans(merged_conduit_depth[, -c(1,2)], na.rm = TRUE))


# Calculate cross-sectional Flow and mean flow velocity

# Define variables
radius <- 1.5 

# Create empty data frames
theta <- matrix(0, nrow(mean_conduit_depth), ncol(mean_conduit_depth))
flow_area_half_full <- matrix(0, nrow(mean_conduit_depth), ncol(mean_conduit_depth))
flow_volume_half_full <- matrix(0, nrow(mean_conduit_depth), ncol(mean_conduit_depth))
conduit_HRT_half_full <- matrix(0, nrow(mean_conduit_depth), ncol(mean_conduit_depth))

flow_area_full <- matrix(0, nrow(mean_conduit_depth), ncol(mean_conduit_depth))
flow_volume_full <- matrix(0, nrow(mean_conduit_depth), ncol(mean_conduit_depth))
conduit_HRT_full <- matrix(0, nrow(mean_conduit_depth), ncol(mean_conduit_depth))

# Convert Length column to numeric if needed
link_summary_df$Length <- as.numeric(link_summary_df$Length)

# Loop through each row of mean_conduit_depth
for (i in 1:ncol(mean_conduit_depth)) {
  theta[, i] <- 2*acos(((radius - mean_conduit_depth[, i]))/radius)
  flow_area_half_full[, i] <- (radius^2*(theta[, i] - sin(theta[, i])))/2
  flow_volume_half_full[, i] <- flow_area_half_full[, i]*(link_summary_df$Length[i])
  conduit_HRT_half_full[, i ] <- (flow_volume_half_full[, i] / mean_flow_df[, i])/3600
  
  
  flow_area_full[, i] <- (pi*radius^2) - ((radius^2*(theta[, i] - sin(theta[, i])))/2)
  flow_volume_full[, i] <- flow_area_full[, i]*(link_summary_df$Length[i])
  conduit_HRT_full[, i] <- (flow_volume_full[, i] / mean_flow_df[, i])/3600
}

# Assuming conduit_col_names is a vector or list containing conduit names
mean_conduit_depth$Conduit <- conduit_col_names

# Convert to data frames
conduit_HRT_half_full <- as.data.frame(conduit_HRT_half_full)
conduit_HRT_full <- as.data.frame(conduit_HRT_full)

### Create comprehensive table

# Format datasets
mean_flow_df_t <- mean_flow_df %>%
  t() %>%
  .[-c(20:25), ] %>%
  as.data.frame() %>%
  setNames("Mean Flow Rate") %>%
  mutate(Conduit = conduit_col_names)

conduit_HRT_full <- conduit_HRT_full %>%
  setNames("Conduit HRT - more than half full") %>%
  mutate(Conduit = conduit_col_names)

conduit_HRT_half_full <- conduit_HRT_half_full %>%
  setNames("Conduit HRT - less than half full") %>%
  mutate(Conduit = conduit_col_names)

flow_area_full <- flow_area_full %>%
  as.data.frame() %>%
  t() %>%
  .[-c(20:25), ] %>%
  as.data.frame() %>%
  setNames("Flow Area - More than half full") %>%
  mutate(Conduit = conduit_col_names)

flow_area_half <- flow_area_half_full %>%
  as.data.frame() %>%
  t() %>%
  .[-c(20:25), ] %>%
  as.data.frame() %>%
  setNames("Flow Area - Less than half full") %>%
  mutate(Conduit = conduit_col_names)

# Combine dataframes
combinedTab <- link_summary_df %>%
  left_join(xsection_summary_df, by = c("Conduit")) %>%
  left_join(mean_conduit_depth, by = c("Conduit")) %>%
  left_join(flow_area_full, by = c("Conduit")) %>%
  left_join(flow_area_half, by = c("Conduit")) %>%
  left_join(mean_flow_df_t_, by = c("Conduit")) %>%
  left_join(conduit_HRT_half_full, by = c("Conduit")) %>%
  left_join(conduit_HRT_full, by = c("Conduit"))

# Subcatchment Inlet
newcombinedTab <- subcatchment_summary_df %>%
                  left_join(combinedTab, by = c("Inlet"))


combinedTab_2 <- combinedTab[, -c(8, 9, 10, 11, 12, 13, 14, 15, 16)]

W_subcatchments <- c("sc_3", "sc_10", "sc_5", "sc_9")

SE_subcatchments <- c("sc_19", "sc_14", "sc_7", "sc_13",
                      "sc_2",  "sc_6",  "sc_8", "sc_11")

N_subcatchments <- c("sc_21", "sc_16", "sc_12", "sc_18", 
                     "sc_17", "sc_0",  "sc_1",  "sc_4", "sc_15", "sc_20")

newcombinedTab$WWTP <- NA

newcombinedTab_2 <- newcombinedTab[!duplicated(newcombinedTab$`Subcatchment ID`), ]

for (i in 1: nrow(newcombinedTab_2))
{
  if (newcombinedTab_2$`Subcatchment ID`[i] %in% W_subcatchments)
  {
    newcombinedTab_2$WWTP[i] <- "West"
  }
  
   else if (newcombinedTab_2$`Subcatchment ID`[i] %in% SE_subcatchments)
  {
    newcombinedTab_2$WWTP[i] <- "South"
  }
  
  else if  (newcombinedTab_2$`Subcatchment ID`[i] %in% N_subcatchments)
  {
    newcombinedTab_2$WWTP[i] <- "North"
  }
}

# Define the paths
paths <- list(
  WEWPCC = list(
    path_11  = combinedTab_2$`Conduit HRT - less than half full`[3] + combinedTab_2$`Conduit HRT - less than half full`[8] + combinedTab_2$`Conduit HRT - less than half full`[5],
    
    path_1 = combinedTab_2$`Conduit HRT - less than half full`[8] + combinedTab_2$`Conduit HRT - less than half full`[5],
    
    path_10 = combinedTab_2$`Conduit HRT - less than half full`[5],
    path_21 = combinedTab_2$`Conduit HRT - less than half full`[5]/2
  ),
  SEWPCC = list(
    path_16 = combinedTab_2$`Conduit HRT - less than half full`[17] + combinedTab_2$`Conduit HRT - less than half full`[11] + combinedTab_2$`Conduit HRT - less than half full`[2],
    
    path_9 = combinedTab_2$`Conduit HRT - less than half full`[11] + combinedTab_2$`Conduit HRT - less than half full`[2],
    
    path_15 = combinedTab_2$`Conduit HRT - less than half full`[2],
    
    path_8 = combinedTab_2$`Conduit HRT - less than half full`[12] + combinedTab_2$`Conduit HRT - less than half full`[11] + combinedTab_2$`Conduit HRT - less than half full`[2],
    
    path_17 = combinedTab_2$`Conduit HRT - less than half full`[6] + combinedTab_2$`Conduit HRT - less than half full`[9] + combinedTab_2$`Conduit HRT - less than half full`[2],
    
    path_0 = combinedTab_2$`Conduit HRT - less than half full`[7] + combinedTab_2$`Conduit HRT - less than half full`[9] + combinedTab_2$`Conduit HRT - less than half full`[2],
    
    path_2 = combinedTab_2$`Conduit HRT - less than half full`[9] + combinedTab_2$`Conduit HRT - less than half full`[2],
    
    path_12 = combinedTab_2$`Conduit HRT - less than half full`[2] /2
  ),
  NEWPCC = list(
    path_18 = combinedTab_2$`Conduit HRT - less than half full`[4]+ combinedTab_2$`Conduit HRT - less than half full`[18] + combinedTab_2$`Conduit HRT - less than half full`[14] + combinedTab_2$`Conduit HRT - less than half full`[15],
   
    path_20 = combinedTab_2$`Conduit HRT - less than half full`[13] + combinedTab_2$`Conduit HRT - less than half full`[18] + combinedTab_2$`Conduit HRT - less than half full`[14] + combinedTab_2$`Conduit HRT - less than half full`[15],
    
    path_7 = combinedTab_2$`Conduit HRT - less than half full`[18] + combinedTab_2$`Conduit HRT - less than half full`[14] + combinedTab_2$`Conduit HRT - less than half full`[15],
    
    path_4 = combinedTab_2$`Conduit HRT - less than half full`[1] + combinedTab_2$`Conduit HRT - less than half full`[14] + combinedTab_2$`Conduit HRT - less than half full`[15],
    
    path_6 = combinedTab_2$`Conduit HRT - less than half full`[14] + combinedTab_2$`Conduit HRT - less than half full`[16] + combinedTab_2$`Conduit HRT - less than half full`[15],
    
    path_13 = combinedTab_2$`Conduit HRT - less than half full`[15] + combinedTab_2$`Conduit HRT - less than half full`[16],
    
    path_5 = combinedTab_2$`Conduit HRT - less than half full`[19] + combinedTab_2$`Conduit HRT - less than half full`[16] + combinedTab_2$`Conduit HRT - less than half full`[15],
    
    path_19 = combinedTab_2$`Conduit HRT - less than half full`[10] + combinedTab_2$`Conduit HRT - less than half full`[16] + combinedTab_2$`Conduit HRT - less than half full`[15],
    
    path_14 = combinedTab_2$`Conduit HRT - less than half full`[15],
    
    path_3 = combinedTab_2$`Conduit HRT - less than half full`[15]/2
  )
)

# Print the updated sc_HRT
sc_HRT <- newcombinedTab_2[, -c(6, 8, 10, 12:19,18,22, 23, 24, 26) ] %>%
           rename(`HRT` = `Conduit HRT - less than half full`)
sc_HRT$Inlet <- NA
 
# Iterate over each row in sc_HRT
for (i in 1:nrow(sc_HRT)) {
  inlet_2 <- sc_HRT$Outlet[i]
  matching_index <- which(combinedTab_2$Inlet == inlet_2)
           
  # If a match is found, assign the corresponding Inlet value to sc_HRT$In
  if (length(matching_index) > 0) 
  {
   sc_HRT$Inlet[i] <- combinedTab_2$Outlet[matching_index]
  }
}

# Function to convert the list to a data frame
list_to_df <- function(lst) {
  df <- bind_rows(lapply(lst, enframe), .id = "Subcatchment ID")
  df <- df %>%
    select(-name) %>% 
    rename(HRT = value)
    return(df)
}

# Combine the data frames into one with an additional column for the source
combine_data <- function(df_list, label) {
  df <- list_to_df(df_list)
  df_long <- df %>%
    mutate(WWTP = label)
  return(df_long)
}

# Convert the lists to data frames and add WWTP labels
WEWPCC_long <- combine_data(paths$WEWPCC, "WEWPCC")
SEWPCC_long <- combine_data(paths$SEWPCC, "SEWPCC")
NEWPCC_long <- combine_data(paths$NEWPCC, "NEWPCC")

# Combine all data frames into one
combined_data <- bind_rows(WEWPCC_long, SEWPCC_long, NEWPCC_long)

# Format df
sc_HRT <- sc_HRT %>%
  mutate(Node_Number = sub("node_", "", Outlet)) %>%
  mutate(Path_Name = paste0("path_", Node_Number))

updated_sc_HRT <- sc_HRT %>%
  left_join(combined_data %>% rename(Path_Name = `Subcatchment ID`), by = "Path_Name") %>%
  rename(HRT = HRT.y) %>%
  rename(WWTP = WWTP.x) %>%
  select(-HRT.x, -WWTP.y) %>%
  rename(Inlet_Node = Outlet) %>%
  rename(Downstream_Node = Inlet) 

## Bar plots

# Create a faceted bar plot
bar_plt_subcatchment <- ggplot(updated_sc_HRT, aes(x = `Subcatchment ID`, y = HRT, fill = WWTP))  +
  geom_bar(stat = "identity", color = "black") +
  geom_text(aes(label = round(HRT, 1)), vjust = -0.5, color = "black", size = 3.5) +
  theme_minimal() +
  labs(title = "Conduit HRT by Subcatchment and WWTP", 
       x = 'Subcatchment ID', y = "HRT (hr)") +
  facet_wrap(~ WWTP, scales = "free_x") +
  theme(legend.position = "bottom",
        axis.text.x = element_text(angle = 45, hjust = 1), # Rotate x-axis text
        axis.text.y = element_text(margin = margin(r = 10)), # Add margin to y-axis text
        plot.title = element_text(hjust = 0.5)) # Center the plot title

# Calculate mean HRT for each WWTP
wwtp_mean_hrt <- combined_data %>%
  group_by(WWTP) %>%
  summarise(mean_HRT = mean(HRT))

# Merge mean HRT back to the combined data frame
combined_data <- combined_data %>%
  left_join(wwtp_mean_hrt, by = "WWTP")

# Create the histogram plot with mean HRT annotations
dist_WWTP_plot <- ggplot(combined_data, aes(x = HRT, fill = WWTP)) +
  #geom_histogram(aes(y = ..density..), alpha = 0.7, position = "identity", color = "black") +
  geom_density(alpha = 0.5) +
  facet_wrap(~ WWTP, scales = "free") +
  labs(x = 'Path HRT (hr)', y = "Density of Flow Path", title = "Hydraulic Residence Time by WWTP") +
  geom_vline(aes(xintercept = mean_HRT), color = "black", linetype = "dashed", size = 0.5) +
  geom_text(data = combined_data %>% group_by(WWTP) %>% summarize(mean_HRT = mean(HRT)),
            aes(x = mean_HRT, label = paste0('Mean HRT = ', round(mean_HRT, 0.5)), y = 0.5),
            color = "black", vjust = -1.5, hjust = 0.4, size = 2.5) +
  theme_minimal() +
  theme(legend.position = "bottom",
        axis.text.x = element_text(angle = 45, hjust = 1),
        axis.text.y = element_text(margin = margin(r = 10)),
        plot.title = element_text(hjust = 0.5))
## Bar plots

# Create a faceted bar plot
bar_plt_subcatchment <- ggplot(updated_sc_HRT, aes(x = `Subcatchment ID`, y = `HRT`, fill = WWTP)) +
  geom_bar(stat = "identity", color = "black") +
  geom_text(aes(label = round(`HRT`, 1)), vjust = -0.5, color = "black", size = 3.5) +
  theme_minimal() +
  labs(title = "Conduit HRT by Subcatchment and WWTP", 
       x = 'Subcatchment ID', y = "HRT (hr)") +
  facet_wrap(~ WWTP, scales = "free_x") +
  theme(legend.position = "bottom",
  axis.text.x = element_text(angle = 45, hjust = 1), # Rotate x-axis text
  axis.text.y = element_text(margin = margin(r = 10)), # Add margin to y-axis text
  plot.title = element_text(hjust = 0.5)) # Center the plot title


# Create the box plot WWTP
box_plt_WWTP <- ggplot(combined_data, aes(x = WWTP, y = HRT, fill = WWTP)) +
  geom_boxplot() +
  labs(title = "HRT by WWTP",
       x = "WWTP",
       y = "HRT (hours)") +
  theme_minimal() +
  theme(legend.position = "none") +
  ylim(0, 50)

# Create the time_difference dataframe
  time_difference <- data.frame(Subcatchment_ID = detailed_model_HRT_df$`Subcatchment ID`, 
                                time_diff = rep(0, nrow(detailed_model_HRT_df)))
  
# Merge the two dataframes on the Subcatchment ID column
  merged_df <- merge(detailed_model_HRT_df, updated_sc_HRT, by.x = "Subcatchment ID", by.y = "Subcatchment ID")
  
# Calculate the time difference
  merged_df$time_diff <- merged_df$HRT.x - merged_df$HRT.y
  
# Create the time_difference dataframe from the merged dataframe
  time_difference <- merged_df[, c("Subcatchment ID", "time_diff")]
  
  bar_plt_time_diff <- ggplot(merged_df, aes(x = `Subcatchment ID`, y = `time_diff`, fill = WWTP.y)) +
    geom_bar(stat = "identity", color = "black") +
    geom_text(aes(label = round(`time_diff`, 1)), vjust = -0.5, color = "black", size = 3.5) +
    theme_minimal() +
    labs(title = "Conduit HRT by Subcatchment and WWTP", 
         x = 'Subcatchment ID', y = "Time difference (hr)") +
    facet_wrap(~ WWTP.y, scales = "free_x") +
    theme(legend.position = "bottom",
          axis.text.x = element_text(angle = 45, hjust = 1), # Rotate x-axis text
          axis.text.y = element_text(margin = margin(r = 10)), # Add margin to y-axis text
          plot.title = element_text(hjust = 0.5)) # Center the plot title
  
# SAVING PLOTS
  pdf('concp-mod-HRT.pdf', width=11, height=8)
  plot(bar_plt_subcatchment)
  plot(dist_WWTP_plot)
  plot(box_plt_WWTP)
  plot(bar_plt_time_diff)
  dev.off()
  
# Save csv
write.csv(combinedTab_2, "concp_model_wpg_HRT.csv", row.names = FALSE)
write.csv(updated_sc_HRT, "concp_model_wpg_HRT_sc.csv", row.names = FALSE)
write.csv(time_difference, "concp_model_vs_detailed_timediff.csv", row.names = FALSE)

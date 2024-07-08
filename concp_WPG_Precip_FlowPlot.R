# ========================================
#
# PURPOSE: This script processes data from Total Inflow txt file (from concp_wpg.inp)
# and precip.dat file, outputs comprehensive graph.
#
# AUTHOR: LUCY CASTILLO
#
# =========================================

# Load libraries

library(ggplot2)
library(lubridate)
library(dplyr)
library(patchwork)
library(tidyverse)
library(dataRetrieval)
library(cowplot)
library(magrittr)
library(ggpubr)


workspace.name=choose.dir(default = "")

wd=setwd(workspace.name)

# Extract data from files
rainData <- read.table('precip.dat', header = FALSE, skip = 1)

newpccFlow <- read.table(file = "node3_TOTALINFLOW.txt", 
                         fill = TRUE, header = TRUE, skip = 3)

sewpccFlow <- read.table("node12_TOTALINFLOW_.txt", 
                         fill = TRUE, header = TRUE, skip = 3)

wewpccFlow <- read.table("node21_TOTALINFLOW.txt", 
                         fill = TRUE, header = TRUE, skip = 3)

# Reformat header and column names
vars.rain = c("Station","Year","Month","Day","Hour","Minute","Precip (mm)")
names(rainData) <- vars.rain

rainData = rainData |> 
  mutate(Date = ymd_hm(paste(Year, Month, Day, Hour, Minute, sep='-')))

date.start = ymd_hm('2020-08-24 00:00')

# Create new column with dates in Y-M-D format

newpccFlow <- newpccFlow %>%
  mutate(Date = mdy_hms(paste(Date, Time))) %>%
  select(Date, node_3)

sewpccFlow <- sewpccFlow %>%
  mutate(Date = mdy_hms(paste(Date, Time))) %>%
  select(Date, node_12)

wewpccFlow <- wewpccFlow %>%
  mutate(Date = mdy_hms(paste(Date, Time))) %>%
  select(Date, node_21)

# Merge rainData and Flow data frames 
newpccResults <- merge.data.frame(rainData, newpccFlow, by = c("Date"))

# Delete extra columns
newpccResults[, c("Station", "Year", "Month", "Day", "Hour", "Hours", "Minute")] <- list(NULL)

# Rename column
colnames(newpccResults)[3] <- "Flow (cms)"

sewpccResults <- merge.data.frame(rainData, sewpccFlow, by = c("Date"))

#Delete extra columns
sewpccResults[, c("Station", "Year", "Month", "Day", "Hour", "Hours", "Minute")] <- list(NULL)

# Rename columns
colnames(sewpccResults)[3] <- "Flow (cms)"

wewpccResults <- merge.data.frame(rainData, wewpccFlow, by = c("Date"))

# Delete extra columns
wewpccResults[, c("Station", "Year", "Month", "Day", "Hour", "Hours", "Minute", "Days", "Time")] <- list(NULL)

#Rename column
colnames(wewpccResults)[3] <- "Flow (cms)"

  coeff <- 10

# Assign colours to display on plot
  flowColour <- "#69b3a2"
  precipColour <- rgb(0.2, 0.6, 0.9, 1)
  
  newpcc_combined_data <- cbind(newpccResults, Flow_scaled = newpccResults$`Flow (cms)` / coeff)
  
# Flow hydrograph for NEWPCC
  N1 <- ggplot(newpcc_combined_data) +
    geom_line(aes(Date, Flow_scaled, color = flowColour)) +
    scale_y_continuous(position = "left",
                       limits = c(0, 1),
                       expand = c(0,0)) +
    scale_color_manual(values = c("sienna1")) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Flow [cms]",
         x = "Date") +
    theme_minimal() +
    theme(axis.title.y.left = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.25, 0.5),
          legend.title = element_blank())
  
# Precipitation graph for NEWPCC
  N2 <- ggplot(newpcc_combined_data) +
    geom_line(aes(Date, newpccResults$`Precip (mm)`, color = precipColour)) +
    scale_y_reverse(position = "right",
                    limits = c(20,0),
                    breaks = c(0,0.25,0.5),
                    labels = c(0,0.25,0.5),
                    expand = c(0,0)) +
    scale_color_manual(values = c("black")) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Precipitation [mm]", x = "") +
    theme_minimal() +
    theme(axis.title.y.right = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.75, 0.5),
          legend.title = element_blank())
  
# Combine graphs
  aligned_plots <- align_plots(N1, N2, align = "hv", axis = "tblr")
  N3 <- ggdraw(aligned_plots[[1]]) + draw_plot(aligned_plots[[2]]) 
  
# Modify legend and add title
  N3 <- N3 +
    theme(plot.title = element_text(hjust = 0.5)) +  
    guides(color = guide_legend(title = "NEWPCC Results")) +  
    labs(title = "NEWPCC")
 
# Filter 24 hour period from study period
start_date24hr <- ymd_hms('2022-08-18 00:00:00')
end_date24hr <- start_date24hr + days(2)
  
newpccResults_24h <- newpccResults %>%
  filter(Date >= start_date24hr & Date < end_date24hr)

newpccResults_24h <- newpccResults_24h %>%
  mutate(Flow_scaled = `Flow (cms)` /coeff)

N4 <- ggplot(newpccResults_24h) +
  geom_line(aes(Date, Flow_scaled, color = flowColour)) +
  scale_y_continuous(position = "left",
                     limits = c(0, 1),
                     expand = c(0,0)) +
  scale_color_manual(values = c("sienna1")) +
  guides(x = guide_axis(angle = 90)) +
  labs(y = "Flow [cms]",
       x = "Date") +
  theme_minimal() +
  theme(axis.title.y.left = element_text(hjust = 0),
        legend.position = "bottom",
        legend.justification = c(0.25, 0.5),
        legend.title = element_blank())

# Precipitation graph for 24 hours
N5 <- ggplot(newpccResults_24h) +
  geom_line(aes(Date, `Precip (mm)`, color = precipColour)) +
  scale_y_reverse(position = "right",
                  limits = c(10,0),
                  breaks = c(0,0.5,1),
                  labels = c(0,0.5,1),
                  expand = c(0,0)) +
  scale_color_manual(values = c("black")) +
  guides(x = guide_axis(angle = 90)) +
  labs(y = "Precipitation [mm]", x = "") +
  theme_minimal() +
  theme(axis.title.y.right = element_text(hjust = 0),
        legend.position = "bottom",
        legend.justification = c(0.75, 0.5),
        legend.title = element_blank())

# Combine graphs
aligned_plots <- align_plots(N4, N5, align = "hv", axis = "tblr")
N6 <- ggdraw(aligned_plots[[1]]) + draw_plot(aligned_plots[[2]]) 

# Modify legend and add title
N6 <- N6 +
  theme(plot.title = element_text(hjust = 0.5)) +  
  guides(color = guide_legend(title = "NEWPCC Results")) +  
  labs(title = "NEWPCC")
  
#SEWPCC PLOTS
  
  sewpcc_combined_data <- cbind(sewpccResults, Flow_scaled = sewpccResults$`Flow (cms)` / coeff)
  
# Flow hydrograph for SEWPCC
  S1 <- ggplot(sewpcc_combined_data) +
    geom_line(aes(Date, Flow_scaled, color = flowColour)) +
    scale_y_continuous(position = "left",
                       limits = c(0, 1),
                       expand = c(0,0)) +
    scale_color_manual(values = flowColour) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Flow [cms]",
         x = "Date") +
    theme_minimal() +
    theme(axis.title.y.left = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.25, 0.5),
          legend.title = element_blank())
  
# Precipitation graph for SEWPCC
  S2 <- ggplot(sewpcc_combined_data) +
    geom_line(aes(Date, sewpccResults$`Precip (mm)`, color = precipColour)) +
    scale_y_reverse(position = "right",
                    limits = c(20,0),
                    breaks = c(0,0.25,0.5),
                    labels = c(0,0.25,0.5),
                    expand = c(0,0)) +
    scale_color_manual(values = c("black")) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Precipitation [mm]", x = "") +
    theme_minimal() +
    theme(axis.title.y.right = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.75, 0.5),
          legend.title = element_blank())
  
# Combine graphs
  aligned_plots <- align_plots(S1,S2 , align = "hv", axis = "tblr")
  S3 <- ggdraw(aligned_plots[[1]]) + draw_plot(aligned_plots[[2]]) 
  
# Modify legend and add title
    S3 <- S3 +
    theme(plot.title = element_text(hjust = 0.5)) + 
    guides(color = guide_legend(title = "SEWPCC Results")) +  
    labs(title = "SEWPCC")  
    
# Filter 24 hour period from study period
    sewpccResults_24h <- sewpccResults %>%
      filter(Date >= start_date24hr & Date < end_date24hr)
    
    sewpccResults_24h <- sewpccResults_24h %>%
      mutate(Flow_scaled = `Flow (cms)` /coeff)
    
    S4 <- ggplot(sewpccResults_24h) +
      geom_line(aes(Date, Flow_scaled, color = flowColour)) +
      scale_y_continuous(position = "left",
                         limits = c(0, 1),
                         expand = c(0,0)) +
      scale_color_manual(values = flowColour) +
      guides(x = guide_axis(angle = 90)) +
      labs(y = "Flow [cms]",
           x = "Date") +
      theme_minimal() +
      theme(axis.title.y.left = element_text(hjust = 0),
            legend.position = "bottom",
            legend.justification = c(0.25, 0.5),
            legend.title = element_blank())
    
    # Precipitation graph for 24 hours
    S5 <- ggplot(sewpccResults_24h) +
      geom_line(aes(Date, `Precip (mm)`, color = precipColour)) +
      scale_y_reverse(position = "right",
                      limits = c(10,0),
                      breaks = c(0,0.5,1),
                      labels = c(0,0.5,1),
                      expand = c(0,0)) +
      scale_color_manual(values = c("black")) +
      guides(x = guide_axis(angle = 90)) +
      labs(y = "Precipitation [mm]", x = "") +
      theme_minimal() +
      theme(axis.title.y.right = element_text(hjust = 0),
            legend.position = "bottom",
            legend.justification = c(0.75, 0.5),
            legend.title = element_blank())
    
    # Combine graphs
    aligned_plots <- align_plots(S4, S5, align = "hv", axis = "tblr")
    S6 <- ggdraw(aligned_plots[[1]]) + draw_plot(aligned_plots[[2]]) 
    
    # Modify legend and add title
    S6 <- S6 +
      theme(plot.title = element_text(hjust = 0.5)) +  
      guides(color = guide_legend(title = "SEWPCC Results")) +  
      labs(title = "SEWPCC")
  
  #WEWPCC PLOTS

  wewpcc_combined_data <- cbind(wewpccResults, Flow_scaled = wewpccResults$`Flow (cms)` / coeff)
  
# Flow hydrograph for WEWPCC
  W1 <- ggplot(wewpcc_combined_data) +
    geom_line(aes(Date, Flow_scaled, color = flowColour)) +
    scale_y_continuous(position = "left",
                       limits = c(0, 1),
                       expand = c(0,0)) +
    scale_color_manual(values = c("steelblue")) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Flow [cms]",
         x = "Date") +
    theme_minimal() +
    theme(axis.title.y.left = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.25, 0.5),
          legend.title = element_blank())
  
# Precipitation graph for SEWPCC
  W2 <- ggplot(wewpcc_combined_data) +
    geom_line(aes(Date, wewpccResults$`Precip (mm)`, color = precipColour)) +
    scale_y_reverse(position = "right",
                    limits = c(20,0),
                    breaks = c(0,0.25,0.5),
                    labels = c(0,0.25,0.5),
                    expand = c(0,0)) +
    scale_color_manual(values = c("black")) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Precipitation [mm]", x = "") +
    theme_minimal() +
    theme(axis.title.y.right = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.75, 0.5),
          legend.title = element_blank())
  
# Combine graphs
  aligned_plots <- align_plots(W1, W2, align = "hv", axis = "tblr")
  W3 <- ggdraw(aligned_plots[[1]]) + draw_plot(aligned_plots[[2]])
  
# Modify legend and add title
  W3 <- W3 +
    theme(plot.title = element_text(hjust = 0.5)) +  
    guides(color = guide_legend(title = "WEWPCC Results")) +  
    labs(title = "WEWPCC")  

# Filter 24 hour period from study period
  wewpccResults_24h <- wewpccResults %>%
    filter(Date >= start_date24hr & Date < end_date24hr)
  
  wewpccResults_24h <- wewpccResults_24h %>%
    mutate(Flow_scaled = `Flow (cms)` /coeff)
  
  W4 <- ggplot(wewpccResults_24h) +
    geom_line(aes(Date, Flow_scaled, color = flowColour)) +
    scale_y_continuous(position = "left",
                       limits = c(0, 1),
                       expand = c(0,0)) +
    scale_color_manual(values = c("steelblue")) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Flow [cms]",
         x = "Date") +
    theme_minimal() +
    theme(axis.title.y.left = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.25, 0.5),
          legend.title = element_blank())
  
  # Precipitation graph for 24 hours
  W5 <- ggplot(newpccResults_24h) +
    geom_line(aes(Date, `Precip (mm)`, color = precipColour)) +
    scale_y_reverse(position = "right",
                    limits = c(10,0),
                    breaks = c(0,0.5,1),
                    labels = c(0,0.5,1),
                    expand = c(0,0)) +
    scale_color_manual(values = c("black")) +
    guides(x = guide_axis(angle = 90)) +
    labs(y = "Precipitation [mm]", x = "") +
    theme_minimal() +
    theme(axis.title.y.right = element_text(hjust = 0),
          legend.position = "bottom",
          legend.justification = c(0.75, 0.5),
          legend.title = element_blank())
  
  # Combine graphs
  aligned_plots <- align_plots(W4, W5, align = "hv", axis = "tblr")
  W6 <- ggdraw(aligned_plots[[1]]) + draw_plot(aligned_plots[[2]]) 
  
  # Modify legend and add title
  W6 <- W6 +
    theme(plot.title = element_text(hjust = 0.5)) +  
    guides(color = guide_legend(title = "WEWPCC Results")) +  
    labs(title = "WEWPCC")
  
  combined_plots <- ggarrange(N3, S3, W3, ncol = 3,nrow = 1,
                             legend = "none", 
                             common.legend = FALSE) +
                             facet_wrap(~.)


  combined_plots24h <- ggarrange(N6, S6, W6, ncol = 3,nrow = 1,
                              legend = "none", 
                              common.legend = FALSE) +
                              facet_wrap(~.)
  
  ggsave("combinedplots.png", plot = combined_plots, bg = "white")
  ggsave("combinedplots_24hr.png", plot = combined_plots24h, bg = "white")
  

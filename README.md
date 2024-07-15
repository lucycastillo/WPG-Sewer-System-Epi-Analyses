**Project Description**
-------------------------------------------------------------------
Project aims to design and develop an in-sewer viral fate and transport model
for an existing conceptual hydraulic model based on the City of Winnipeg wastewater
system. Conceptual model was developed in the U.S Environmental Protection Agency's
Stormwater Management Model (EPA-SWMM). The pyswmm library was used to interact with software,
analyze the system and calibrate the model. 

**Execution**
-------------------------------------------------------------------
The scripts should be launched in this order:
- `concp_WPG_Precip_FlowPlot.R` : Creates combined flow hydrograph and hyetograph.
- `HRT-Concp-Mod.R` : Processes time series data from EPA-SWMM and conducts network analyses to determine shortest node-to-outfall path. Illustrates hydraulic residence time for each path using bar, box and distribution plots.
- `calibration_HRT.py` : Calibrates model.
- `model_wTSS.py` : Simulates transport of TSS to study agent of concern, SARS-CoV-2.

**Required data**
--------------------------------------------------------------------
- City of Winnipeg conceptual model : _wpg_cm.inp_
- Rainfall data : _precip.dat_

import networkx as nx
import itertools as it
import pandas as pd
import sdf
import os
from tree import Tree
from pyToMod import PyToMod
import numpy as np

# Prüfer code generation
n = 4 # number of stations (supply or building) in district
sequences = []
for comb in it.combinations_with_replacement(range(n), n-2) :
    for perm in it.permutations(comb) :
        sequences.append(perm)
P_list = list(set(sequences))

def create_G(supply_name) :
    '''
    returns initialized model 
    networkx graph with arbitrary positions
    no edges between nodes yet
    one source
    building 1 needs heat for heating
    building 2 needs heat for DHW
    building 3 needs heat for both heating and DHW
    '''
    G = nx.Graph()
    G.add_nodes_from([supply_name]+['Building_'+str(i) for i in range(1,n)])
    nx.set_node_attributes(G, {supply_name : {'pos':(0,0)},
		'Building_1' : {'pos':(0,200), 'T_heating':45, 'T_DHW':0},
		'Building_2' : {'pos':(200,100), 'T_heating':0, 'T_DHW':60}, 
		'Building_3' : {'pos':(300,200), 'T_heating':45, 'T_DHW':60},		
		})
    nx.set_node_attributes(G, False, 'is_supply_heating')
    G.nodes[supply_name]['is_supply_heating'] = True
    return G

def ring(supply_name) :
    '''
    returns initialized ring model
    networkx graph with arbitrary positions
    creates edges in order to form a loop
    building 1 needs heat for heating
    building 2 needs heat for DHW
    building 3 needs heat for both heating and DHW
    '''
    G_ring = create_G(supply_name)
    G_ring.add_edge(supply_name, 'Building_1')
    G_ring.add_edge('Building_1', 'Building_2')
    G_ring.add_edge('Building_2', 'Building_3')
    G_ring.add_edge('Building_3', supply_name)
    nx.set_edge_attributes(G_ring, 'a', 'direction')
    return G_ring


# specific parameters to each source for simulation
# n_pipes=1
source_param_1 = {'gas_boiler': {'names' : ['constant_supply_gas_boiler.k'], 
        'val' : [273.15+65]},
    'heat_pump' : {'names' : ['constant_supply_heat_pump.k', 'source_sea_supply_heat_pump.T', 'source_sea_supply_heat_pump.m_flow', 'sink_sea_supply_heat_pump.p'], 
        'val' : [273.15+65, 273.15+15, 5, 1e5]}, 
    'gas_boiler_geo' : {'names' : ['constant_supply_gas_boiler_geo.k', 'source_geo_supply_gas_boiler_geo.T', 'source_geo_supply_gas_boiler_geo.m_flow', 'sink_geo_supply_gas_boiler_geo.p'], 
        'val' : [273.15+65, 273.15+60, 5, 2e5]},
    'geo_heat_pump' : {'names' :['constant_supply_geo_heat_pump.k', 'source_sea_supply_geo_heat_pump.T', 'source_sea_supply_geo_heat_pump.m_flow', 'sink_sea_supply_geo_heat_pump.p', 'source_geo_supply_geo_heat_pump.T', 'source_geo_supply_geo_heat_pump.m_flow', 'sink_geo_supply_geo_heat_pump.p'],
        'val' : [273.15+65, 273.15+15, 5, 1e5, 273.15+60, 5, 2e5]},
    'heat_pump_gas_boiler' : {'names' : ['const_supply_heat_pump_gas_boiler.k', 'constant_supply_heat_pump_gas_boiler.k', 'source_sea_supply_heat_pump_gas_boiler.T', 'source_sea_supply_heat_pump_gas_boiler.m_flow', 'sink_sea_supply_heat_pump_gas_boiler.p'],
        'val' : [273.15+50, 273.15+65, 273.15+15, 5, 1e5]},
    'simple_source' : {'names' : [], 'val' : []}
    }

# n_pipes=2
source_param_2 = {'gas_boiler': {'names' : ['constant_supply_gas_boiler.k'], 
        'val' : [273.15+65]},
    'heat_pump' : {'names' : ['constant_supply_heat_pump.k', 'source_sea_supply_heat_pump.T', 'source_sea_supply_heat_pump.m_flow', 'sink_sea_supply_heat_pump.p'], 
        'val' : [273.15+65, 273.15+15, 5, 1e5]}, 
    'gas_boiler_geo' : {'names' : ['constant_supply_gas_boiler_geo.k', 'source_geo_supply_gas_boiler_geo.T', 'source_geo_supply_gas_boiler_geo.m_flow', 'sink_geo_supply_gas_boiler_geo.p'], 
        'val' : [273.15+65, 273.15+60, 5, 2e5]},
    'geo_heat_pump' : {'names' :['constant_supply_geo_heat_pump.k', 'source_sea_supply_geo_heat_pump.T', 'source_sea_supply_geo_heat_pump.m_flow', 'sink_sea_supply_geo_heat_pump.p', 'source_geo_supply_geo_heat_pump.T', 'source_geo_supply_geo_heat_pump.m_flow', 'sink_geo_supply_geo_heat_pump.p'],
        'val' : [273.15+65, 273.15+15, 5, 1e5, 273.15+60, 5, 2e5]},
    'heat_pump_gas_boiler' : {'names' : ['const_supply_heat_pump_gas_boiler.k', 'constant_supply_heat_pump_gas_boiler.k', 'source_sea_supply_heat_pump_gas_boiler.T', 'source_sea_supply_heat_pump_gas_boiler.m_flow', 'sink_sea_supply_heat_pump_gas_boiler.p'],
        'val' : [273.15+50, 273.15+65, 273.15+15, 5, 1e5]},
    'simple_source' : {'names' : [], 'val' : []}
    }

# n_pipes=3
source_param_3 = {'gas_boiler': {'names' : ['constant_supply_gas_boiler.k', 'constant_Lsupply_gas_boiler.k'], 
        'val' : [273.15+65, 273.15+50]},
    'heat_pump' : {'names' : ['constant_supply_heat_pump.k', 'source_sea_supply_heat_pump.T', 'source_sea_supply_heat_pump.m_flow', 'sink_sea_supply_heat_pump.p', 'constantL_supply_heat_pump.k', 'source_seaL_supply_heat_pump.T', 'source_seaL_supply_heat_pump.m_flow', 'sink_seaL_supply_heat_pump.p'], 
        'val' : [273.15+65, 273.15+15, 5, 1e5, 273.15+50, 273.15+15, 5, 1e5]}, 
    'gas_boiler_geo' : {'names' : ['constant_supply_gas_boiler_geo.k', 'constant_Lsupply_gas_boiler_geo.k', 'source_geo_supply_gas_boiler_geo.T', 'source_geoL_supply_gas_boiler_geo.T', 'source_geo_supply_gas_boiler_geo.m_flow', 'source_geoL_supply_gas_boiler_geo.m_flow', 'sink_geo_supply_gas_boiler_geo.p', 'sink_geoL_supply_gas_boiler_geo.p'], 
        'val' : [273.15+65, 273.15+50, 273.15+60, 273.15+60, 5, 5, 2e5, 2e5]},
    'geo_heat_pump' : {'names' :['constant_supply_geo_heat_pump.k', 'source_sea_supply_geo_heat_pump.T', 'source_sea_supply_geo_heat_pump.m_flow', 'sink_sea_supply_geo_heat_pump.p', 'source_geo_supply_geo_heat_pump.T', 'source_geo_supply_geo_heat_pump.m_flow', 'sink_geo_supply_geo_heat_pump.p', 'constantL_supply_geo_heat_pump.k', 'source_seaL_supply_geo_heat_pump.T', 'source_seaL_supply_geo_heat_pump.m_flow', 'sink_seaL_supply_geo_heat_pump.p', 'source_geoL_supply_geo_heat_pump.T', 'source_geoL_supply_geo_heat_pump.m_flow', 'sink_geoL_supply_geo_heat_pump.p'],
        'val' : [273.15+65, 273.15+15, 5, 1e5, 273.15+60, 5, 2e5, 273.15+50, 273.15+15, 5, 1e5, 273.15+60, 5, 2e5]},
    'heat_pump_gas_boiler' : {'names' : ['const_supply_heat_pump_gas_boiler.k', 'constant_supply_heat_pump_gas_boiler.k', 'source_sea_supply_heat_pump_gas_boiler.T', 'source_sea_supply_heat_pump_gas_boiler.m_flow', 'sink_sea_supply_heat_pump_gas_boiler.p', 'constL_supply_heat_pump_gas_boiler.k', 'constant_Lsupply_heat_pump_gas_boiler.k', 'source_seaL_supply_heat_pump_gas_boiler.T', 'source_seaL_supply_heat_pump_gas_boiler.m_flow', 'sink_seaL_supply_heat_pump_gas_boiler.p'],
        'val' : [273.15+50, 273.15+65, 273.15+15, 5, 1e5, 273.15+50, 273.15+50, 273.15+15, 5, 1e5]},
    'simple_source' : {'names' : [], 'val' : []}
    }

# specific variables to read at the end of the simulation
# n_pipes=1
source_results_1 = {'gas_boiler' : {'component' : ['boiler_supply_gas_boiler'], 'var' : ['QFue_flow']},
    'heat_pump' : {'component' : ['HP_supply_heat_pump'], 'var' : ['P']},
    'gas_boiler_geo' : {'component' : ['boiler_supply_gas_boiler'], 'var' :['QFue_flow']},
    'geo_heat_pump' : {'component' : ['HP_supply_geo_heat_pump'], 'var' : ['P']},
    'heat_pump_gas_boiler' : {'component' : ['boiler_supply_heat_pump_gas_boiler', 'HP_supply_heat_pump_gas_boiler'], 'var' : ['QFue_flow', 'P']}  
    }

# n_pipes=2
source_results_2 = {'gas_boiler' : {'component' : ['boiler_supply_gas_boiler'], 'var' : ['QFue_flow']},
    'heat_pump' : {'component' : ['HP_supply_heat_pump'], 'var' : ['P']},
    'gas_boiler_geo' : {'component' : ['boiler_supply_gas_boiler_geo'], 'var' :['QFue_flow']},
    'geo_heat_pump' : {'component' : ['HP_supply_geo_heat_pump'], 'var' : ['P']},
    'heat_pump_gas_boiler' : {'component' : ['boiler_supply_heat_pump_gas_boiler', 'HP_supply_heat_pump_gas_boiler'], 'var' : ['QFue_flow', 'P']}  
    }

# n_pipes=3
source_results_3 = {'gas_boiler' : {'component' : ['boiler_supply_gas_boiler', 'boilerL_supply_gas_boiler'], 'var' : ['QFue_flow', 'QFue_flow']},
    'heat_pump' : {'component' : ['HP_supply_heat_pump', 'HPL_supply_heat_pump'], 'var' : ['P', 'P']},
    'gas_boiler_geo' : {'component' : ['boiler_supply_gas_boiler_geo', 'boilerL_supply_gas_boiler_geo'], 'var' :['QFue_flow', 'QFue_flow']},
    'geo_heat_pump' : {'component' : ['HP_supply_geo_heat_pump', 'HPL_supply_geo_heat_pump'], 'var' : ['P', 'P']},
    'heat_pump_gas_boiler' : {'component' : ['boiler_supply_heat_pump_gas_boiler', 'HP_supply_heat_pump_gas_boiler', 'boilerL_supply_heat_pump_gas_boiler', 'HPL_supply_heat_pump_gas_boiler'], 'var' : ['QFue_flow', 'P', 'QFue_flow', 'P']}  
    } 

source_param = [source_param_1, source_param_2, source_param_3]
source_results = [source_results_1, source_results_2, source_results_3]
sources = ['gas_boiler', 'heat_pump', 'heat_pump_gas_boiler', 'geo_heat_pump', 'gas_boiler_geo']


from pathlib import Path
working_dir = Path(os.getcwd())

import sys
sys.path.insert(0, os.path.join(working_dir, 'Dymola', 'interface', 'dymola.egg'))
from dymola.dymola_interface import DymolaInterface
from dymola.dymola_exception import DymolaException
dymola = None
path = os.path.join(working_dir, 'Method.mo')


# initialization of data, that will contain all usefull variables from simulation
data = []


# we first create and simulate model_ring alone
# values initialization 
model_id = 'model_sea_ring'
n_pipes = 1
gas_boiler = False
heat_pump = False
geothermal = False
gas_P = np.nan
HP_P = np.nan
geo_P = np.nan
indiv_HP_P = np.nan
pump_P = np.nan
                
G = ring('sea')
pos = nx.get_node_attributes(G, 'pos')

model_name = 'Method.model_sea_ring'
model = PyToMod(G, 'model_sea_ring')
model.set_source('sea')
model.set_n_pipes(1)
print(model.write_in_file('Method.mo'))
L = model.pipe_length()

# Instantiate the Dymola interface and start Dymola and load models, update this line according to the installation folder of Dymola
dymola = DymolaInterface(os.path.join('C:\Program Files\Dymola 2021x', 'bin64', 'Dymola.exe'))

# Load the library, it may take time, depending on the size of the loaded file
ok = dymola.openModel(path=os.path.join(working_dir, 'Dymola', 'Buildings-v9.0.0', 'Buildings 9.0.0', 'package.mo'), changeDirectory=False)
print('Loading OK? : ', ok)

ok = dymola.openModel(path=os.path.join(working_dir, 'Method.mo'), changeDirectory=False)
print('Loading OK? : ', ok)

# Set up the parameters and simulate the model
resultFile = 'res'

init_names =[]
init_val = []

# Building_1 (water for heating)
init_names += ['source_SST_Building_1.m_flow', 'source_SST_Building_1.T', 'sink_SST_Building_1.p', 'constant_SST_Building_1.k']
init_val += [1, 273.15+40, 2e5, 273.15+45]

# Building_2 (hot domestic water)
init_names += ['source_SST_Building_2.m_flow', 'source_SST_Building_2.T', 'sink_SST_Building_2.p', 'constant_SST_Building_2.k']
init_val += [1, 273.15+12, 2e5, 273.15+60]

# Building_3 (both)
init_names += ['source_W_SST_Building_3.m_flow', 'source_W_SST_Building_3.T', 'sink_W_SST_Building_3.p', 'constant_W_SST_Building_3.k']
init_val += [1, 273.15+12, 2e5, 273.15+60]
init_names += ['source_H_SST_Building_3.m_flow', 'source_H_SST_Building_3.T', 'sink_H_SST_Building_3.p', 'constant_H_SST_Building_3.k']
init_val += [1, 273.15+40, 2e5, 273.15+45]

# Fluid circulation
init_names += ['prod_supply_sea.p', 'sink_supply_sea.p']
init_val += [5e5, 1e5]

# Heat source
init_names += ['source_sea_supply_sea.m_flow', 'source_sea_supply_sea.T', 'sink_sea_supply_sea.p'] 
init_val += [5, 273.15+15, 2e5]


ok, values = dymola.simulateExtendedModel(problem=model_name, resultFile=resultFile,\
            startTime=0.0, stopTime=6000, numberOfIntervals=100, \
            initialNames=init_names, initialValues=init_val)   
print(ok)

if not ok :
    print("Simulation failed. Below is the translation log.")
    log = dymola.getLastErrorLog()
    print(log)
            
if dymola is not None:
    dymola.close()
    dymola = None

# Extract the results
res = sdf.load(os.path.join(working_dir, resultFile+'.mat'))
t = res['Time'].data

components = ['HP_SST_Building_1', 'HP_SST_Building_2', 'HP_W_SST_Building_3', 'HP_H_SST_Building_3',]

# individual HP power
for comp in components :
    l = 0
    # the value is the average of steady state values
    while t[l] < 5400 :
        l += 1
    indiv_HP_P += np.average(res[comp]['P'].data[l:])

# sea pump power
geo_P = 5e2

# pump power
m_flow = res['pipe_Building_1Building_2']['m_flow'].data
dP = 4e5 
pump_P = m_flow*0.001*dP

data.append([model_id, n_pipes, gas_boiler, heat_pump, geothermal, gas_P, HP_P, geo_P, indiv_HP_P, pump_P]) 

df1 = pd.DataFrame(data, columns=['model_id', 'n_pipes', 'gas_boiler', 'heat_pump', 'geothermal', 'gas_P', 'HP_P', 'geo_P', 'indiv_HP_P', 'pump_P'])
df1.to_csv('results1.csv') # save in case the simulation stops


# we then create and simulate all 160 other models

i_range = len(sources)
j_range = len(P_list)
n_range = [2,3]

for n_pipes in n_range :
    for i in range(i_range) :
        for j in range (j_range) :
                print('n_pipes : ', n_pipes)
                print('source : ',sources[i])
                print('configuration ', j)

                # values initialization 
                model_id = 'model_'+sources[i]+'_'+str(n_pipes)+str(j)
                n_pipes = n_pipes
                gas_boiler = False
                heat_pump = False
                geothermal = False
                gas_P = np.nan
                HP_P = np.nan
                geo_P = np.nan
                indiv_HP_P = np.nan
                pump_P = np.nan
                
                G = create_G(sources[i])
                pos = nx.get_node_attributes(G, 'pos')
                T = Tree(G)
                T.construct_tree(list(P_list[j]))

                model_name = 'Method.model_'+sources[i]+'_'+str(n_pipes)+str(j)
                model = PyToMod(G, 'model_'+sources[i]+'_'+str(n_pipes)+str(j))
                model.set_source(sources[i])
                model.set_n_pipes(n_pipes)
                model.write_in_file('Method.mo')
                L = model.pipe_length()

                # Instantiate the Dymola interface and start Dymola and load models, update this line according to the installation folder of Dymola
                dymola = DymolaInterface(os.path.join('C:\Program Files\Dymola 2021x', 'bin64', 'Dymola.exe'))

                # Load the library, it may take time, depending on the size of the loaded file
                ok = dymola.openModel(path=os.path.join(working_dir, 'Dymola', 'Buildings-v9.0.0', 'Buildings 9.0.0', 'package.mo'), changeDirectory=False)
                print('Loading OK? : ', ok)

                ok = dymola.openModel(path=os.path.join(working_dir, 'Method.mo'), changeDirectory=False)
                print('Loading OK? : ', ok)

                # Set up the parameters and simulate the model
                resultFile = 'res'

                init_names =[]
                init_val = []

                # Building_1 (water for heating)
                init_names += ['source_SST_Building_1.m_flow', 'source_SST_Building_1.T', 'sink_SST_Building_1.p', 'constant_SST_Building_1.k']
                init_val += [1, 273.15+40, 2e5, 273.15+45]

                # Building_2 (hot domestic water)
                init_names += ['source_SST_Building_2.m_flow', 'source_SST_Building_2.T', 'sink_SST_Building_2.p', 'constant_SST_Building_2.k']
                init_val += [1, 273.15+12, 2e5, 273.15+60]

                # Building_3 (both)
                init_names += ['source_W_SST_Building_3.m_flow', 'source_W_SST_Building_3.T', 'sink_W_SST_Building_3.p', 'constant_W_SST_Building_3.k']
                init_val += [1, 273.15+12, 2e5, 273.15+60]
                init_names += ['source_H_SST_Building_3.m_flow', 'source_H_SST_Building_3.T', 'sink_H_SST_Building_3.p', 'constant_H_SST_Building_3.k']
                init_val += [1, 273.15+40, 2e5, 273.15+45]

                # Fluid circulation
                init_names += ['prod_supply_'+sources[i]+'.p', 'sink_supply_'+sources[i]+'.p']
                init_val += [5e5, 1e5]

                # Heat source
                init_names += source_param[n_pipes-1][sources[i]]['names'] 
                init_val += source_param[n_pipes-1][sources[i]]['val']


                ok, values = dymola.simulateExtendedModel(problem=model_name, resultFile=resultFile,\
                            startTime=0.0, stopTime=6000, numberOfIntervals=100, \
                            initialNames=init_names, initialValues=init_val)   
                print(ok)

                if not ok :
                    print("Simulation failed. Below is the translation log.")
                    log = dymola.getLastErrorLog()
                    print(log)

                # Extract the results
                res = sdf.load(os.path.join(working_dir, resultFile+'.mat'))
                t = res['Time'].data 

                # Values update
                # source
                if 'gas_boiler' in sources[i] :
                    gas_boiler = True
                if 'heat_pump' in sources[i] :
                    heat_pump = True
                if 'geo' in sources[i] :
                    geothermal = True

                # HP or gas boiler power
                for k in range (len(source_results[n_pipes-1][sources[i]]['component'])) :
                    l = 0
                    while t[l] < 5400 :
                        l += 1
                    P = np.average(res[source_results[n_pipes-1][sources[i]]['component'][k]][source_results[n_pipes-1][sources[i]]['var'][k]].data[l:])
                    if 'HP' in source_results[n_pipes-1][sources[i]]['component'][k] :
                        HP_P = P
                    elif 'boiler' in source_results[n_pipes-1][sources[i]]['component'][k]:
                        gas_P = P

                # geothermal power
                if 'geo' in sources[i] :
                    geo_P = 5e2

                # pump power
                l = 0
                while t[l] < 5400 :
                    l += 1
                m_flow = np.average(res['hex_SST_Building_1']['m1_flow'].data[l:])
                dP = 4e5 
                pump_P = m_flow*dP*0.001
                
                data.append([model_id, n_pipes, gas_boiler, heat_pump, geothermal, gas_P, HP_P, geo_P, indiv_HP_P, pump_P]) 
            
                if dymola is not None:
                    dymola.close()
                    dymola = None
    if n_pipes == 2 :
        df2 = pd.DataFrame(data, columns=['model_id', 'n_pipes', 'gas_boiler', 'heat_pump', 'geothermal', 'gas_P', 'HP_P', 'geo_P', 'indiv_HP_P', 'pump_P'])
        df2.to_csv('results2.csv') # save in case the simulation stops

    if n_pipes == 3 :
        df3 = pd.DataFrame(data, columns=['model_id', 'n_pipes', 'gas_boiler', 'heat_pump', 'geothermal', 'gas_P', 'HP_P', 'geo_P', 'indiv_HP_P', 'pump_P'])
        df3.to_csv('results3.csv') # save in case the simulation stops

df = df1.append(df2.append(df3, ignore_index=True), ignore_index=True)
df.to_csv('results.csv')


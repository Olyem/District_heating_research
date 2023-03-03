# Carefull with the names of the elements
# They must match in port names and variable names
# Examples : hex_SST_1001, source_supply_1005, etc...

# Annotations are just for display in Dymola, they do not influence model behaviour
# If not present, it is impossible to display components or connections once in Dymola

# Some lists are np.narrays, some are python lists, with no particular reason

import numpy as np
import networkx as nx
import os
from arg import arg

class PyToMod :
    graph = nx.DiGraph()
    n_pipes = 2
    dir_list = ['a', 'b', 'aL']

    def __init__(self, graph, model_name='model_python', inplace=False) :
        '''
        graph : networkx DiGraph describing urban heating
        model_name : name of modelica model which will be created
        '''
        self.arg = arg

        if inplace :
            self.graph = graph
        else :
            self.graph = graph.copy() 

        self.model_name = model_name 
        
        # we set all attributes to False at initialization
        names = ['is_built', 'i_port_a', 'i_port_b', 'i_port_aL', 'i_port_bL', 'port_a', 'port_aL', 'port_b']
        val = [False for i in range(len(names))]
        for i in range (len(val)) :
            nx.set_node_attributes(self.graph, val[i], names[i])
        nx.set_edge_attributes(self.graph, False, 'is_built')



    # Script command --------------------------------------

    def script_element(self, name, type, x=0.,y=0., nports=False, length=0, input=False, param='') :
        '''
        Returns a string corresponding to the declaration to a component
        '''
        an = 'annotation (Placement(transformation(extent={{-10,-10},{10,10}}, origin={'+ str(x) + ',' + str(y) + '})))'
        arg = self.arg[type]
        arg += param
        if nports : # in the case of a multiport (e.g mass flow source)
            arg += 'nPorts='+str(nports)+'\n'
            return str(type) + ' ' + str(name) + ' (\n  ' + arg + ') \n' + an +';\n'
        elif length : # in the case of a pipe
            arg += 'length='+str(length)+'\n'
            return str(type) + ' ' + str(name) + ' (\n  ' + arg + ') \n' + an +';\n'
        elif input : # in the case of an input component
            arg += 'y='+input
            return str(type) + ' ' + str(name) + ' (\n  ' + arg + ') \n' + an +';\n'
        else :
            return str(type) + ' ' + str(name) + ' (\n  ' + arg + ') \n' + an +';\n'
        

    def script_substation(self, name, x=0.,y=0., T=0, heat_pump=False) :
        '''
        Return modelica script to build a substation
        In the form of a list : first element corresponds to declaration, second element corresponds to connection
        '''

        # two elements list [name, script]
        source = np.array(['source_'+name, self.script_element('source_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', x+10,y-10, nports=1)]) 
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', x-10,y-10, nports=1)]) 
        
        # random annotation to allow visualization in Dymola
        an = 'annotation (Line(points={{' + str(x) + ',' + str(y) + '}},color={0,127,255}))'
        connections = ''

        if heat_pump : # in the case of circular grid, each substation has a heat pump
            HP = np.array(['HP_'+name, self.script_element('HP_'+name, 'Buildings.Fluid.HeatPumps.Carnot_TCon')])
            const = np.array(['constant_'+name, self.script_element('constant_'+name, 'Modelica.Blocks.Sources.Constant')])
            connections += 'connect('+source[0]+'.ports[1], '+HP[0]+'.port_a2);\n' 
            connections += 'connect('+HP[0]+'.port_b2, '+sink[0]+'.ports[1]);\n' 
            connections += 'connect('+const[0]+'.y, '+HP[0]+'.TSet);\n'
            declar = source[1] + sink[1] + HP[1] + const[1]

        else : # for n_pipes=2 or 3, each substation has a valve and a heat exchanger
            hex = np.array(['hex_'+name, self.script_element('hex_'+name, 'Buildings.Fluid.HeatExchangers.PlateHeatExchangerEffectivenessNTU', x,y+10)])
            valv = self.script_element('valve_'+name, 'Buildings.Fluid.Actuators.Valves.TwoWayLinear')
            cont = self.script_controller(name, input=hex[0]+'.sta_b2.T', T=T)
            connections += 'connect('+source[0]+'.ports[1], '+hex[0]+'.port_a2)\n    ' + an + ';\n'
            connections += 'connect('+hex[0]+'.port_b2, '+sink[0]+'.ports[1])\n    ' + an + ';\n'    
            connections += cont[2]
            connections += 'connect('+cont[0]+'.y, valve_'+name+'.y);\n'
            connections += 'connect(valve_'+name+'.port_b, '+hex[0]+'.port_a1);\n' 
            declar = source[1] + sink[1] + hex[1] + cont[1] + valv

        return [declar, connections]


    def script_simple_source(self, name, x=0,y=0, nports=1) :
        """
        Imaginary source only for testing
        """

        # fluid circulation
        prod = np.array(['prod_'+name, self.script_element('prod_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        prodL = np.array(['prodL_'+name, self.script_element('prodL_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        term = np.array(['temp_return_'+name, self.script_element('temp_return_'+name, 'Buildings.Fluid.Sensors.Temperature')])

        connections = ''
        connections += 'connect('+sink[0]+'.ports[1], '+term[0]+'.port);\n'
        connections += 'connect('+prod[0]+'.T_in, '+term[0]+'.T);\n'

        return [prod[1] + prodL[1] + sink[1] + term[1], connections]

    def script_gas_boiler(self, name, x=0,y=0, nports=1) :
        '''
        Return modelica script to build a gas boiler source
        In the form of a list : first element corresponds to declaration, second element corresponds to connection
        '''

        # fluid circulation
        prod = np.array(['prod_'+name, self.script_element('prod_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=max(1,self.n_pipes-1))])
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        term = np.array(['temp_return_'+name, self.script_element('temp_return_'+name, 'Buildings.Fluid.Sensors.Temperature')])
        
        # gas boiler
        boil = np.array(['boiler_'+name, self.script_element('boiler_'+name, 'Buildings.Fluid.Boilers.BoilerPolynomial')])
        cont = self.script_controller(name, input=boil[0]+'.sta_b.T')


        connections = ''
        connections += 'connect('+sink[0]+'.ports[1], '+term[0]+'.port);\n'
        connections += 'connect('+prod[0]+'.T_in, '+term[0]+'.T);\n'
        connections += 'connect('+prod[0]+'.ports[1], '+boil[0]+'.port_a);\n'
        connections += cont[2]
        connections += 'connect('+cont[0]+'.y, '+boil[0]+'.y);\n'

        if self.n_pipes == 3 :
            # we add a gas boiler
            # we add 'L' next to all names
            boilL = np.array(['boilerL_'+name, self.script_element('boilerL_'+name, 'Buildings.Fluid.Boilers.BoilerPolynomial')])
            contL = self.script_controller('L'+name, input=boilL[0]+'.sta_b.T')
            connections += 'connect('+prod[0]+'.ports[2], '+boilL[0]+'.port_a);\n'
            connections += contL[2]
            connections += 'connect('+contL[0]+'.y, '+boilL[0]+'.y);\n'
            return [boil[1] + cont[1] + boilL[1] + contL[1] + prod[1] + sink[1] + term[1], connections]

        return [boil[1] + cont[1] + prod[1] + sink[1] + term[1], connections]

    def script_gas_boiler_geo(self, name, x=0,y=0, nports=1) :
        '''
        Return modelica script to build a combined source gas boiler + geothermal
        In the form of a list : first element corresponds to declaration, second element corresponds to connection
        '''

        # fluid circulation
        prod = np.array(['prod_'+name, self.script_element('prod_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=max(1,self.n_pipes-1))])
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        term = np.array(['temp_return_'+name, self.script_element('temp_return_'+name, 'Buildings.Fluid.Sensors.Temperature')])
        
        # gas boiler
        boil = np.array(['boiler_'+name, self.script_element('boiler_'+name, 'Buildings.Fluid.Boilers.BoilerPolynomial')])
        cont = self.script_controller(name, input=boil[0]+'.sta_b.T')
        
        # geothermal
        hex = np.array(['hex_'+name, self.script_element('hex_'+name, 'Buildings.Fluid.HeatExchangers.PlateHeatExchangerEffectivenessNTU')])
        source_geo = np.array(['source_geo_'+name, self.script_element('source_geo_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
        sink_geo = np.array(['sink_geo_'+name, self.script_element('sink_geo_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])

        W = boil[1] + prod[1] + sink[1] + term[1] + cont[1] + hex[1] + source_geo[1] + sink_geo[1]

        connections = ''
        connections += 'connect('+sink[0]+'.ports[1], '+term[0]+'.port);\n'
        connections += 'connect('+prod[0]+'.T_in, '+term[0]+'.T);\n'
        connections += 'connect('+prod[0]+'.ports[1], '+hex[0]+'.port_a1);\n'
        connections += 'connect('+hex[0]+'.port_b1, '+boil[0]+'.port_a);\n'
        connections += 'connect('+source_geo[0]+'.ports[1], '+hex[0]+'.port_a2);\n'
        connections += 'connect('+hex[0]+'.port_b2, '+sink_geo[0]+'.ports[1]);\n'
        connections += cont[2]
        connections += 'connect('+cont[0]+'.y, '+boil[0]+'.y);\n'

        if self.n_pipes == 3 :
            # gas boiler
            boilL = np.array(['boilerL_'+name, self.script_element('boilerL_'+name, 'Buildings.Fluid.Boilers.BoilerPolynomial')])
            contL = self.script_controller('L'+name, input=boil[0]+'.sta_b.T')
            
            # geothermal
            hexL = np.array(['hexL_'+name, self.script_element('hexL_'+name, 'Buildings.Fluid.HeatExchangers.PlateHeatExchangerEffectivenessNTU')])
            source_geoL = np.array(['source_geoL_'+name, self.script_element('source_geoL_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
            sink_geoL = np.array(['sink_geoL_'+name, self.script_element('sink_geoL_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])

            connections += 'connect('+source_geoL[0]+'.ports[1], '+hexL[0]+'.port_a2);\n'
            connections += 'connect('+hexL[0]+'.port_b2, '+sink_geoL[0]+'.ports[1]);\n'
            connections += 'connect('+prod[0]+'.ports[2], '+hexL[0]+'.port_a1);\n'
            connections += contL[2]
            connections += 'connect('+contL[0]+'.y, '+boilL[0]+'.y);\n'

            H = boilL[1] + contL[1] + hexL[1] + source_geoL[1] + sink_geoL[1]
            return [W + H, connections]

        return [W, connections]

    def script_heat_pump(self, name, x=0,y=0, nports=1) :
        '''
        Return modelica script to build a heat pump source
        In the form of a list : first element corresponds to declaration, second element corresponds to connection
        '''
        
        # Fluid circulation
        prod = np.array(['prod_'+name, self.script_element('prod_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=max(1,self.n_pipes-1))])
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        term = np.array(['temp_return_'+name, self.script_element('temp_return_'+name, 'Buildings.Fluid.Sensors.Temperature')])

        # heat pump
        HP = np.array(['HP_'+name, self.script_element('HP_'+name, 'Buildings.Fluid.HeatPumps.Carnot_TCon')])
        source_sea = np.array(['source_sea_'+name, self.script_element('source_sea_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
        sink_sea = np.array(['sink_sea_'+name, self.script_element('sink_sea_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])
        const = np.array(['constant_'+name, self.script_element('constant_'+name, 'Modelica.Blocks.Sources.Constant')])

        W = HP[1] + const[1] + prod[1] + sink[1] + term[1] + source_sea[1] + sink_sea[1]

        connections = ''
        connections += 'connect('+sink[0]+'.ports[1], '+term[0]+'.port);\n'
        connections += 'connect('+prod[0]+'.T_in, '+term[0]+'.T);\n'
        connections += 'connect('+prod[0]+'.ports[1], '+HP[0]+'.port_a1);\n'
        connections += 'connect('+source_sea[0]+'.ports[1], '+HP[0]+'.port_a2);\n'
        connections += 'connect('+HP[0]+'.port_b2, '+sink_sea[0]+'.ports[1]);\n'
        connections += 'connect('+const[0]+'.y, '+HP[0]+'.TSet);\n'

        if self.n_pipes == 3 :
            # heat pump
            HPL = np.array(['HPL_'+name, self.script_element('HPL_'+name, 'Buildings.Fluid.HeatPumps.Carnot_TCon')])
            source_seaL = np.array(['source_seaL_'+name, self.script_element('source_seaL_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
            sink_seaL = np.array(['sink_seaL_'+name, self.script_element('sink_seaL_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])
            constL = np.array(['constantL_'+name, self.script_element('constantL_'+name, 'Modelica.Blocks.Sources.Constant')])
            L = HPL[1] + source_seaL[1] + sink_seaL[1] + constL[1]

            connections += 'connect('+prod[0]+'.ports[2], '+HPL[0]+'.port_a1);\n'
            connections += 'connect('+source_seaL[0]+'.ports[1], '+HPL[0]+'.port_a2);\n'
            connections += 'connect('+HPL[0]+'.port_b2, '+sink_seaL[0]+'.ports[1]);\n'
            connections += 'connect('+constL[0]+'.y, '+HPL[0]+'.TSet);\n'

            return [W+L, connections]

        return [W, connections]

    def script_geo_heat_pump(self, name, x=0,y=0, nports=1) :
        '''
        Return modelica script to build a combined source geothermal + heat pump
        In the form of a list : first element corresponds to declaration, second element corresponds to connection
        '''

        # heat pump
        HP = np.array(['HP_'+name, self.script_element('HP_'+name, 'Buildings.Fluid.HeatPumps.Carnot_TCon')])
        source_sea = np.array(['source_sea_'+name, self.script_element('source_sea_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
        sink_sea = np.array(['sink_sea_'+name, self.script_element('sink_sea_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])
        const = np.array(['constant_'+name, self.script_element('constant_'+name, 'Modelica.Blocks.Sources.Constant')])
        
        # geothermal
        hex = np.array(['hex_'+name, self.script_element('hex_'+name, 'Buildings.Fluid.HeatExchangers.PlateHeatExchangerEffectivenessNTU')])
        source_geo = np.array(['source_geo_'+name, self.script_element('source_geo_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
        sink_geo = np.array(['sink_geo_'+name, self.script_element('sink_geo_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])

        # fluid circulation
        prod = np.array(['prod_'+name, self.script_element('prod_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=max(1,self.n_pipes-1))])
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        term = np.array(['temp_return_'+name, self.script_element('temp_return_'+name, 'Buildings.Fluid.Sensors.Temperature')])
        
        W = HP[1] + source_sea[1] + sink_sea[1] + const[1] + prod[1] + sink[1] + term[1] + hex[1] + source_geo[1] + sink_geo[1]

        connections = ''
        connections += 'connect('+sink[0]+'.ports[1], '+term[0]+'.port);\n'
        connections += 'connect('+prod[0]+'.T_in, '+term[0]+'.T);\n'
        connections += 'connect('+prod[0]+'.ports[1], '+hex[0]+'.port_a1);\n'
        connections += 'connect('+source_geo[0]+'.ports[1], '+hex[0]+'.port_a2);\n'
        connections += 'connect('+sink_geo[0]+'.ports[1], '+hex[0]+'.port_b2);\n'
        connections += 'connect('+hex[0]+'.port_b1, '+HP[0]+'.port_a1);\n'
        connections += 'connect('+source_sea[0]+'.ports[1], '+HP[0]+'.port_a2);\n'
        connections += 'connect('+HP[0]+'.port_b2, '+sink_sea[0]+'.ports[1]);\n'
        connections += 'connect('+const[0]+'.y, '+HP[0]+'.TSet);\n'

        if self.n_pipes == 3 :
            # heat pump
            HPL = np.array(['HPL_'+name, self.script_element('HPL_'+name, 'Buildings.Fluid.HeatPumps.Carnot_TCon')])
            source_seaL = np.array(['source_seaL_'+name, self.script_element('source_seaL_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
            sink_seaL = np.array(['sink_seaL_'+name, self.script_element('sink_seaL_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])
            constL = np.array(['constantL_'+name, self.script_element('constantL_'+name, 'Modelica.Blocks.Sources.Constant')])
            
            # geothermal
            hexL = np.array(['hexL_'+name, self.script_element('hexL_'+name, 'Buildings.Fluid.HeatExchangers.PlateHeatExchangerEffectivenessNTU')])
            source_geoL = np.array(['source_geoL_'+name, self.script_element('source_geoL_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
            sink_geoL = np.array(['sink_geoL_'+name, self.script_element('sink_geoL_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])
            L = HPL[1] + source_seaL[1] + sink_seaL[1] + constL[1] + hexL[1] + source_geoL[1] + sink_geoL[1]

            connections += 'connect('+prod[0]+'.ports[2], '+hexL[0]+'.port_a1);\n'
            connections += 'connect('+source_geoL[0]+'.ports[1], '+hexL[0]+'.port_a2);\n'
            connections += 'connect('+sink_geoL[0]+'.ports[1], '+hexL[0]+'.port_b2);\n'
            connections += 'connect('+hexL[0]+'.port_b1, '+HPL[0]+'.port_a1);\n'
            connections += 'connect('+source_seaL[0]+'.ports[1], '+HPL[0]+'.port_a2);\n'
            connections += 'connect('+HPL[0]+'.port_b2, '+sink_seaL[0]+'.ports[1]);\n'
            connections += 'connect('+constL[0]+'.y, '+HPL[0]+'.TSet);\n'

            return [W+L, connections]

        return [W, connections]

    def script_heat_pump_gas_boiler(self, name, x=0,y=0, nports=1) :
        '''
        Return modelica script to build a combined source heat pump + gas boiler
        In the form of a list : first element corresponds to declaration, second element corresponds to connection
        '''

        # heat pump
        HP = np.array(['HP_'+name, self.script_element('HP_'+name, 'Buildings.Fluid.HeatPumps.Carnot_TCon')])
        source_sea = np.array(['source_sea_'+name, self.script_element('source_sea_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
        sink_sea = np.array(['sink_sea_'+name, self.script_element('sink_sea_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])
        const = np.array(['const_'+name, self.script_element('const_'+name, 'Modelica.Blocks.Sources.Constant')])

        # gas boiler
        boil = np.array(['boiler_'+name, self.script_element('boiler_'+name, 'Buildings.Fluid.Boilers.BoilerPolynomial')])
        # controller
        cont = self.script_controller(name, input=boil[0]+'.sta_b.T')

        # fluid circulation
        prod = np.array(['prod_'+name, self.script_element('prod_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=max(1,self.n_pipes-1))])
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        term = np.array(['temp_return_'+name, self.script_element('temp_return_'+name, 'Buildings.Fluid.Sensors.Temperature')])

        W = HP[1] + source_sea[1] + sink_sea[1] + const[1] + boil[1] + cont[1] + prod[1] + sink[1] + term[1] 

        connections = ''
        connections += 'connect('+sink[0]+'.ports[1], '+term[0]+'.port);\n'
        connections += 'connect('+prod[0]+'.T_in, '+term[0]+'.T);\n'
        connections += 'connect('+prod[0]+'.ports[1], '+HP[0]+'.port_a1);\n'
        connections += 'connect('+source_sea[0]+'.ports[1], '+HP[0]+'.port_a2);\n'
        connections += 'connect('+HP[0]+'.port_b2, '+sink_sea[0]+'.ports[1]);\n'
        connections += 'connect('+const[0]+'.y, '+HP[0]+'.TSet);\n'
        connections += 'connect('+HP[0]+'.port_b1, '+boil[0]+'.port_a);\n'
        connections += cont[2]
        connections += 'connect('+cont[0]+'.y, '+boil[0]+'.y);\n'

        if self.n_pipes == 3 :

            # heat pump
            HPL = np.array(['HPL_'+name, self.script_element('HPL_'+name, 'Buildings.Fluid.HeatPumps.Carnot_TCon')])
            source_seaL = np.array(['source_seaL_'+name, self.script_element('source_seaL_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
            sink_seaL = np.array(['sink_seaL_'+name, self.script_element('sink_seaL_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])
            constL = np.array(['constL_'+name, self.script_element('constL_'+name, 'Modelica.Blocks.Sources.Constant')])

            # gas boiler
            boilL = np.array(['boilerL_'+name, self.script_element('boilerL_'+name, 'Buildings.Fluid.Boilers.BoilerPolynomial')])
            # controller
            contL = self.script_controller('L'+name, input=boil[0]+'.sta_b.T')

            L = HPL[1] + source_seaL[1] + sink_seaL[1] + constL[1] + boilL[1] + contL[1]  

            connections += 'connect('+prod[0]+'.ports[2], '+HPL[0]+'.port_a1);\n'
            connections += 'connect('+source_seaL[0]+'.ports[1], '+HPL[0]+'.port_a2);\n'
            connections += 'connect('+HPL[0]+'.port_b2, '+sink_seaL[0]+'.ports[1]);\n'
            connections += 'connect('+constL[0]+'.y, '+HPL[0]+'.TSet);\n'
            connections += 'connect('+HPL[0]+'.port_b1, '+boilL[0]+'.port_a);\n'
            connections += contL[2]
            connections += 'connect('+contL[0]+'.y, '+boilL[0]+'.y);\n'

            return [W+L, connections]

        return [W, connections]

    def script_sea(self, name, x=0,y=0, nports=1) :
        """
        Return modelica script to build a water source 
        Only for ring model
        In the form of a list : first element corresponds to declaration, second element corresponds to connection
        """
        # fluid circulation
        prod = np.array(['prod_'+name, self.script_element('prod_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=max(1,self.n_pipes-1))])
        sink = np.array(['sink_'+name, self.script_element('sink_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=nports)])
        term = np.array(['temp_return_'+name, self.script_element('temp_return_'+name, 'Buildings.Fluid.Sensors.Temperature')])
       
        # sea exchanger
        hex = np.array(['hex_'+name, self.script_element('hex_'+name, 'Buildings.Fluid.HeatExchangers.PlateHeatExchangerEffectivenessNTU')])
        source_sea = np.array(['source_sea_'+name, self.script_element('source_sea_'+name, 'Buildings.Fluid.Sources.MassFlowSource_T', nports=1)])
        sink_sea = np.array(['sink_sea_'+name, self.script_element('sink_sea_'+name, 'Buildings.Fluid.Sources.Boundary_pT', nports=1)])

        connections = ''
        connections += 'connect('+sink[0]+'.ports[1], '+term[0]+'.port);\n'
        connections += 'connect('+prod[0]+'.T_in, '+term[0]+'.T);\n'
        connections += 'connect('+prod[0]+'.ports[1], '+hex[0]+'.port_a1);\n'
        connections += 'connect('+source_sea[0]+'.ports[1], '+hex[0]+'.port_a2);\n'
        connections += 'connect('+sink_sea[0]+'.ports[1], '+hex[0]+'.port_b2);\n'

        return [prod[1] + sink[1] + term[1] + hex[1] + source_sea[1] + sink_sea[1], connections]


    def script_controller(self, name, input, x=0,y=0, T=0) :
        '''
        input : return variable for the controller
        Return modelica script to build a substation
        In the form of a list :
        0 : name of the component
        1 : declarations
        2 : connections
        '''

        def_T = 'k=273.15+'+str(T)+', \n'

        # two elements list [name, script]
        PID = np.array(['PID_'+name, self.script_element('PID_'+name, 'Modelica.Blocks.Continuous.LimPID', x-30,y+10)])
        inp = np.array(['input_'+name, self.script_element('input_'+name, 'Modelica.Blocks.Sources.RealExpression', x-40,y, input=input)])
        const = np.array(['constant_'+name, self.script_element('constant_'+name, 'Modelica.Blocks.Sources.Constant', x-50,y+10, param=def_T)])

        # connections
        connections = ''
        connections += 'connect('+inp[0]+'.y, '+PID[0]+'.u_m);\n'
        connections += 'connect('+const[0]+'.y, '+PID[0]+'.u_s);\n'

        return np.array([PID[0], PID[1] + inp[1] + const[1], connections])


    # Create commands --------------------------------------
    # they initialize the names of the ports of each element
    # they set the boolean is_built to True

    def create_simple_source(self, node) :
        # for sources, ports are reversed because when connected to SST
        # the connections are b-a and a-b
        self.graph.nodes[node]['port_b'] = 'temp_return_supply_'+str(node)+'.port'
        self.graph.nodes[node]['port_a'] = 'prod_supply_'+str(node)+'.ports'
        self.graph.nodes[node]['i_port_a'] = 1
        self.graph.nodes[node]['port_aL'] = 'prodL_supply_'+str(node)+'.ports'
        self.graph.nodes[node]['i_port_aL'] = 1
        self.graph.nodes[node]['is_built'] = True

    def create_gas_boiler(self, node) :
        self.graph.nodes[node]['port_b'] = 'temp_return_supply_'+str(node)+'.port'
        self.graph.nodes[node]['port_aL'] = 'boilerL_supply_'+str(node)+'.port_b'
        self.graph.nodes[node]['port_a'] = 'boiler_supply_'+str(node)+'.port_b' 
        self.graph.nodes[node]['is_built'] = True

    def create_heat_pump(self, node) :
        self.graph.nodes[node]['port_b'] = 'temp_return_supply_'+str(node)+'.port'
        self.graph.nodes[node]['port_a'] = 'HP_supply_'+str(node)+'.port_b1'
        self.graph.nodes[node]['port_aL'] = 'HPL_supply_'+str(node)+'.port_b1' 
        self.graph.nodes[node]['is_built'] = True       

    def create_sea(self, node) :
        self.graph.nodes[node]['port_b'] = 'temp_return_supply_'+str(node)+'.port'
        self.graph.nodes[node]['port_a'] = 'hex_supply_'+str(node)+'.port_b1'
        self.graph.nodes[node]['is_built'] = True 

    def create_building(self, node, both=False, L='', heat_pump=False) :
        if heat_pump : # in the ring model
            if both : # if the SST requires both heating and DHW
                self.graph.nodes[node]['port_a'] = 'HP_W_SST_'+str(node)+'.port_a1'
                self.graph.nodes[node]['port_b'] = 'HP_H_SST_'+str(node)+'.port_b1'
            else :
                self.graph.nodes[node]['port_a'] = 'HP_SST_'+str(node)+'.port_a1'
                self.graph.nodes[node]['port_b'] = 'HP_SST_'+str(node)+'.port_b1'
        else : # if n_pips=2 or 3
            if both : # if the SST requires both heating and DHW
                self.graph.nodes[node]['port_a'] = 'valve_W_SST_'+str(node)+'.port_a'
                self.graph.nodes[node]['port_aL'] = 'valve_H_SST_'+str(node)+'.port_a'
                self.graph.nodes[node]['port_b'] = 'hex_H_SST_'+str(node)+'.port_b1'
            else :
                # valve.port_a is either port_a or port_aL according to demand_T from SST
                self.graph.nodes[node]['port_a'+L] = 'valve_SST_'+str(node)+'.port_a'
                self.graph.nodes[node]['port_b'] = 'hex_SST_'+str(node)+'.port_b1'
        self.graph.nodes[node]['is_built'] = True


    def port(self, node, dir, L='') :
        '''
        if node is a multiple connection port, increments n_ports and returns the correct port
        if port does not already exist (3 pipes case), returns False
        '''
        iport = self.graph.nodes[node]['i_port_'+dir+L]
        if not iport :
            if self.graph.nodes[node]['port_'+dir+L] :
                return self.graph.nodes[node]['port_'+dir+L]
            else : 
                return False
        else : 
            self.graph.nodes[node]['i_port_'+dir+L] += 1
            if self.graph.nodes[node]['port_'+dir+L] :
                return self.graph.nodes[node]['port_'+dir+L] + '[' + str(iport) + ']'
            else : 
                return False
            

    def write_model(self) :
        '''
        Returns modelica script to build the whole model
        According to the graph
        Note : initially, I wanted to create connections and elements at the same time, 
        that is why I iterate on vertices and their adjacency 
        Now that I don't do that (I connect all elements after they have been created)
        we could just iterate over all vertices without any particular order
        and avoid reading multiple times the same vertex
        '''

        begin = 'model ' + self.model_name + '\n \n \n'
        end = '\n \n end ' + self.model_name + ';'

        declaration = ''
        equation = '\n equation \n \n'


        supply_h = '\n // Supply_heating \n \n'
        buildings = '\n // Buildings \n \n'
        pipes = '\n // Pipes \n \n' 

        for node, neighbors in self.graph.adjacency() :
            x1,y1 = self.graph.nodes[node]['pos']
            nports_node = 0
            nports_neighbor = 0
            # node construction if not already built
            # we assume that all nodes are either substations or sources
            if not self.graph.nodes[node]['is_built'] :
                equation += '\n //' + node + '\n \n'
                if self.graph.nodes[node]['is_supply_heating'] : # the node is a heat source
                    nports_node = len(list(self.graph.neighbors(node))) # number of connections from the source
                    if self.source_type == 'simple_source' :
                        supply_h += self.script_simple_source('supply_'+str(node), x1,y1, nports_node)[0] 
                        equation += self.script_simple_source('supply_'+str(node), x1,y1)[1] 
                        self.create_simple_source(node)
                    elif self.source_type == 'gas_boiler' :
                        supply_h += self.script_gas_boiler('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_gas_boiler('supply_'+str(node), x1,y1)[1] 
                        self.create_gas_boiler(node)  
                    elif self.source_type == 'gas_boiler_geo' :
                        supply_h += self.script_gas_boiler_geo('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_gas_boiler_geo('supply_'+str(node), x1,y1)[1] 
                        self.create_gas_boiler(node)
                    elif self.source_type == 'heat_pump' :
                        supply_h += self.script_heat_pump('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_heat_pump('supply_'+str(node), x1,y1)[1] 
                        self.create_heat_pump(node)  
                    elif self.source_type == 'geo_heat_pump' :
                        supply_h += self.script_geo_heat_pump('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_geo_heat_pump('supply_'+str(node), x1,y1)[1] 
                        self.create_heat_pump(node)   
                    elif self.source_type == 'heat_pump_gas_boiler' :
                        supply_h += self.script_heat_pump_gas_boiler('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_heat_pump_gas_boiler('supply_'+str(node), x1,y1)[1] 
                        self.create_gas_boiler(node) 
                    elif self.source_type == 'sea' :
                        supply_h += self.script_sea('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_sea('supply_'+str(node), x1,y1)[1] 
                        self.create_sea(node)        
                else : # the node is a substation
                    T_heating = self.graph.nodes[node]['T_heating']
                    T_DHW = self.graph.nodes[node]['T_DHW']
                    if T_heating and T_DHW :
                    # in that case, two ports are created, the SST works with 2 or 3 pipes
                        buildings += self.script_substation('H_SST_'+str(node), x1,y1, T=T_heating)[0]
                        equation += self.script_substation('H_SST_'+str(node), x1,y1, T=T_heating)[1]
                        buildings += self.script_substation('W_SST_'+str(node), x1,y1, T=T_DHW)[0]
                        equation += self.script_substation('W_SST_'+str(node), x1,y1, T=T_DHW)[1]
                        equation += 'connect (hex_H_SST_'+str(node)+'.port_b1, hex_W_SST_'+str(node)+'.port_b1); \n'
                        if self.n_pipes == 2 :
                            equation += 'connect (valve_H_SST_'+str(node)+'.port_a, valve_W_SST_'+str(node)+'.port_a); \n'                 
                        self.create_building(node, both=True)
                    elif self.n_pipes == 3 : 
                    # we must label the station heating or DHW to attribute the correct ports
                        T = max(T_heating, T_DHW)
                        buildings += self.script_substation('SST_'+str(node), x1,y1, T)[0]
                        equation += self.script_substation('SST_'+str(node), x1,y1, T)[1]
                        if T == T_heating :
                            self.create_building(node, L='L')
                        elif T == T_DHW :
                            self.create_building(node)
                    else :
                    # there is only one demand temperature and one active port
                        buildings += self.script_substation('SST_'+str(node), x1,y1, T=max(T_heating, T_DHW))[0]
                        equation += self.script_substation('SST_'+str(node), x1,y1, T=max(T_heating, T_DHW))[1]
                        self.create_building(node)

            for neighbor,at in neighbors.items() :
                x2,y2 = self.graph.nodes[neighbor]['pos']

                # neighbor creation if not already built
                if not self.graph.nodes[neighbor]['is_built'] :
                    equation += '\n //' + neighbor + '\n \n'
                    if self.graph.nodes[neighbor]['is_supply_heating'] :
                        nports_neighbor = len(list(self.graph.neighbors(neighbor)))
                        if self.source_type == 'simple_source' :
                            buildings += self.script_simple_source('supply_'+str(neighbor), x2,y2, nports_neighbor)[0]
                            equation += self.script_simple_source('supply_'+str(neighbor), x2,y2)[1]
                            self.create_simple_source(neighbor)
                        elif self.source_type == 'gas_boiler' :
                            buildings += self.script_gas_boiler('supply_'+str(neighbor), x2,y2)[0]
                            equation += self.script_gas_boiler('supply_'+str(neighbor), x2,y2)[1]
                            self.create_gas_boiler(neighbor)
                        elif self.source_type == 'gas_boiler_geo' :
                            supply_h += self.script_gas_boiler_geo('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_gas_boiler_geo('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_gas_boiler(neighbor) 
                        elif self.source_type == 'heat_pump' :
                            supply_h += self.script_heat_pump('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_heat_pump('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_heat_pump(neighbor) 
                        elif self.source_type == 'geo_heat_pump' :
                            supply_h += self.script_geo_heat_pump('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_geo_heat_pump('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_heat_pump(neighbor)
                        elif self.source_type == 'heat_pump_gas_boiler' :
                            supply_h += self.script_heat_pump_gas_boiler('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_heat_pump_gas_boiler('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_gas_boiler(neighbor)  
                        elif self.source_type == 'sea' :
                            supply_h += self.script_sea('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_sea('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_sea(neighbor)     
                    else :
                        T_heating = self.graph.nodes[neighbor]['T_heating']
                        T_DHW = self.graph.nodes[neighbor]['T_DHW']
                        if T_heating and T_DHW :
                        # in that case, two ports are created, and the SST works with 2 or 3 pipes
                            buildings += self.script_substation('H_SST_'+str(neighbor), x1,y1, T=T_heating)[0]
                            equation += self.script_substation('H_SST_'+str(neighbor), x1,y1, T=T_heating)[1]
                            buildings += self.script_substation('W_SST_'+str(neighbor), x1,y1, T=T_DHW)[0]
                            equation += self.script_substation('W_SST_'+str(neighbor), x1,y1, T=T_DHW)[1]
                            equation += 'connect (hex_H_SST_'+str(neighbor)+'.port_b1, hex_W_SST_'+str(neighbor)+'.port_b1); \n'
                            if self.n_pipes == 2 :
                                equation += 'connect (valve_H_SST_'+str(neighbor)+'.port_a, valve_W_SST_'+str(neighbor)+'.port_a); \n'
                            self.create_building(neighbor, both=True)
                        elif self.n_pipes == 3 :
                        # we must label the station heating or DHW to attribute the correct ports
                            T = max(T_heating, T_DHW)
                            buildings += self.script_substation('SST_'+str(neighbor), x1,y1, T)[0]
                            equation += self.script_substation('SST_'+str(neighbor), x1,y1, T)[1]
                            if T == T_heating :
                                self.create_building(neighbor, L='L')
                            elif T == T_DHW :
                                self.create_building(neighbor)
                        else :
                        # there is only one demand temperature and one active port
                            buildings += self.script_substation('SST_'+str(neighbor), x1,y1, T=max(T_heating, T_DHW))[0]
                            equation += self.script_substation('SST_'+str(neighbor), x1,y1, T=max(T_heating, T_DHW))[1]
                            self.create_building(neighbor)

                # creation of pipes and connections if not already built
                if not at['is_built'] :
                    equation += '\n // ' + node + ', ' + neighbor + '\n \n'
                    X,Y = (x1+x2)/2, (y1+y2)/2

                    # pipe length
                    p = np.array([x1,y1])
                    q = np.array([x2,y2])
                    length = int(np.sqrt(np.sum((p-q)**2)))

                    if self.n_pipes == 1 : # in the case of the ring model
                        
                        pipe_name = 'pipe_' + str(node) + str(neighbor)
                        pipes += self.script_element(pipe_name, 'Buildings.Fluid.FixedResistances.Pipe', X,Y, nports=0, length=length)

                        # we must connect port b to a
                        node_port = self.port(node, 'b')
                        neigh_port = self.port(neighbor, 'a')
                        equation += 'connect (' + node_port + ', ' + pipe_name + '.port_a) \n    '
                        equation += 'annotation (Line(points={{' + str((x1+X)//2) + ', ' + str((y1+Y)//2) + '}})) ;\n'
                        equation += 'connect (' + pipe_name + '.port_b, ' + neigh_port + ') \n    '
                        equation += 'annotation (Line(points={{' + str((x1+X)//2) + ', ' + str((y1+Y)//2) + '}})) ;\n'

                    else : # if n_ppes=2 or 3
                        for i in range (self.n_pipes) :
                            dir = self.dir_list[i]
                            pipe_name = 'pipe_' + str(node) + str(neighbor) + '_' + dir
                            pipes += self.script_element(pipe_name, 'Buildings.Fluid.FixedResistances.Pipe', X,Y, nports=0, length=length)
    
                            # we must connect port a to a, and b to b
                            node_port = self.port(node, dir)
                            neigh_port = self.port(neighbor, dir)
                            if node_port :
                                equation += 'connect (' + node_port + ', ' + pipe_name + '.port_a) \n    '
                                equation += 'annotation (Line(points={{' + str((x1+X)//2) + ', ' + str((y1+Y)//2) + '}})) ;\n'
                            self.graph.nodes[node]['port_'+dir] = pipe_name + '.port_a'
                            self.graph.nodes[node]['i_port_'+dir] = False
                            if neigh_port :
                                equation += 'connect (' + pipe_name + '.port_b' + ', ' + neigh_port + ') \n    '
                                equation += 'annotation (Line(points={{' + str((x2+X)//2) + ', ' + str((y2+Y)//2) + '}})) ;\n'
                            self.graph.nodes[neighbor]['port_'+dir] = pipe_name + '.port_b'
                            self.graph.nodes[neighbor]['i_port_'+dir] = False

                        at['is_built'] = True

        declaration += supply_h
        declaration += buildings
        declaration += pipes
        
        txt = begin + declaration + equation + end
        return txt


    def write_model_ring (self) :
        '''
        Returns modelica script for the whole ring model (n_pipes=1)
        '''

        begin = 'model ' + self.model_name + '\n \n \n'
        end = '\n \n end ' + self.model_name + ';'

        declaration = ''
        equation = '\n equation \n \n'


        supply_h = '\n // Supply_heating \n \n'
        buildings = '\n // Buildings \n \n'
        pipes = '\n // Pipes \n \n' 

        for node, neighbors in self.graph.adjacency() :
            x1,y1 = self.graph.nodes[node]['pos']
            nports_node = 0
            nports_neighbor = 0
            # node construction if not already built
            if not self.graph.nodes[node]['is_built'] :
                equation += '\n //' + node + '\n \n'
                if self.graph.nodes[node]['is_supply_heating'] : # the node is a heat source
                    nports_node = len(list(self.graph.neighbors(node))) 
                    if self.source_type == 'simple_source' :
                        supply_h += self.script_simple_source('supply_'+str(node), x1,y1, nports_node)[0] 
                        equation += self.script_simple_source('supply_'+str(node), x1,y1)[1] 
                        self.create_simple_source(node)
                    elif self.source_type == 'gas_boiler' :
                        supply_h += self.script_gas_boiler('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_gas_boiler('supply_'+str(node), x1,y1)[1] 
                        self.create_gas_boiler(node)  
                    elif self.source_type == 'gas_boiler_geo' :
                        supply_h += self.script_gas_boiler_geo('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_gas_boiler_geo('supply_'+str(node), x1,y1)[1] 
                        self.create_gas_boiler(node)
                    elif self.source_type == 'heat_pump' :
                        supply_h += self.script_heat_pump('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_heat_pump('supply_'+str(node), x1,y1)[1] 
                        self.create_heat_pump(node)  
                    elif self.source_type == 'geo_heat_pump' :
                        supply_h += self.script_geo_heat_pump('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_geo_heat_pump('supply_'+str(node), x1,y1)[1] 
                        self.create_heat_pump(node)   
                    elif self.source_type == 'heat_pump_gas_boiler' :
                        supply_h += self.script_heat_pump_gas_boiler('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_heat_pump_gas_boiler('supply_'+str(node), x1,y1)[1] 
                        self.create_gas_boiler(node)      
                    elif self.source_type == 'sea' :
                        supply_h += self.script_sea('supply_'+str(node), x1,y1)[0] 
                        equation += self.script_sea('supply_'+str(node), x1,y1)[1] 
                        self.create_sea(node)     
                else : # the node is a substation
                    T_heating = self.graph.nodes[node]['T_heating']
                    T_DHW = self.graph.nodes[node]['T_DHW']
                    if T_heating and T_DHW :
                    # in that case, two ports are created, the SST works with 2 or 3 pipes
                        buildings += self.script_substation('H_SST_'+str(node), x1,y1, T=T_heating, heat_pump=True)[0]
                        equation += self.script_substation('H_SST_'+str(node), x1,y1, T=T_heating, heat_pump=True)[1]
                        buildings += self.script_substation('W_SST_'+str(node), x1,y1, T=T_DHW, heat_pump=True)[0]
                        equation += self.script_substation('W_SST_'+str(node), x1,y1, T=T_DHW, heat_pump=True)[1]
                        equation += 'connect (HP_W_SST_'+str(node)+'.port_b1, HP_H_SST_'+str(node)+'.port_a1); \n'                 
                        self.create_building(node, both=True, heat_pump=True)
                    else :
                    # there is only one demand temperature and one active port
                        buildings += self.script_substation('SST_'+str(node), x1,y1, T=max(T_heating, T_DHW), heat_pump=True)[0]
                        equation += self.script_substation('SST_'+str(node), x1,y1, T=max(T_heating, T_DHW), heat_pump=True)[1]
                        self.create_building(node, heat_pump=True)

            for neighbor,at in neighbors.items() :
                x2,y2 = self.graph.nodes[neighbor]['pos']

                # neighbor creation if not already built
                if not self.graph.nodes[neighbor]['is_built'] :
                    equation += '\n //' + neighbor + '\n \n'
                    if self.graph.nodes[neighbor]['is_supply_heating'] :
                        nports_neighbor = len(list(self.graph.neighbors(neighbor)))
                        if self.source_type == 'simple_source' :
                            buildings += self.script_simple_source('supply_'+str(neighbor), x2,y2, nports_neighbor)[0]
                            equation += self.script_simple_source('supply_'+str(neighbor), x2,y2)[1]
                            self.create_simple_source(neighbor)
                        elif self.source_type == 'gas_boiler' :
                            buildings += self.script_gas_boiler('supply_'+str(neighbor), x2,y2)[0]
                            equation += self.script_gas_boiler('supply_'+str(neighbor), x2,y2)[1]
                            self.create_gas_boiler(neighbor)
                        elif self.source_type == 'gas_boiler_geo' :
                            supply_h += self.script_gas_boiler_geo('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_gas_boiler_geo('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_gas_boiler(neighbor) 
                        elif self.source_type == 'heat_pump' :
                            supply_h += self.script_heat_pump('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_heat_pump('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_heat_pump(neighbor) 
                        elif self.source_type == 'geo_heat_pump' :
                            supply_h += self.script_geo_heat_pump('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_geo_heat_pump('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_heat_pump(neighbor)
                        elif self.source_type == 'heat_pump_gas_boiler' :
                            supply_h += self.script_heat_pump_gas_boiler('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_heat_pump_gas_boiler('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_gas_boiler(neighbor)  
                        elif self.source_type == 'sea' :
                            supply_h += self.script_sea('supply_'+str(neighbor), x1,y1)[0] 
                            equation += self.script_sea('supply_'+str(neighbor), x1,y1)[1] 
                            self.create_sea(neighbor)  
                    else :
                        T_heating = self.graph.nodes[neighbor]['T_heating']
                        T_DHW = self.graph.nodes[neighbor]['T_DHW']
                        if T_heating and T_DHW :
                        # in that case, two ports are created, and the SST works with 2 or 3 pipes
                            buildings += self.script_substation('H_SST_'+str(neighbor), x1,y1, T=T_heating, heat_pump=True)[0]
                            equation += self.script_substation('H_SST_'+str(neighbor), x1,y1, T=T_heating, heat_pump=True)[1]
                            buildings += self.script_substation('W_SST_'+str(neighbor), x1,y1, T=T_DHW, heat_pump=True)[0]
                            equation += self.script_substation('W_SST_'+str(neighbor), x1,y1, T=T_DHW, heat_pump=True)[1]
                            equation += 'connect (HP_W_SST_'+str(neighbor)+'.port_b1, HP_H_SST_'+str(neighbor)+'.port_a1); \n'  
                            self.create_building(neighbor, both=True, heat_pump=True)
                        else :
                        # there is only one demand temperature and one active port
                            buildings += self.script_substation('SST_'+str(neighbor), x1,y1, T=max(T_heating, T_DHW), heat_pump=True)[0]
                            equation += self.script_substation('SST_'+str(neighbor), x1,y1, T=max(T_heating, T_DHW), heat_pump=True)[1]
                            self.create_building(neighbor, heat_pump=True)   

        # creation of pipes and connections if not already built
        for i in range (len(self.graph.nodes)) :
            node = list(self.graph.nodes)[i]
            neighbor = (list(self.graph.nodes)+[list(self.graph.nodes)[0]])[i+1]
            equation += '\n // ' + node + ', ' + neighbor + '\n \n'
            
            X,Y = (x1+x2)/2, (y1+y2)/2
            # pipe length
            p = np.array([x1,y1])
            q = np.array([x2,y2])
            length = int(np.sqrt(np.sum((p-q)**2)))
                        
            pipe_name = 'pipe_' + str(node) + str(neighbor)
            pipes += self.script_element(pipe_name, 'Buildings.Fluid.FixedResistances.Pipe', X,Y, nports=0, length=length)

            # we must connect port b to a
            node_port = self.port(node, 'b')
            if self.graph.nodes[node]['is_supply_heating'] :
                node_port = self.port(node, 'a')
            neigh_port = self.port(neighbor, 'a')
            if self.graph.nodes[neighbor]['is_supply_heating'] :
                neigh_port = self.port(neighbor, 'b')
            equation += 'connect (' + node_port + ', ' + pipe_name + '.port_a); \n    '
            equation += 'annotation (Line(points={{' + str((x1+X)//2) + ', ' + str((y1+Y)//2) + '}})) ;\n'
            equation += 'connect (' + pipe_name + '.port_b, ' + neigh_port + '); \n    '
            equation += 'annotation (Line(points={{' + str((x1+X)//2) + ', ' + str((y1+Y)//2) + '}})) ;\n'
        

        declaration += supply_h
        declaration += buildings
        declaration += pipes
        
        txt = begin + declaration + equation + end
        return txt




    def set_source(self, source_name) :
        self.source_type = source_name
    
    def set_n_pipes(self, n_pipes) :
        self.n_pipes = n_pipes

    def pipe_length(self) :
        L = 0
        for edge in self.graph.edges :
            x1,y1 = self.graph.nodes[edge[0]]['pos']
            x2,y2 = self.graph.nodes[edge[1]]['pos']
            p = np.array([x1,y1])
            q = np.array([x2,y2])
            length = int(np.sqrt(np.sum((p-q)**2)))
            L += length * self.n_pipes
        return L





    def write_in_file(self, file_name) :
        '''
        Includes script from write_model in file 'file_name'
        which is a modelica package that must already exist
        if model named model_name already exists, replaces it with txt
        '''

        package_name = file_name[:-3]
        file1 = open(file_name, 'r')
        file2 = open(self.model_name+'.mo', 'w')
        if self.n_pipes == 1 :
            txt = self.write_model_ring()
        else :
            txt = self.write_model()
        go_on = True
        write = True

        while go_on :
            line = file1.readline()
            if line.startswith('model '+self.model_name) :
                write = False
            elif line.startswith('end ' + package_name + ';') :
                go_on = False
                file2.write(txt+'\n')
                file2.write('end ' + package_name + ';')

            if write and go_on: 
                file2.write(line)

            if line.startswith('end '+self.model_name+';') :
                write = True

        file1.close()
        file2.close()
        os.remove(file_name)
        os.rename(self.model_name+'.mo', file_name)

        return True



    

        
                 
            
                


            
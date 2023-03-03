arg = {

    'Buildings.Fluid.Sources.Boundary_pT' :
        'redeclare package Medium = Buildings.Media.Water, \n'
        + 'T = 273.15+40,\n'
        + 'p = 2e5,\n'
    ,

    'Buildings.Fluid.Sources.MassFlowSource_T' :
        'redeclare package Medium = Buildings.Media.Water, \n'
        + 'T = 273.15+40\n'
        + 'm_flow = 1,\n'
    ,

    'Buildings.Fluid.HeatExchangers.PlateHeatExchangerEffectivenessNTU' : 
        'redeclare package Medium1 = Buildings.Media.Water, \n'
        + 'redeclare package Medium2 = Buildings.Media.Water, \n'
        + 'configuration=Buildings.Fluid.Types.HeatExchangerConfiguration.CounterFlow,\n'
        + 'm1_flow_nominal=1,\n'
        + 'm2_flow_nominal=1,\n'
        + 'dp1_nominal=1,\n'
        + 'dp2_nominal=1,\n'
        + 'use_Q_flow_nominal=false,\n'
        + 'eps_nominal=0.9,\n'
        + 'show_T=true,\n'
    ,
    
    'Buildings.Fluid.FixedResistances.Pipe' :
        'redeclare package Medium = Buildings.Media.Water, \n'
        + 'm_flow_nominal=1,\n'
        + 'thicknessIns=0.05,\n'
        + 'lambdaIns=0.03,\n'
        + 'diameter=0.1,\n'
    ,

    'Modelica.Blocks.Continuous.LimPID' :
        'k=0.0001,\n'
        + 'yMax=1,\n'
        + 'yMin=0.001\n'
    ,

    'Modelica.Blocks.Sources.Constant' :
        ''
    ,

    'Modelica.Blocks.Sources.RealExpression' :
        ''
    ,

    'Buildings.Fluid.Actuators.Valves.TwoWayLinear' :
        'redeclare package Medium = Buildings.Media.Water, \n'
        + 'CvData=Buildings.Fluid.Types.CvTypes.Kv,\n'
        + 'm_flow_nominal=1,\n'
        + 'Kv=10,\n'
    ,

    'Buildings.Fluid.Boilers.BoilerPolynomial' :
        'redeclare package Medium = Buildings.Media.Water, \n'
        + 'm_flow_nominal=10, \n'
        + 'dp_nominal=0, \n'
        + 'Q_flow_nominal=1e6, \n'
        + 'effCur=Buildings.Fluid.Types.EfficiencyCurves.Constant, \n'
        + 'fue=Buildings.Fluid.Data.Fuels.NaturalGasHigherHeatingValue() \n'
    ,

    'Buildings.Fluid.Sensors.Temperature' :
        'redeclare package Medium = Buildings.Media.Water, \n'
    ,

    'Buildings.Fluid.HeatPumps.Carnot_TCon' :
        'redeclare package Medium1 = Buildings.Media.Water,\n'
        + 'redeclare package Medium2 = Buildings.Media.Water,\n'
        + 'show_T=true,\n'
        + 'QCon_flow_nominal=1e6,\n'
        + 'use_eta_Carnot_nominal=false,\n'
        + 'COP_nominal=4,\n'
        + 'dp1_nominal=0,\n'
        + 'dp2_nominal=0\n'
    ,
        }


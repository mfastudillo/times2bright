import brightway2 as bw
import numpy as np
import pandas as pd
import re

def find_tflow(act,flow_name,literal=False,toprint=True):
    '''it returns the reference of the technosphere flows that  
    match the flow_name, it could be more than one if
    the process consumes two types of flows with similar names

    parameters:
    ----------
    act: brighway2 activity
    flow_name: string
        should identify the flow name
    literal: bool
        if true it will try to match the exact name of the flow_name
        otherwise, it will include all flows that contain the flow_name
        string in their name.
    toprint: bool
        either to print or not the flow name.

    returns:
    list of technosphere exchanges with that flow name.
    '''

    assert isinstance(flow_name,str), 'flow_name should be a string'

    if literal == False:
        tflow_query = [ex for ex in act.technosphere() if (flow_name in ex['name'])]
    if literal == True:
        tflow_query = [ex for ex in act.technosphere() if (flow_name == ex['name'])]

    if (len(tflow_query)!=1):
        print('careful',len(tflow_query),'flows with the name:')
        if toprint is True:
            [print(f['name']) for f in tflow_query]

    return(tflow_query)


def find_eflow(act, flow_name, literal=False, toprint=True):
    '''it returns a list of biosphere flows, that
    match a given name.

    parameters:
    ----------
    act: brighway2 activity
    flow_name: string
        should identify the flow name
    literal: bool
        if true it will try to match the exact name of the flow_name
        otherwise, it will include all flows that contain the flow_name
        string in their name.
    toprint: bool
        either to print or not the flow name.
    returns:
    list of biosphere exchanges with that flow name.
    '''
    assert isinstance(flow_name, str), 'flow_name should be a string'

    if literal == False:
        bflow_query = [ex for ex in act.biosphere() if (flow_name in ex['name'])]
    if literal == True:
        bflow_query = [ex for ex in act.biosphere() if (flow_name == ex['name'])]
    
    if toprint == True: print(len(bflow_query),'flows with the name:')
    
    #do flows from different markets have the same name?
    if toprint == True: [print(f['name']) for f in bflow_query]
    
    return(bflow_query)


def determine_eff(act, flow, literal=False):
    '''provides the efficiency given the fuel flow name,
    if more than one tflow exist, then the sum is used (e.g. using inputs
    from different markets) prints the units of the efficiency

    parameters:
    ----------
    act: brighway2 activity
    flow: string
        should identify the fuel flow
    literal: bool
        if true it will try to match the exact name of the flow
        otherwise, it will include all flows that contain the flow
        string in their name.
    
    returns:
        amount of output per amount of fuel. Whatever the units
        are

    '''
    fuel_query = find_tflow(act, flow, literal=literal)

        
    if len(fuel_query) > 1:
        print('ups, more than one entry of that fuel')
        print('warning: total amount assuming they are the same type of input')
        # assuming they have the same unit
        print('fuel unit:',fuel_query[0]['unit'])
        print('output unit:',act['unit'])
        f_amount=0
        for f in fuel_query:
            f_amount = f_amount+f['amount']
        return(act['production amount']/f_amount)

    elif len(fuel_query)==1:
        print('fuel unit:',fuel_query[0]['unit'])
        print('output unit:',act['unit'])
               
        fuel_in_flow = fuel_query[0]
        f_amount = fuel_in_flow['amount']
        return(act['production amount']/f_amount)

    elif len(fuel_query) == 0:
        print('careful, no fuel found')
        return(np.nan)


def determine_ef(act, tflow, bflow, literal=False):
    '''provides the emission factor given the fuel flow, and
    a biosphere (emission) flow. Prints the units of the
    emission factor

    parameters:
    ----------
    act: brighway2 activity
    tflow: string
        should identify the fuel flow
    bflow: string
        should identify the emission to biosphere
    literal: bool
        if true it will try to match the exact name of the flow
        otherwise, it will include all flows that contain the flow
        string in their name.

    returns:
        amount of emission per amount of fuel. Whatever the units
        are
    '''

    fuel_query = find_tflow(act, tflow, literal=literal)
    emission_query = find_eflow(act, bflow, literal=literal)

    #assuming they have the same unit
    set([f['unit'] for f in fuel_query])
    print('fuel unit:',set([f['unit'] for f in fuel_query]))
    print('output unit:',set([f['unit'] for f in emission_query]))

    if (len(fuel_query)==0)&(len(emission_query)==0):
        print('WARNING, any fuel was found under that name')
        print('any biosphere flow was found')
        return(np.nan)

    elif (len(fuel_query)>0)&(len(emission_query)==0):
        print('Warning, any biosphere flow was found')
        return(0)
    
    elif (len(fuel_query)==0)&(len(emission_query)>0):
        print('WARNING, any fuel was found under that name')
        return(np.nan)
    
    elif (len(fuel_query)==0)&(len(emission_query)>1):
        print('WARNING, any fuel was found under that name')
        return(np.nan)

    elif (len(fuel_query)>1)&(len(emission_query)==0):
        print('Warning, any biosphere flow was found')
        return(0)

    elif (len(fuel_query)==1)&(len(emission_query)==1):
        #simplest case
        tf_amount= fuel_query[0]['amount']
        bf_amount= emission_query[0]['amount']
        return(bf_amount/tf_amount)

    elif (len(fuel_query)>=1)&(len(emission_query)>=1):
        print('ups, more than one entry of that fuel')
        print('warning: total amount assuming they are the same type of input')
        print('ups, more than one entry of that emission name')
        print('warning: total amount assuming they are the same type of output')
        
        tf_amount=0
        for f in fuel_query:
            tf_amount=tf_amount+f['amount']
        
        bf_amount=0
        for f in emission_query:
            bf_amount=bf_amount+f['amount']

        return(bf_amount/tf_amount)
        



def change_origin_tflow(act,flow_name,act_nflow,literal=False):
    '''changes the origin of a technosphere flow of a given activity
    it gives a warming if the reference product of the substituting
    provider has not the same name as the original provider.

    parameters:
    ----------
    act: brighway2 activity
        activity to modify
    flow_name: string 
        name that identifies the flow to be modified
    act_nflow: brigthway2 activity
        activity that provides the flow to be substituted
    literal: bool
        if true, the flow_name should exactly match the
        name of the identified flow. This is used for inuambigous
        identification (e.g. hard coal and hard coal ash)
    
    returns: brighway2 activity
        activity with the origin (provider) of the technosphere
        flow updated. 

    '''
    
    assert isinstance(flow_name,str), 'flow_name must be a string'
    
    tf=find_tflow(act,flow_name,literal=literal)
    
    if len(set([t['name'] for t in tf]))!=1:
        raise ValueError('incorrect technosphere flow identification')
               
    for t in tf:
        #test stuff
        if t['name']!=act_nflow['reference product']:
            print('warning, substituting activity does not produce same product')
            print(t['name'])
            print(act_nflow['reference product'])
        if t['unit']!=act_nflow['unit']:
            raise ValueError('activity and technosphere flows with different units')
        
        t.input=act_nflow
        t['name']=act_nflow['reference product']
        t.save()
    
    update_harmonisation(act,{'tflow_origin':True})
            
    return(act)

def update_harmonisation(act,d):
    '''update the dictionary with harmonisation parameters
    if not existing create one.'''

    try:
        act['harmonisation'].update(d)
    except:
        act['harmonisation']={}
        act['harmonisation'].update(d)

def scale_technosphere_flow(act,flow_name,scale_factor=1,literal=False):
    '''returns the bw activity with the technosphere flow scaled by
    the factor prescribed. it modifies the harmonisation dict to 
    register that the flow has been modified
    
    parameters:
    ----------
    act: brighway2 activity
        activity to modify
    flow_name: string 
        name that identifies the flow to be modified   
    scale_factor: float
        multiplier to be applied to the flow amount
    literal: bool
        if true, the flow_name should exactly match the
        name of the identified flow. This is used for inuambigous
        identification (e.g. hard coal and hard coal ash)
    '''
    
    tf=find_tflow(act,flow_name,literal=literal)
    
    if len(set([t['name'] for t in tf]))!=1:
        raise ValueError('incorrect emission identification')
        
    for t in tf:
        t['amount']=t['amount']*scale_factor
        t.save()

        #as it is we only store one tflow scaled
        update_harmonisation(act,{'tfow_scaled':True})
    return(act)

def scale_biosphere_flow(act,flow_name,scale_factor=1,literal=False):
    '''returns the bw activity with the biosphere flow scaled by
    the factor prescribed. it modifies the 'harmonisation' dict
    to register that the flow has been changed
    
    parameters:
    ----------
    act: brighway2 activity
        activity to modify
    flow_name: string 
        name that identifies the flow to be modified   
    scale_factor: float
        multiplier to be applied to the flow amount
    literal: bool
        if true, the flow_name should exactly match the
        name of the identified flow. This is used for inuambigous
        identification

    returns: brightway2 activity
        activity with the biosphere flow updated   

    '''
    
    bf=find_eflow(act,flow_name,literal=literal)
    
    if len(set([b['name'] for b in bf]))!=1:
        raise ValueError('incorrect emission identification')
        
    for b in bf:
        b['amount']=b['amount']*scale_factor
        b.save()
        
        update_harmonisation(act,{'ef_scaled':True})
        #act['harmonisation'].update({'ef_scaled':b['name']})
    return(act)


def scale_fuel_cons(act,fuel_name,scale_factor=1,literal=False):
    '''scale a fuel technosphere flow and all biosphere emissions
    to air, which are assumed to be caused by fuel consumption
    
    parameters:
    ----------
    act: brighway2 activity
    fuel_name: string
        should identify the flow name
    scale_factor: number
        factor to scale emissions and fuel consumption 
        >1 means reductions in efficiency (more fuel cons and emissions)
        <1 means improvements in efficiency (less fuel cons and emissions)
    literal: bool
        if true it will try to match the exact name of the flow_name
        otherwise, it will include all flows that contain the flow_name
        string in their name.
    
    returns:
    activity with the exchanges updated.
    '''
    tf=find_tflow(act,fuel_name,literal=literal)
    
    if len(set([t['name'] for t in tf]))!=1:
        raise ValueError('incorrect fuel identification')
    
    for f in tf:
        f['amount']=f['amount']*scale_factor
        f.save()
    for exc in act.biosphere():
        if bw.get_activity(exc['input'])['categories'][0]=='air':
            exc['amount']=exc['amount']*scale_factor
            exc.save()
    
    update_harmonisation(act,{'eff_scaled':True})

    return (act)

def isit_modified(bw_activity):
    '''returns true if the activity has entries in the 
    harmonisation dict. This dict is used to register
    changes in the activity'''

    try : 
        bw_activity['harmonisation']
        return(True)
    except: 
        return(False)

def compound_tflow(act,tflow_name,literal=False):
    '''for activities with several technosphere
    exchanges with the same name, it aggregates them
    into a single exchange with an amount equal to the
    sum of amounts. Aggregates based on the most 
    important provider.
    
    parameters:
    ----------
    act: brighway2 activity
        activity to modify
    flow_name: string 
        name that identifies the flow to be aggregated   
    literal: bool
        if true, the flow_name should exactly match the
        name of the identified flow. This is used for inuambigous
        identification

    returns: brightway2 activity
        activity with some technosphere flows aggregated.
    
    '''
    tf=find_tflow(act,tflow_name,literal=literal)
    
    #the name of the fuel is unique
    if len(set([t['name'] for t in tf]))!=1:
        raise ValueError('incorrect fuel identification')
    
    #if its just one we do not need to do anything
    if len(tf)>1:
        f_amount=0
        for f in tf:
            print(f['name'],
                  f['amount'],
                  bw.get_activity(f['input'])['name'],
                  bw.get_activity(f['input'])['location'])
            f_amount=f_amount+f['amount']
        
        #create new based on the flow with highest amount

        selected_flow=tf[0]
        for f in tf:
            if f['amount']>selected_flow['amount']:
                selected_flow=f
        
        newflow=act.new_exchange(flow=selected_flow['flow'],
                          unit=selected_flow['unit'],
                          type=selected_flow['type'],
                          name=selected_flow['name'],
                          input=selected_flow['input'],
                          comment='aggregation of fuels, uncertainty lost',
                          amount=f_amount)
        
        newflow.save()
        
        for f in tf:
            f.delete()
        
        
    return(act)

def check_query(query_result):
    '''just checking that a list contains one element. 
    Tipically used to check a query in a LCA database.
    it gives warning messages if the list has 0 or >1 lenghts

    parameters:
    ----------
    query_result: list
        typically, a list of activities from a lca database

    returns:
        unique element of the list

    '''

    assert isinstance(query_result,list)
    
    if len(query_result)>1:
        print('too many results (>1)')
        return(query_result)
    elif len(query_result)<1:
        print('0 results')
        return(query_result)
    elif len(query_result)==1:
        query_result=query_result[0]
        return(query_result)


def clean_variable_name(s):
    '''function that replaces invalid characters to convert a string in
    a suitable variable name'''
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '_', s)

    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '_', s)

    return s
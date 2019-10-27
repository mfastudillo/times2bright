
import brightway2 as bw
import numpy as np
import pandas as pd
from collections import defaultdict
import bw2analyzer as bwa


def mlca_todf(mlca):
    '''receives a multiLCA object and returns a pandas dataframe
    with some impact results and some useful activity data.
    parameters:
    ----------
    mlca: multilca object.

    returns: pandas dataframe
        impacts per activity, activity data includes, originating
        database, name, location, unit and scenario and times_pcode
        it includes all the scores per activity in the functional
        unit for all the methods defined in the MultiLCA instance.

     '''
    scores = pd.DataFrame(mlca.results, columns=mlca.methods)

    # list of tuples containng the activity and the
    # acomunt demanded
    as_activities = [
    (bw.get_activity(key), amount)
    for dct in mlca.func_units
    for key, amount in dct.items()]

    metadata_list = []
    for x, y in as_activities:

        try:
            scenario = x['harmonisation']['scenario']
            times_pcode = x['harmonisation']['times_pcode']
        except:
            scenario = ''
            times_pcode = ''

        metadata_list.append((x['database'],
                              x['name'],
                              x['location'],
                              x['unit'],
                              scenario,
                              times_pcode,
                              y))

    df_fu = pd.DataFrame(metadata_list,
                         columns=('Database',
                                  'Name',
                                  'Location',
                                  'Unit',
                                  'scenario',
                                  'times_pcode',
                                  'Amount',))

    return(pd.concat([df_fu, scores], axis=1))





def direct_impact(lca):
    '''calculates the lca score of the biosphere flows of an activity.
    excluding the impact of biosphere flows from intermediate 'technosphere'
    inputs to that activity.

    parameters:
    ----------
    lca: brightway2 lca object

    returns: float
        impact caused by the biosphere flows of the activity. It does not
        include impact of "supply chain" biosphere flows, related to
        inputs needed by the activity.

    '''
    columns_demand = [lca.activity_dict[k] for k in lca.demand.keys()]
    direct_impact = lca.characterized_inventory.sum(axis=0).A1[columns_demand].sum()
    return(direct_impact)


def find_isic(act):

    '''finds the isic code of a ecoinvent activity
    returns it as a tuple. needed because the field
    is not easy to parse otherwise

    parameters:
    -----------
    lca: brighway2 lca object

    results: tuple
        tuple containing the number and the description
        of what that number means.
    '''

    try:
        for c in act['classifications']:
            if c[0] == 'ISIC rev.4 ecoinvent':
                colon = c[1].find(':')
                return((c[1][:colon]), c[1][colon+1:])
    except:
        return(None)

# not sure if needed
# ca = bwa.ContributionAnalysis()
import pandas as pd


def preprocess_times(path):
    '''receives a excel file output of times, with scenario/attribute/
    commodity/process in the first row and year and timeslice in the
    header. it returns a clean dataframe with the same info, but using
    multiindex.

    parameters:
    ----------
    path:file path to the excel file

    returns: pandas dataframe

   '''
    io = pd.read_excel(path,
                     skiprows=6,
                     index_col=0,
                     header=[0, 1]).reset_index(drop=True)

    # print scenario (it should be one)
    assert(len(io.loc[:, io.columns.get_level_values(1) == "Scenario"].drop_duplicates())==1)
    print(io.loc[:, io.columns.get_level_values(1) == "Scenario"].drop_duplicates().iloc[0, 0])
    # delete scenario column
    io = io.loc[:, ~(io.columns.get_level_values(1) == "Scenario")]

    io = io.set_index([io.columns[0], io.columns[1], io.columns[2]])
    io.index = io.index.rename(['attribute', 'commodity', 'process'])
    io.columns = io.columns.rename(['year', 'ts'])
    return(io)


def tech_and_bio(df, pat_ghg_inclusive='CH4|CO2|N2O', pat_ghg_exclusive='CH4|CO2|N2O|GHG'):
    '''receives a dataframe generated from preprocess_times and divides it in
    technosphere (i.e. exchanges between processes) and biosphere flows
    (e.g. emissions) using regex.

    parameters:
    ----------
    df: pandas dataframe
        (describe the format)
    pat_ghg_inclusive: string
        used in regex to identify biosphere flows they should be separated by |
    pat_ghg_exclusive: string
        used in regex to identify what are not technosphere flows

    returns: list of dataframes
    dataframes with the biosphere and technosphere flows by process
    the first one contains biosphere flows and the second one technosphere flows
    '''
    return([df[df.index.get_level_values('commodity').str.contains(pat_ghg_inclusive)],
            df[~df.index.get_level_values('commodity').str.contains(pat_ghg_exclusive)]
           ])


def calculate_co2eq(emissions_df, ch4gwp=29.7, n2ogwp=264.8):
    '''calculates the total CO2eq emissions per process based on their
    CO2, CH4 and N2O emissions per time slice.

    parameters:
    ----------
    - emissions_df: pandas dataframe
        with a multindex [attribute,commodity,process] as index and a
        multindex header [year,timeslice]
    - ch4gwp: float
        global warming potential of CH4
    -n2ogwp: float
        global warming potential of N2O

    (default values based on implementation of IPCC 2013 by ecoinvent)

    returns:
    pandas series with total CO2eq per process, ordered
    '''
    dfs = emissions_df.sum(axis=1)
    dfs[dfs.index.get_level_values('commodity').str.contains('CH4')] *= ch4gwp
    dfs[dfs.index.get_level_values('commodity').str.contains('N2O')] *= n2ogwp
    dfs=dfs.groupby('process').agg('sum').sort_values(ascending=False)
    return(dfs)


def screen_processes(s_baseline, s_alternative, cutoff=0.95):
    """function to screen the processes that contribute the most to
    the absolute changes in GHGe measured as CO2eq emissions.

    parameters:
    ----------
    s_baseline: pandas Series
       Series containing the co2eq emissions per process for
       a certain simulation period. row index contains the processes.
    s_alternative: pandas Series
       same format as dfbaseline but containing the emissions associated
       with a counterfactual scenario. For "consequential" assessment.
    cutoff: float between 0-1
       proportion of the changes in co2 emissions to be considered in
       further analysis. Default 0.95 (95%)

    returns:
    pandas.dataframe
       dataframe containing as rows the processes that contribute the
       most to changes in GHGe. columns include "co2eq alternative",
       co2eq baseline, difference and absolute difference of CO2eq e
       per process between two scenarios. Ordered by contribution
    """
    df = pd.concat([s_alternative, s_baseline],
                 axis=1,
                 keys=('alternative', 'baseline'),
                 sort=False).fillna(0)

    df.loc[:, 'diffCO2'] = df.loc[:, 'alternative']-df.loc[:,'baseline']
    df.loc[:, 'absdiffCO2'] = abs(df.loc[:, 'diffCO2'])

    if cutoff>=1:
        return(df.sort_values(by='absdiffCO2', ascending=False))
    else:

        # calculate the contribution (%) to abs changes in GHG by process
        # add one by one until we reach the cut-off criterion
        top_p = (df['absdiffCO2']/df['absdiffCO2']\
        .sum()).sort_values(ascending=False, na_position='last')\
        .values.tolist()
        counter=0
        summation=0
        for p in top_p:
            if summation >cutoff:
                break
            summation=summation+p
            counter=counter+1

        df = df.sort_values(by='absdiffCO2', ascending=False)[0:counter]
        df.loc[:, 'contribution'] = df.loc[:, 'absdiffCO2']\
        / df.loc[:, 'absdiffCO2'].sum()*cutoff

    return(df)

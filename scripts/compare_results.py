import os
import csv
import pandas as pd
from os.path import join, basename
import pathlib
import sys
import matplotlib.pyplot as plt

def readData(frames, filename):
      df = pd.read_csv(filename)
      frames.append(df)
      return

def dateEarlierThan(date1, date2):
      # date is in the following form: Tue_Sep_29_22:53:21_2020
      month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
      weekday1,month1,day1,time1,year1,tz = date1.split("_")
      weekday2,month2,day2,time2,year2,tz = date2.split("_")
      if int(year1) < int(year2):
            return True
      if month.index(month1) < month.index(month2):
            return True
      if int(day1) < int(day2):
            return True
      return False

curDir=str(pathlib.Path(__file__).parent.absolute())
dataDir = join(curDir, "../data/")

experiments = []
solvers = []
solverToDate = {} # solver to the latest commit date
solverIdToExperiments = {}
for filename in os.listdir(dataDir):
      if filename == "benchmarks.csv":
            benchmarks = pd.read_csv(join(dataDir, filename))
      else:
            experiments.append(join(dataDir, filename))
            solver,date,commit,args,timeout=filename.split("%%")
            solverId = solver + " " + " ".join(args.split("+"))
            solvers.append(solverId)

            if solverId not in solverToDate:
                  solverIdToExperiments[solverId] = []
            solverIdToExperiments[solverId].append(join(dataDir, filename))
            
            if solver not in solverToDate:
                  solverToDate[solver] = date
            elif dateEarlierThan(solverToDate[solver], date):
                  solverToDate[solver] = date

family = benchmarks.family.unique()
family = ['all'] + family

valueToCompare = ["wall time"]
scheme = ["PAR2", "PAR1"]

benchmark_to_family = {}
for row in benchmarks.values.tolist():
      fam = row[0]
      benchmark = row[1]
      if benchmark not in benchmark_to_family:
            benchmark_to_family[benchmark] = set()
      benchmark_to_family[benchmark].add(fam)

def getPARTime(time, result, par, limit):
      if time > limit or (result not in ['sat', 'unsat']):
            return par * limit
      else:
            return time
      
def getDataForSolver(solverId, metric, scheme, limit):
      experimentsForSolverId = solverIdToExperiments[solverId]
      date = solverToDate[solverId.split()[0]]
      for experiment in experimentsForSolverId:
            if basename(experiment).split("%%")[1] == date:
                  df = pd.read_csv(experiment)[["result",metric, "network", "property"]]
                  df['benchmark'] = df["network"] + "%%" + df["property"]
                  df['solverId'] = solverId
                  if scheme == "PAR1":
                        df[scheme] = df.apply(lambda row: getPARTime(row[metric], row['result'], 1, limit), axis=1)
                  elif scheme == "PAR2":
                        df[scheme] = df.apply(lambda row: getPARTime(row[metric], row['result'], 2, limit), axis=1)
                  df = df.drop(["network", "property"], axis=1)
                  return df
      print("Can't find corresponding experiment!")
      assert(False)

def inFamily(family, benchmark):
      return family in benchmark_to_family[benchmark]
      
def compareSolvers(solverId1, solverId2, metric="wall time", scheme="PAR2", limit=5000, family='all'):
      df1 = getDataForSolver(solverId1, metric, scheme, limit)
      df2 = getDataForSolver(solverId2, metric, scheme, limit)
      df = pd.concat([df1, df2])
      if family != 'all':
            df['family'] = df.apply(lambda row: inFamily(family, row['benchmark']), axis=1)
            df = df[df['family']]
      df = df.pivot(index='benchmark', columns='solverId', values=scheme)
      plt.scatter(df[solverId1], df[solverId2], style='o')
      plt.xlim(0, limit)
      plt.ylim(0, limit)
      plt.show()

def getRanking(metric="wall time", scheme="PAR2"):
      for solverId in solvers:
            df = getDataForSolver(solverId, metric)

def checkConsistency(df):
      return

compareSolvers(solvers[0],solvers[1], valueToCompare[0], limit=1200, family=sys.argv[1])

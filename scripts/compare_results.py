import os
import csv
import pandas as pd
from os.path import join, basename
import pathlib
import sys
import seaborn as sns
import numpy as np
sns.set_theme()
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


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

families = benchmarks.family.unique().tolist()
families = ['all'] + families

valueToCompare = ["wall time"]
scheme = ["PAR2", "PAR1"]
results = ["all", "sat", "unsat"]

benchmark_to_family = {}
for row in benchmarks.values.tolist():
      fam = row[0]
      benchmark = row[1]
      if benchmark not in benchmark_to_family:
            benchmark_to_family[benchmark] = []
      benchmark_to_family[benchmark].append(fam)

def getPARTime(time, result, par, limit):
      if time > limit or result == 'to':
            return par * limit
      elif result == 'mo':
            return par * limit * 1.05
      elif result == 'err':
            return par * limit * 1.1
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

def getFamily(benchmark, fam="all"):
      if fam == 'all' or fam in benchmark_to_family[benchmark]:
            fams = benchmark_to_family[benchmark]
            assert(len(fams) <= 2)
            if fams[0] == 'tests':
                  return fams[1]
            else:
                  return fams[0]
      else:
            return "unknown"

def getResult(results):
      assert(not('sat' in results and 'unsat' in results))
      if 'sat' in results:
            return 'sat'
      if 'unsat' in results:
            return 'unsat'
      return 'unknown'

def compareSolvers(solverId1, solverId2, metric="wall time", scheme="PAR1", limit=5000, family='all', result='all'):
      df1 = getDataForSolver(solverId1, metric, scheme, limit)
      df2 = getDataForSolver(solverId2, metric, scheme, limit)
      df = pd.concat([df1, df2])
      if family != 'all':
            df['family'] = df.apply(lambda row: getFamily(row['benchmark'], family), axis=1)
            df = df[df['family'] == family]
      else:
            df['family'] = df.apply(lambda row: getFamily(row['benchmark'], family), axis=1)
            df = df[df['family'] != "unknown"]

      df_scheme = df.pivot(index='benchmark', columns='solverId', values=scheme).reset_index()
      df_scheme['family'] = df_scheme.apply(lambda row: getFamily(row['benchmark'], family), axis=1)

      df_result = df.pivot(index='benchmark', columns='solverId', values="result").reset_index()
      df_result["result"] = df_result.apply(lambda row: getResult([row[solverId1], row[solverId2]]), axis=1)
      resultMap = df_result.set_index('benchmark').T.to_dict('list')
      df_scheme['result'] = df_scheme.apply(lambda row: resultMap[row['benchmark']][-1], axis=1)
      if result == 'all':
            df_scheme = df_scheme[df_scheme['result'] != 'unknown']
      elif result == 'sat':
            df_scheme = df_scheme[df_scheme['result'] == 'sat']
      elif result == 'unsat':
            df_scheme = df_scheme[df_scheme['result'] == 'unsat']
      else:
            assert(False)

      df_scheme['family'] = df_scheme.apply(lambda row: getFamily(row['benchmark'], family), axis=1)

      plt.figure(figsize=(9,8))
      sns.scatterplot(data=df_scheme, x=solverId1, y=solverId2, hue="family", s=70)
      #plt.scatter(x=solverId1, y=solverId2, data=df_scheme, c="family", label="family")
      plt.legend(bbox_to_anchor=(1.01, 1),borderaxespad=0, fontsize=15)
      plt.plot([0, limit], [0, limit], '--', color='grey')
      plt.text(limit/2 * 0.9, limit * 0.95, '2x', fontsize=12)
      plt.plot([0, limit/2], [0, limit], '--', color='grey', linewidth=0.5)
      plt.plot([0, limit], [0, limit/2], '--', color='grey', linewidth=0.5)
      plt.text(limit/8 * 0.9, limit * 0.95, '8x', fontsize=12)
      plt.plot([0, limit/8], [0, limit], '--', color='grey', linewidth=0.5)
      plt.plot([0, limit], [0, limit/8], '--', color='grey', linewidth=0.5)
      plt.plot([0, limit], [limit, limit], color='grey', linewidth=0.8)
      plt.plot([limit, limit], [0, limit], color='grey', linewidth=0.8)
      plt.plot([0, limit * 1.05], [limit * 1.05, limit * 1.05], color='blue', linewidth=0.8)
      plt.plot([limit * 1.05, limit * 1.05], [0, limit * 1.05], color='blue', linewidth=0.8)
      plt.plot([0, limit * 1.1], [limit * 1.1, limit * 1.1], color='red', linewidth=0.8)
      plt.plot([limit * 1.1, limit * 1.1], [0, limit * 1.1], color='red', linewidth=0.8)
      plt.text(0, limit -25, 'to', fontsize=10)
      plt.text(0, limit * 1.05 - 25, 'mo', fontsize=10)
      plt.text(0, limit * 1.1 - 25, 'err', fontsize=10)

      plt.xlim(0, limit * 1.12)   # set the xlim to left, right
      plt.ylim(0, limit * 1.12)
      plt.xlabel(solverId1, fontsize=15)
      plt.ylabel(solverId2, fontsize=15)
      plt.xticks(fontsize=12)
      plt.yticks(fontsize=12)
      plt.show()

def getRanking(metric="wall time", scheme="PAR2"):
      for solverId in solvers:
            df = getDataForSolver(solverId, metric)

def checkConsistency(df):
      return


def main():
      df = compareSolvers(solvers[3],solvers[0], valueToCompare[0], limit=1200, family=sys.argv[1], result=sys.argv[2])

if __name__ == "__main__":
      main()

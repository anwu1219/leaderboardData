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

#pd.set_option("display.max_rows", None, "display.max_columns", None)

MO_FACTOR=1.4
ERR_FACTOR=2

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

#dataDir = join(curDir, "../data_test/")
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
            if solverId not in solvers:
                  solvers.append(solverId)

            if solverId not in solverIdToExperiments:
                  solverIdToExperiments[solverId] = []
            solverIdToExperiments[solverId].append(join(dataDir, filename))

            if solver not in solverToDate:
                  solverToDate[solver] = date
            elif not dateEarlierThan(solverToDate[solver], date):
                  solverToDate[solver] = date

print(solverToDate)

families = benchmarks.family.unique().tolist()
families = ['all'] + families

valueToCompare = ["wall time"]
results = ["all", "sat", "unsat"]

benchmark_to_family = {}
for row in benchmarks.values.tolist():
      fam = row[0]
      benchmark = row[1]
      if benchmark not in benchmark_to_family:
            benchmark_to_family[benchmark] = []
      benchmark_to_family[benchmark].append(fam)

def getTime(time, result, limit):
      if time > limit or result == 'to':
            return limit
      elif result == 'mo':
            return limit * MO_FACTOR
      elif result == 'err':
            return limit * ERR_FACTOR
      else:
            return time

def getDataForSolver(solverId, metric, limit):
      experimentsForSolverId = solverIdToExperiments[solverId]
      date = solverToDate[solverId.split()[0]]
      for experiment in experimentsForSolverId:
            if basename(experiment).split("%%")[1] == date:
                  df = pd.read_csv(experiment)[["result",metric, "network", "property"]]
                  df['benchmark'] = df["network"] + "%%" + df["property"]
                  df['solverId'] = solverId
                  df["processed_time"] = df.apply(lambda row: getTime(row[metric], row['result'], limit), axis=1)
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

def getResultMap(df, solverIds):
      df_result = df.pivot(index='benchmark', columns='solverId', values="result").reset_index()
      df_result["result"] = df_result.apply(lambda row: getResult([row[solverId] for solverId in solverIds]), axis=1)
      resultMap = df_result.set_index('benchmark').T.to_dict('list')
      for ele in resultMap:
            resultMap[ele] = resultMap[ele][-1]
      return resultMap

def compareSolvers(solverId1, solverId2, metric="wall time", limit=5000, family='all', result='all'):
      if solverId1 == solverId2:
            return
      df1 = getDataForSolver(solverId1, metric, limit)
      df2 = getDataForSolver(solverId2, metric, limit)
      df = pd.concat([df1, df2])

      # select benchmarks, remove unknown benchmarks
      if family != 'all':
            df['family'] = df.apply(lambda row: getFamily(row['benchmark'], family), axis=1)
            df = df[df['family'] == family]
      else:
            df['family'] = df.apply(lambda row: getFamily(row['benchmark'], family), axis=1)
            df = df[df['family'] != "unknown"]

      df_scheme = df.pivot(index='benchmark', columns='solverId', values="processed_time").reset_index()

      # add a column denoting the family that the benchmark belongs
      df_scheme['family'] = df_scheme.apply(lambda row: getFamily(row['benchmark'], family), axis=1)

      resultMap = getResultMap(df, [solverId1, solverId2])

      # select results to show (all/sat/unsat)
      df_scheme['result'] = df_scheme.apply(lambda row: resultMap[row['benchmark']], axis=1)
      if result == 'all':
            df_scheme = df_scheme[df_scheme['result'] != 'unknown']
      elif result == 'sat':
            df_scheme = df_scheme[df_scheme['result'] == 'sat']
      elif result == 'unsat':
            df_scheme = df_scheme[df_scheme['result'] == 'unsat']
      else:
            assert(False)

      # plot
      plt.figure(figsize=(9,8))
      plt.xscale('log')
      plt.yscale('log')

      sns.scatterplot(data=df_scheme, x=solverId1, y=solverId2, hue="family", s=70)
      plt.legend(bbox_to_anchor=(1.01, 1),borderaxespad=0, fontsize=15)
      plt.plot([1, limit], [1, limit], '--', color='grey')
      plt.text(limit/2 * 0.9, limit * 0.95, '2x', fontsize=12)
      plt.plot([1, limit/2], [2, limit], '--', color='grey', linewidth=0.5)
      plt.plot([2, limit], [1, limit/2], '--', color='grey', linewidth=0.5)
      plt.text(limit/8 * 0.9, limit * 0.95, '8x', fontsize=12)
      plt.plot([1, limit/8], [8, limit], '--', color='grey', linewidth=0.5)
      plt.plot([8, limit], [1, limit/8], '--', color='grey', linewidth=0.5)
      plt.plot([0, limit], [limit, limit], color='grey', linewidth=0.8)
      plt.plot([limit, limit], [0, limit], color='grey', linewidth=0.8)
      plt.plot([0, limit * MO_FACTOR], [limit * MO_FACTOR, limit * MO_FACTOR], color='blue', linewidth=0.8)
      plt.plot([limit * MO_FACTOR, limit * MO_FACTOR], [0, limit * MO_FACTOR], color='blue', linewidth=0.8)
      plt.plot([0, limit * ERR_FACTOR], [limit * ERR_FACTOR, limit * ERR_FACTOR], color='red', linewidth=0.8)
      plt.plot([limit * ERR_FACTOR, limit * ERR_FACTOR], [0, limit * ERR_FACTOR], color='red', linewidth=0.8)
      plt.text(1, limit -25, 'to', fontsize=10)
      plt.text(1, limit * MO_FACTOR - 25, 'mo', fontsize=10)
      plt.text(1, limit * ERR_FACTOR - 25, 'err', fontsize=10)

      plt.xlim(1, limit * (ERR_FACTOR + 0.5))   # set the xlim to left, right
      plt.ylim(1, limit * (ERR_FACTOR + 0.5))
      plt.xlabel(solverId1, fontsize=15)
      plt.ylabel(solverId2, fontsize=15)
      plt.xticks(fontsize=12)
      plt.yticks(fontsize=12)
      plt.show()

dataGenerated = False
rankData = {}


# ["PAR1 wall time", "PAR2 wall time", "solved"]
def getRanking(metric="PAR1 wall time", family="all", limit=5000, result='all'):
      if not dataGenerated:
            # Get the data for each solver
            # Each data frame is in the following form:
            dfs = []
            for solverId in solvers:
                  dfs.append(getDataForSolver(solverId, "wall time", limit))
            df = pd.concat(dfs)

            # select benchmarks, remove unknown benchmarks
            if family != 'all':
                  df['family'] = df.apply(lambda row: getFamily(row['benchmark'], family), axis=1)
                  df = df[df['family'] == family]
            else:
                  df['family'] = df.apply(lambda row: getFamily(row['benchmark'], family), axis=1)
                  df = df[df['family'] != "unknown"]

            df_scheme = df.pivot(index='benchmark', columns='solverId', values="processed_time").reset_index()

            # add a column denoting the family that the benchmark belongs
            df_scheme['family'] = df_scheme.apply(lambda row: getFamily(row['benchmark'], family), axis=1)

            resultMap = getResultMap(df, solvers)
            df_scheme['result'] = df_scheme.apply(lambda row: resultMap[row['benchmark']], axis=1)

            # select result
            if result == 'sat':
                  df_scheme = df_scheme[df_scheme['result'] == 'sat']
            elif result == 'unsat':
                  df_scheme = df_scheme[df_scheme['result'] == 'unsat']

            PAR1 = []
            PAR2 = []
            SOLVED = []
            DATE = []
            for solverId in solvers:
                  times = df_scheme[solverId].to_numpy()
                  numInstances = len(times.tolist())
                  SOLVED.append(len(times[times < limit].tolist()))
                  PAR1.append(sum(times[times < limit]) + limit * (numInstances - SOLVED[-1]))
                  PAR2.append(sum(times[times < limit]) + limit * 2 * (numInstances - SOLVED[-1]))
                  DATE.append(" ".join(solverToDate[solverId.split()[0]].split("_")))
            rankData = {"solver":solvers, "Commit date": DATE, "PAR1 wall time": PAR1, "PAR2 wall time": PAR2, "solved": SOLVED}
      df = pd.DataFrame(data=rankData)
      df = df.sort_values(by=[metric], ascending=(metric != "solved"))
      return df


def checkConsistency(df):
      return


def main():
      print(solvers)
      df = compareSolvers(solvers[int(sys.argv[3])], solvers[int(sys.argv[4])], metric="wall time", limit=1200, family=sys.argv[2], result='all')
      #df = getRanking(family=sys.argv[2], metric = "PAR1 wall time", result='all', limit=1200)
      #print(df)

if __name__ == "__main__":
      main()

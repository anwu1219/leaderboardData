import os
import csv
import pandas as pd
from os.path import join

curDir = os.getcwd()
dataDir = join(curDir, "../data/")

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

experiments = []
solvers = []
solverToDate = {}
for filename in os.listdir(dataDir):
      if filename == "benchmarks.csv":
            benchmarks = pd.read_csv(join(dataDir, filename))
      else:
            experiments.append(join(dataDir, filename))
            solver,date,commit,args,timeout=filename.split("%%")
            solverId = solver + " " + " ".join(args.split("+"))
            solvers.append(solverId)
            if solver not in solverToDate:
                  solverToDate[solver] = date
            elif dateEarlierThan(solverToDate[solver], date):
                  solverToDate[solver] = date

family = benchmarks.family.unique()

      

import sys
import os
import sqlite3
import datetime
import numpy as np
#does not support adding new key-value pairs in the dictionary, the number of columns must be manually set with "{}" in ALTER DATA, before logging the data/running!

#connecting to database:

dbname='test'
tablename='measured_data'
colnamelist=['Voltage', 'Current','CurrentTime']


#test dict:
testdict={ 
	"Voltage":"10",
	"Current" :"20",
	"Temperature":"0",

	"Testcol1":10,
	"Testcol2":5
	}

timedict={"CurrentTime":datetime.datetime.now().strftime("%Y%m%d%H%M%S")} #it was the only way i could implement date and time and still select them
#merging the old dict with a new key value pair for time
testdict={**timedict,**testdict}



def connectdb(dbname):
	try:
		global conn 
		conn= sqlite3.connect(dbname)
		conn.commit()
	except sqlite3.connect.Error as err:
		print("Couldn't establish connection {}".format(err))


#cursor setup:

connectdb(dbname)
mycursor = conn.cursor()

#Optional command to delete a table, must be commented out
#mycursor.execute("DROP TABLE measured_data")

#initializing a table with primary key as first column:

def createtable(tablename,dictname):
	
	mycursor.execute("CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY,{} INTEGER,{} REAL,{} REAL,{} TEXT,{} REAL,{} REAL)".format(tablename,*list(dictname.keys())))
	conn.commit()

createtable(tablename,testdict)

#inserting in the measured values:

def updatetable(tablename,dictname):
	
	sql="INSERT INTO {} ({},{},{},{},{},{}) VALUES ({},{},{},{},{},{})" .format(tablename,*list(dictname.keys()),*list(dictname.values()))
	mycursor.execute(sql)
	conn.commit()

updatetable("measured_data",testdict)


def printtable(tablename,dictname,date1,date2):
	
	print("{},{},{},{},{},{},{})".format('id',*list(dictname.keys())))
	sql="SELECT * from {} WHERE CurrentTime BETWEEN {} AND {}".format(tablename,date1,date2)
	mycursor.execute(sql)
	
	data =mycursor.fetchall()
	for row in data:
		print(row)

printtable(tablename,testdict,20180915155243,20190915155242)





def exportdatatoarr (tablename,colnamelist):

	
	array=[]

	sql="SELECT {},{},{} from {} ".format(*colnamelist,tablename)
	mycursor.execute(sql)
	data =mycursor.fetchall()
		
	for row in data:
		array.append(list(row))
		print(row)
	
	nparray=np.asarray(array)	
	print("the numpy array:")
	print(nparray)

exportdatatoarr(tablename,colnamelist)
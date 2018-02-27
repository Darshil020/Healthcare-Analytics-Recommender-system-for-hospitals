# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 22:19:54 2017

@author: Darshil
"""

import requests
import os
import zipfile
import openpyxl
import sqlite3
import glob
import getpass
import requests
import csv
import string
import pandas as pd
import numpy as np
import shutil

#Fetching the Url from the internet 
url="https://data.medicare.gov/views/bg9k-emty/files/0a9879e0-3312-4719-a1db-39fd114890f1?content_type=application%2Fzip%3B%20charset%3Dbinary&filename=Hospital_Revised_Flatfiles.zip"
r=requests.get(url)
staging_dir_name="staging"
#if(os.path.exists(staging_dir_name)==True):  
#    shutil.rmtree(staging_dir_name, ignore_errors=False, onerror=None)
#Making the local directory
os.mkdir(staging_dir_name)
zip_file_name=os.path.join(staging_dir_name, "test.zip")
#Opening the zip file
zf=open(zip_file_name,"wb")
zf.write(r.content)
zf.close()
#Extracting the zip file
z= zipfile.ZipFile(zip_file_name,'r')
z.extractall(staging_dir_name)
z.close()

#Function to actually change the column and table name according to given rules
def rename(name,t):
   y=name.lower() 
   ABC = 'abcdefghijklmnopqrstuvwxyz'
   if y[0] not in ABC:
       if(t=='t'):
           y='t_'+y;
       else:
           y='c_'+y;
   y=y.replace(' ','_')
   y=y.replace('-','_')
   y=y.replace('%','_')
   y=y.replace('/','_')
   return(str(y));

#Code module to change the encoding of the file from cp1252 to UTF-8
glob_dir=os.path.join(staging_dir_name,"*.csv")
for file_name in glob.glob(glob_dir):

    in_fp=open(file_name,"rt",encoding='cp1252')
    input_data=in_fp.read()
    in_fp.close()
    
    file_name_modified=rename(file_name,'t');
    
    ofn=file_name_modified+'.fix'
    out_fp=open(ofn,"wt",encoding='utf-8')
    for c in input_data:
        if c!='\0':
            out_fp.write(c)
    out_fp.close()

#----------------------------------------------------------------------------
#Creating a database and opening a connection
conn=sqlite3.connect("medicare_hospital_compare.db")
#Code block to actually reading the csv files and creating tables like filename and inserting data into tables
glob_dir=os.path.join(staging_dir_name,"*.fix")
for file_name in glob.glob(glob_dir):
    	
    #Below file is currept and hence can not process it 
    if(file_name!='staging\\fy2015_percent_change_in_medicare_payments.csv.fix'):
        c1=conn.cursor()
        #file_name='staging\\timely_and_effective_care___national.csv.fix'
        table_name=os.path.splitext(os.path.splitext(os.path.basename(file_name))[0])[0]
    
        with open(file_name, 'r', newline='',encoding="utf8") as inFile:
            r=csv.reader(inFile)
            #print(file_name)
            #values=[None]*(len(list(r))-1)
         
            header=next(r,None)
            string='';
            
            j=0
            values_list=list(r)
            values=[None]*len(list(values_list))
            for i in values_list:
                
                if len(header)==len(i):
                    temp=i
                    
                    values[j]=tuple(temp);
                    j=j+1
            
        #Dropping the table if alreay exists
        drop_table_query='drop table if exists '+table_name
        c1.execute(drop_table_query)
        #Creating the table
        create_table_query='create table '+table_name+'('+string[:-1]+')'
        c1.execute(create_table_query)
        question_mark_sring='?,'*(len(string[:-1].split(',')))
        question_mark_sring=question_mark_sring[:-1]
        #Creating a insert query
        insert_value_query='insert into '+table_name+'('+string[:-1]+')'+' values '+'('+question_mark_sring+')'+';'
        if file_name=='staging\\mort_readm_april2017.csv.fix' or 'staging\\psi_april2017.csv.fix':
            for i in range(len(values)):
                if i<(len(values)-2):
                    c1.executemany(insert_value_query, [values[i]])
        else:
            c1.executemany(insert_value_query, values)
        conn.commit()
        #print(create_table_query)
        #c1=conn.cursor()    

conn.close()
#c1=conn.cursor()

#Fetchinng the file from internet 
k_url="http://kevincrook.com/utd/hospital_ranking_focus_states.xlxs"
r=requests.get(k_url)
#Saving it in excel file
xf=open("hospital_ranking_focus_states.xlsx","wb")
xf.write(r.content)
xf.close()

wb=pd.read_excel("hospital_ranking_focus_states.xlsx")
#Opening the database connection
conn=sqlite3.connect("medicare_hospital_compare.db")
c1=conn.cursor()
# Reading the data from the database connection
df_sql=pd.read_sql_query('select provider_id,hospital_name,city,state,county_name From  hospital_general_information',conn)
conn.close()

# Reading the data from the excel file
df_excel_sheet1=pd.read_excel('hospital_ranking_focus_states.xlsx','Hospital National Ranking')
#Converting the provier id column type into string 
for i in list(df_excel_sheet1.index):
    df_excel_sheet1.loc[i,'Provider ID']=int(df_excel_sheet1.loc[i,'Provider ID'])
for i in list(df_sql.index):
    df_sql.loc[i,'provider_id']=int(df_sql.loc[i,'provider_id'])

#Merging the tow dataframes by provider id
nation_merge_df=pd.merge(df_sql, df_excel_sheet1, left_on = 'provider_id', right_on = 'Provider ID')
#sorting the final dataframe by Ranking in ascending order
final_nation_df=nation_merge_df.sort_values(by='Ranking')
final_nation_df.index = range(len(final_nation_df))
#final_nation_df_reindexed=final_nation_df.reset_index


#final_nation_df=final_nation_df.set_index(list(range(0,len(final_nation_df)-1)))

final_nation_df1=final_nation_df.loc[:99,['provider_id','hospital_name','city','state','county_name']]
for i in list(final_nation_df1.index):
    final_nation_df1.loc[i,'provider_id']=str(final_nation_df1.loc[i,'provider_id']).zfill(6)
#Changing the column name of the fianl output file
final_nation_df1.columns=['Provider ID','Hospital Name','City','State','County']
#Putting into the excel file
writer = pd.ExcelWriter('hospital_ranking.xlsx')
final_nation_df1.to_excel(writer,'Nationwide',index=False)


#---------------------------------------------------------------------------------
df_excel_sheet2=pd.read_excel('hospital_ranking_focus_states.xlsx','Focus States')
df_excel_sheet2=df_excel_sheet2.sort_values(by='State Name')
conn=sqlite3.connect("medicare_hospital_compare.db")
x=[None]*6;
j=0;
for state in list(df_excel_sheet2.index):
    
    sql_query='select provider_id,hospital_name,city,state,county_name From  hospital_general_information where state='+'"'+df_excel_sheet2.loc[state,'State Abbreviation']+'"'
    df_state=pd.read_sql_query(sql_query,conn)
    for i in list(df_state.index):
        df_state.loc[i,'provider_id']=int(df_state.loc[i,'provider_id'])
    nation_merge_df=pd.merge(df_state, df_excel_sheet1, left_on = 'provider_id', right_on = 'Provider ID')
    final_nation_df=nation_merge_df.sort_values(by='Ranking')
    final_nation_df.index = range(len(final_nation_df))
    #final_nation_df1=final_nation_df.loc[:99,['provider_id','hospital_name','city','state','county_name']]
    for i in list(final_nation_df1.index):
        final_nation_df1.loc[i,'provider_id']=str(final_nation_df1.loc[i,'provider_id']).zfill(6)
        #Changing the column name of the fianl output file
    final_nation_df1.columns=['Provider ID','Hospital Name','City','State','County']
    
    #Putting into the excel file
    
    final_nation_df1.to_excel(writer,df_excel_sheet2.loc[state,'State Name'],index=False)
    

conn.close()
writer.save()
#-------Code for creation on measures_statistics.xlsx file-----------
#estabilishing the connection to database
conn=sqlite3.connect("medicare_hospital_compare.db")
#sql query creation 
sql_query='select state, measure_id, measure_name,score from timely_and_effective_care___hospital'
df=pd.read_sql_query(sql_query,conn)
length=len(df)+1
delete_index=[None]*length
k=0
#Converting the str type dataset into integer for score column
for i in list(df.index):
    
    try:
        df.loc[i,'score']=int(df.loc[i,'score'])
    except ValueError:
        #print(i)
        delete_index[k]=i
        k=k+1
        continue

delete_index=list(filter(None.__ne__, delete_index))
#droping the non integer type of column from the dataframe
df_int=df.drop(df.index[delete_index])
df_stat=df_int

df_int['score'] = df_int['score'].astype(int)
#Group by min,max, average and standard deviation
df_min=(df_int.groupby(['measure_id','measure_name'])['score'].min()).to_frame()
df_max=(df_int.groupby(['measure_id','measure_name'])['score'].max()).to_frame()
df_mean=(df_int.groupby(['measure_id','measure_name'])['score'].mean()).to_frame()
df_std=(df_int.groupby(['measure_id','measure_name'])['score'].std()).to_frame()

#Convering the nultidimentional index into columns of dataframe
df_min.reset_index(inplace=True)
df_max.reset_index(inplace=True)
df_mean.reset_index(inplace=True)
df_std.reset_index(inplace=True)

#Merging different dataframes and creating a final dataframe
final_df=pd.merge(df_min, df_max, left_on = ['measure_id','measure_name'], right_on = ['measure_id','measure_name'])
final_df=pd.merge(final_df, df_mean, left_on = ['measure_id','measure_name'], right_on = ['measure_id','measure_name'])
final_df=pd.merge(final_df, df_std, left_on = ['measure_id','measure_name'], right_on = ['measure_id','measure_name'])

final_df.columns=['Measure ID','Measure Name','Minimum','Maximum','Average','Standard Deviation']
writer = pd.ExcelWriter('measures_statistics.xlsx')
#Saving the final file for first tab
final_df.to_excel(writer,'Nationwide',index=False)
#Fetching the statenames
df_excel_sheet2=pd.read_excel('hospital_ranking_focus_states.xlsx','Focus States')
df_excel_sheet2=df_excel_sheet2.sort_values(by='State Name')
x=[None]*6;
j=0;
for state in list(df_excel_sheet2.index):
    #sql query creation 
    sql_query='select state, measure_id, measure_name,score from timely_and_effective_care___hospital where state='+'"'+df_excel_sheet2.loc[state,'State Abbreviation']+'"'
    df=pd.read_sql_query(sql_query,conn)
    length=len(df)+1
    delete_index=[None]*length
    k=0
    #Converting the str type dataset into integer for score column
    for i in list(df.index):
        
        try:
            df.loc[i,'score']=int(df.loc[i,'score'])
        except ValueError:
            #print(i)
            delete_index[k]=i
            k=k+1
            continue
    
    delete_index=list(filter(None.__ne__, delete_index))
    #droping the non integer type of column from the dataframe
    df_int=df.drop(df.index[delete_index])
    #df_stat=df_int
    
    df_int['score'] = df_int['score'].astype(int)
    #Group by min,max, average and standard deviation
    df_min=(df_int.groupby(['measure_id','measure_name'])['score'].min()).to_frame()
    df_max=(df_int.groupby(['measure_id','measure_name'])['score'].max()).to_frame()
    df_mean=(df_int.groupby(['measure_id','measure_name'])['score'].mean()).to_frame()
    df_std=(df_int.groupby(['measure_id','measure_name'])['score'].std()).to_frame()
    
    #Convering the nultidimentional index into columns of dataframe
    df_min.reset_index(inplace=True)
    df_max.reset_index(inplace=True)
    df_mean.reset_index(inplace=True)
    df_std.reset_index(inplace=True)
    
    #Merging different dataframes and creating a final dataframe
    final_df=pd.merge(df_min, df_max, left_on = ['measure_id','measure_name'], right_on = ['measure_id','measure_name'])
    final_df=pd.merge(final_df, df_mean, left_on = ['measure_id','measure_name'], right_on = ['measure_id','measure_name'])
    final_df=pd.merge(final_df, df_std, left_on = ['measure_id','measure_name'], right_on = ['measure_id','measure_name'])
    
    final_df.columns=['Measure ID','Measure Name','Minimum','Maximum','Average','Standard Deviation']
    #Saving the final file for respective state tab
    final_df.to_excel(writer,df_excel_sheet2.loc[state,'State Name'],index=False)
    

conn.close()
writer.save()
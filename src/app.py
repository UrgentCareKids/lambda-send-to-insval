import pandas as pd
import psycopg2
import json
import pandas.io.sql as sqlio
pd.set_option('display.max_columns', 500)
import boto3
import os
from loguru import logger

def handler(event,context):
    body = event['Records'][0]['Sns']['Message']
    logger.info('got here', event)
    body = json.loads(body)
    queue_id = body['queue_id']
    patient_id = body['patient_id']
    print(event)
    get_patient_details(queue_id, patient_id)

ssm = boto3.client('ssm',  aws_access_key_id=os.environ['KEY'], aws_secret_access_key=os.environ['SECRET'],  region_name='us-east-2')
param = ssm.get_parameter(Name='uck-etl-db-prod-masterdata', WithDecryption=True )
db_request = json.loads(param['Parameter']['Value']) 

ssm_insval = boto3.client('ssm',  aws_access_key_id=os.environ['KEY'], aws_secret_access_key=os.environ['SECRET'],  region_name='us-east-2')
param_insval = ssm_insval.get_parameter(Name='uck-etl-db-ins-val-svc-dev', WithDecryption=True )
db_request_insval = json.loads(param_insval['Parameter']['Value']) 

ssm_redshift = boto3.client('ssm',  aws_access_key_id=os.environ['KEY'], aws_secret_access_key=os.environ['SECRET'],  region_name='us-east-2')
param_redshift = ssm_redshift.get_parameter(Name='uck-etl-wave-hdc', WithDecryption=True )
db_request_redshift = json.loads(param_redshift['Parameter']['Value']) 

def masterdata_conn():
    hostname = db_request['host']
    portno = db_request['port']
    dbname = db_request['database']
    dbusername = db_request['user']
    dbpassword = db_request['password']
    conn = psycopg2.connect(host=hostname,user=dbusername,port=portno,password=dbpassword,dbname=dbname)
    return conn

def insval_conn():
    hostname = db_request_insval['host']
    portno = db_request_insval['port']
    dbname = db_request_insval['database']
    dbusername = db_request_insval['user']
    dbpassword = db_request_insval['password']
    conn_insval = psycopg2.connect(host=hostname,user=dbusername,port=portno,password=dbpassword,dbname=dbname)
    return conn_insval



# def get_patient_details(queue_id, patient_id):
    _targetconnection = masterdata_conn()
    cur = _targetconnection.cursor()
    select_query = f"select mtfd.primary_ins_id, ic.ext_id from mat_tmp_fast_demographics mtfd left join public.ins_cx ic on mtfd.primary_ins_id::bigint = ic.pri_ins_id where mtfd.pond_id = '{patient_id}' and mtfd.primary_ins_id::bigint = ic.pri_ins_id  and ic.ext_source = 'WAVE'"
    cur.execute(select_query,)
    ins_id = cur.fetchall()
    df = pd.DataFrame(ins_id)
    payer_code = ''
    request_type = ''
    patient_first_name = ''
    patient_middle_name = ''
    patient_last_name = ''
    patient_dob = ''
    primary_ins_ph_first_name = ''
    primary_ins_ph_middle_name = ''
    primary_ins_ph_last_name = ''
    primary_ins_ph_dob = ''
    patient_address = ''
    patient_address2 = ''
    patient_address_city = ''
    patient_address_zip = ''
    patient_address_state = ''
    if df.empty == True:
        request_type = 'DISCO'
    else:
        for i in range(len(df)):
            request_type = 'ELIG'
            payer_code = df.iloc[i,1]
    demo_select = f"select mtfd.patient_first_name, mtfd.patient_middle_name, mtfd.patient_last_name, mtfd.patient_dob::date, mtfd.primary_ins_ph_first_name, mtfd.primary_ins_ph_middle_name, mtfd.primary_ins_ph_last_name, mtfd.primary_ins_ph_dob::date, mtfd.patient_address, mtfd.patient_address2, mtfd.patient_address_city, mtfd.patient_address_state, patient_address_zip from mat_tmp_fast_demographics mtfd where mtfd.pond_id = '{patient_id}'"
    cur.execute(demo_select,)
    demo = cur.fetchall()
    df = pd.DataFrame(demo)
    for i in range(len(df)): 
        patient_first_name = df.iloc[i,0]
        patient_middle_name = df.iloc[i,1]
        patient_last_name = df.iloc[i,2]
        patient_dob = df.iloc[i,3]
        primary_ins_ph_first_name = df.iloc[i,4]
        primary_ins_ph_middle_name = df.iloc[i,5]
        primary_ins_ph_last_name = df.iloc[i,6]
        primary_ins_ph_dob = df.iloc[i,7]
        patient_address = df.iloc[i,8]
        patient_address2 = df.iloc[i,9]
        patient_address_city = df.iloc[i,10]
        patient_address_state = df.iloc[i,11]
        patient_address_zip = df.iloc[i,12]
    _targetconnection = insval_conn()
    cur = _targetconnection.cursor()
    print(request_type, payer_code)
    update_query = f"update public.insval_queue set payer_code = '{payer_code}', request_type = '{request_type}' where queue_id = '{queue_id}'"
    cur.execute(update_query,)
    _targetconnection.commit()
    insert_query= f"with insert_cte as (select '{queue_id}'::int, '{patient_id}', nullif('{patient_first_name}','None'), nullif('{patient_middle_name}','None'), nullif('{patient_last_name}','None'), nullif('{patient_dob}','None')::date, nullif('{primary_ins_ph_first_name}','None'), nullif('{primary_ins_ph_middle_name}','None'), nullif('{primary_ins_ph_last_name}','None'), nullif('{primary_ins_ph_dob}','None')::date, nullif('{patient_address}','None'), nullif('{patient_address2}','None'), nullif('{patient_address_city}','None'), nullif('{patient_address_state}','None'), nullif('{patient_address_zip}','None')) INSERT INTO public.insval_demographics(queue_id, patient_id, patient_first_name, patient_middle_name, patient_last_name, patient_dob, primary_ins_ph_first_name, primary_ins_ph_middle_name, primary_ins_ph_last_name, primary_ins_ph_dob, patient_address1, patient_address2, patient_address_city, patient_address_state, patient_address_zip) select * from insert_cte; "        
    cur.execute(insert_query,)
    _targetconnection.commit()
    proc_call= f"call public.insval_distributor('{queue_id}');"
    print('proc call: ', queue_id)
    cur.execute(proc_call,)
    _targetconnection.commit()
    _targetconnection.close()
    print('DONE', request_type, patient_id)



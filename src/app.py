import pandas as pd
import psycopg2
import json
import pandas.io.sql as sqlio
pd.set_option('display.max_columns', 500)
import boto3
import os
from loguru import logger

def handler(event,context):
    # body = event['Records'][0]['Sns']['Message']
    # logger.info('got here', event)
    # body = json.loads(body)
    # patient_id = body['patient_id']
    payload = event
    # json.dumps(payload)
    # json.loads(payload)
    print(payload)
    print(event)
    # insval_process(payload)

ssm = boto3.client('ssm',  aws_access_key_id=os.environ['KEY'], aws_secret_access_key=os.environ['SECRET'],  region_name='us-east-2')
param = ssm.get_parameter(Name='uck-etl-db-prod-masterdata', WithDecryption=True )
db_request = json.loads(param['Parameter']['Value']) 

ssm_insval = boto3.client('ssm',  aws_access_key_id=os.environ['KEY'], aws_secret_access_key=os.environ['SECRET'],  region_name='us-east-2')
param_insval = ssm_insval.get_parameter(Name='uck-etl-db-ins-val-svc-dev', WithDecryption=True )
db_request_insval = json.loads(param_insval['Parameter']['Value']) 



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

def insval_process(payload):
    _targetconnection = insval_conn()
    cur = _targetconnection.cursor()
    proc_call = f"call insval_queue_loader(0, '{payload}');"
    cur.execute(proc_call,)
    _targetconnection.commit()
    _targetconnection.close()
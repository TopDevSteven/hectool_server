from fastapi import FastAPI, Request, HTTPException
from starlette.responses import RedirectResponse
import hashlib
import httpx
import hmac as HM
from urllib.parse import urlencode
import json
import ast
import re

from langchain import OpenAI, SQLDatabase , SQLDatabaseChain
from langchain.chat_models import ChatOpenAI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import openai
import psycopg2
import os
import math


load_dotenv()

#from .env
redirect_uri = os.getenv("Redirect_URL")
api_key = os.getenv("API_KEY")
shared_secret = os.getenv("SECRET_KEY")
access_token = os.getenv("ACCESS_TOKEN")
store_name = os.getenv("SHOPIFY_STORE_NAME")
openai_key = os.getenv("OPENAI_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
database = os.getenv("DB")
db_host = os.getenv("DBHOST")
user = os.getenv("USER")
password = os.getenv("PASSWORD")
db_port = os.getenv("DBPORT")
db_url = os.getenv("DB_URL")
token_limit = 4000
page_limit = 10
store_endpoint = f"https://{store_name}.myshopify.com/admin/products.json?limit={page_limit}"

# Define SQLDatabaseChain

llm = ChatOpenAI(model_name='gpt-3.5-turbo', openai_api_key=openai_key, temperature=0.3)

db = SQLDatabase.from_uri(db_url, include_tables=['products'])

db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True, return_direct = True, return_intermediate_steps=True)


# Connect to the database


conn = psycopg2.connect(database=database,
                        host=db_host,
                        user=user,
                        password=password,
                        port=db_port,
                        sslmode="require"
                        )



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


greetings = ['hello', 'hi', 'Hello', 'Hi']

@app.get("/hello/")
def read_root():
    return "Hello World"



@app.get("/install/")
async def install(shop: str):
    scopes = "read_orders,read_products"
    install_url = f"https://{shop}.myshopify.com/admin/oauth/authorize?client_id={api_key}&scope={scopes}&redirect_uri={redirect_uri}"
    return RedirectResponse(url=install_url)


@app.get("/generate/")
async def generate(request: Request):
    query_params = request.query_params
    hmac = query_params['hmac']
    code  = query_params['code']
    shop  = query_params['shop']
    
    print(query_params)
    param_name_to_remove = "hmac"
    filtered_params = {key: value for key, value in query_params.items() if key != param_name_to_remove}
    sorted_params = dict(sorted(filtered_params.items()))
    print(sorted_params)  
    
    computed_hmac = HM.new(shared_secret.encode(), urlencode(sorted_params).encode(), hashlib.sha256).hexdigest()
    print(computed_hmac)
    
    if HM.compare_digest(hmac, computed_hmac):
        query = {
            "client_id": api_key,
            "client_secret": shared_secret,
            "code": code,
        }
        access_token_url = f"https://{shop}/admin/oauth/access_token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(access_token_url, data=query)   
        result = await response.json()
        print(result)
        
        access_token = result["access_token"]
        return access_token
    
    else:
        raise HTTPException(status_code=401, detail="HMAC verification failed")
    

@app.get("/new-orders/")
async def get_orders():
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    cursor = conn.cursor()
    async def insert(rlt):
        for tool in rlt:
            # print(tool['title'])
            if "Kit" in tool['title']:
                pass
            
            elif "Clamping" in tool['title']:
                name = tool['title'].split(" - ")[0]
                type = tool['title'].split(" - ")[1]
                item = None
                d_min = float(tool['options'][0]['values'][0])
                d_max = float(tool['options'][0]['values'][len(tool['options'][0]['values']) - 1])
                if len(tool['options'][0]['values']) > 1:
                    d_step = float(tool['options'][0]['values'][1]) - float(tool['options'][0]['values'][0])
                else: d_step = None
                shape = tool['title'].split(" - ")[2]
                bore = tool['title'].split(" - ")[3]
                vendor = tool['vendor']
                size = None
                cursor.execute("INSERT INTO products (name, form, ref_no, shape, bore, diameter_min, diameter_max, diameter_step, vendor, size) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (name, type, item, shape, bore, d_min, d_max, d_step, vendor, size))
                conn.commit()
                
            elif "Collets" in tool['title']:
                name = tool['title'].split(" - ")[0]
                type = tool['title'].split(" - ")[1]
                item = tool['title'].split(" - ")[2]
                shape = tool['title'].split(" - ")[3]
                bore = tool['title'].split(" - ")[4]
                vendor = tool['vendor']
                if tool['options'][0]['values'][0] == "-":
                    d_min = None
                    d_max = None
                    d_step = None
                else:
                    d_min = float(tool['options'][0]['values'][0])
                    d_max = float(tool['options'][0]['values'][len(tool['options'][0]['values']) - 1])
                    if len(tool['options'][0]['values']) > 1:
                        d_step = float(tool['options'][0]['values'][1]) - float(tool['options'][0]['values'][0])
                    else: d_step = None
                size = None
                cursor.execute("INSERT INTO products (name, form, ref_no, shape, bore, diameter_min, diameter_max, diameter_step, vendor, size) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (name, type, item, shape, bore, d_min, d_max, d_step, vendor, size))                
                conn.commit()
                
            elif "Chuck" in tool['title']:
                print("THis is Chuck")
                name = tool['title'].split(" Chuck ")[0] + "Chuck"
                vendor = tool['title'].split(" Chuck ")[1].split(" ")[0]
                size = tool['title'].split(" Chuck ")[1].split(" ")[1]
                item = tool['title'].split(" Chuck ")[1].split(" ")[2]
                bore = None
                shape = None
                d_min = float(tool['options'][0]['values'][0])
                d_max = float(tool['options'][0]['values'][len(tool['options'][0]['values']) - 1])
                if len(tool['options'][0]['values']) > 1:
                    d_step = float(tool['options'][0]['values'][1]) - float(tool['options'][0]['values'][0])
                else: d_step = None
                type = None
                cursor.execute("INSERT INTO products (name, form, ref_no, shape, bore, diameter_min, diameter_max, diameter_step, vendor, size) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (name, type, item, shape, bore, d_min, d_max, d_step, vendor, size))
                conn.commit()
                           
            else:
                pass
            
        return "success"
    counturl = "https://hectool-app-development.myshopify.com/admin/products/count.json"
    async with httpx.AsyncClient() as client:
            response = await client.get(counturl, headers=headers)
    count = response.json()['count']
    count = math.ceil(count / page_limit)
    newurl = store_endpoint
    for i in range(count):
        async with httpx.AsyncClient() as client:
            response = await client.get(newurl, headers=headers)
            result = response.json()
            await insert(result['products'])
            if 'next' in response.links:
                newurl = response.links['next']['url']
            # print(newurl)

                # print(response.links)
    return "Success"

@app.post("/chat/")
async def chat(reqeust: Request):
    body = await reqeust.json()
    query = body['query']
    
    if query in greetings:
        return {"message" : "Hi, I'm Hectool Assistant. How are you?"}
    else :
            
        query.replace("ø", "diameter")
        additional_query = """
            No limit.  Make the correct SQL Query based on existing coulmns.
        """
        query += additional_query
        res = db_chain(query)
        steps = res['intermediate_steps']
        # text = steps[0]['input']

        text = steps[2]['sql_cmd']
        coulmns = []
        cur = conn.cursor()
        if "*" in text:
            cur.execute("Select * FROM products LIMIT 0")
            coulmns = [desc[0] for desc in cur.description]   
            # coulmns = [row[1] for row in cur.fetchall()]
        else :
            coulmns = text.split("SELECT ")[1].split("FROM")[0].split(", ")
        print("---------------")
        results = ast.literal_eval(res["result"])
        # if len(results) == 0:
        #     return "Sorry, there is no such tool. Please ask another."
        # else:
            
        message = f"Question:{body['query']} and Result about Question is the following. Coulmns are {coulmns}\n And rows are"
        print("---------------")
        for rlt in results:
            temp = message + str(rlt)
            if len(re.findall(r'\w+', temp)) > token_limit: break
            message += str(rlt) + "\n"
                
        messages = [ {"role": "system", "content": 
                    "You are a intelligent assistant."} ]
        prompt = """
            With the above content, make readable and clear answer like human. Must not be ambigous.
        """

        message = message + prompt
        print(message)
        if message:
            messages.append(
                {"role": "user", "content": message},
            )
            chat = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=messages
            )
        reply = chat.choices[0].message.content
        return {"message": reply}

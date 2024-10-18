# -*- coding: utf-8 -*-
"""SQL_Agent.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1_u_gH0_kQtV7AfZr3D5vjGTPrKDJDa28
"""

#installing Required Libraries
# !pip install langchain pyodbc sqlalchemy langchain-community pymssql langgraph
# !pip install google.generativeai langchain-google-genai langchain-groq

#importing Libraries
#from langchain.sql_database import SQLDatabase
from langchain_community.utilities import SQLDatabase  
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
import numpy as np
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
#from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from typing import Union, List
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from langchain_groq import ChatGroq
from langchain.agents.output_parsers import ReActSingleInputOutputParser
import base64
from langchain.schema import HumanMessage
import os
#from dotenv import load_dotenv
import time
import streamlit as st
import re
# Load environment variables from the .env file
#load_dotenv()

# File uploader widget
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

# Check if a file has been uploaded
if uploaded_file is not None:
   #loading the csv
  input_dataset = pd.read_csv(uploaded_file,encoding='latin-1')
  print(input_dataset.head())
  #creating a sqlite3 connection
  conn = sqlite3.connect('input_dataset.sqlite')
  input_dataset.to_sql('input_dataset',conn,if_exists='replace',index=False)

#Function to read sql query
def read_sql_query(sql,conn):
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    for row in rows:
        print(row)

# input_dataset.head()

# read_sql_query("SELECT * FROM input_dataset WHERE Low >= 24.7 LIMIT 20;",conn)


#OPENAI_API_KEY=userdata.get('OPENAI_API_KEY')
GEMINI_API_KEY= os.getenv('GEMINI_API_KEY')
GROQ_API_KEY=os.getenv('GROQ_API_KEY')


#from langchain.sql_database import SQLDatabase
db = SQLDatabase.from_uri("sqlite:///input_dataset.sqlite")

# print(db.dialect)
# print(db.get_usable_table_names())

# table_name=db.get_usable_table_names()[0]
# globals()[table_name] = df.copy()





llm=ChatGoogleGenerativeAI(model='gemini-1.5-flash',google_api_key=GEMINI_API_KEY)
#llm = ChatGroq(model='llama-3.1-70b-versatile',api_key=GROQ_API_KEY)

##-----------------------------------------------------TOOL-------------------------------------------------------------------##

#visualization Tool Function

class visualize_input(BaseModel):
  table_schema:str = Field(
        description="The schema of the table from the 'InfoSQLDatabaseTool' in string format, dont add any ```,' etc at the end and begenning of the sql_db_schema while giving as input."
    )
  # user_input: Union[str, List[str]] = Field(
  #       description="The original user input question from 'user_input' variable that has been given to the agent. Its not the SQL command."
  #   )

def visualize_data(table_schema : str):
  """ use this tool in case if user wants to visualize the data,
  input to this tool must be the Table Schema from 'InfoSQLDatabaseTool'
  and the user's input question that is required to visualize the data from 'user_input' variable."""
  # Separate schema from the question
  schema_start = table_schema.find("CREATE TABLE")
  schema_end = table_schema.find("*/") + 2  # Include the closing comment
  df_schema = table_schema[schema_start:schema_end].strip()
  question = table_schema[schema_end:].strip()
  print(f'{schema_start,schema_end}')
  print(f'Schema :{df_schema}')
  print(f'Question :{question}')

  #image_details
  img_path = '/mount/src/DOXPLORE/plots'
  os.makedirs(img_path, exist_ok=True)  # Ensure the plots directory exists
  image_filename = f"{img_path}/plot.jpeg"
  if os.path.exists(image_filename):
    os.remove(image_filename)

  # data = df.strip().split('\n')
  # headers = [col.strip() for col in data[2].split('|') if col.strip()]
  # rows = [[cell.strip() for cell in row.split('|') if cell.strip()] for row in data[4:]]
  # # Create a DataFrame
  # df = pd.DataFrame(rows, columns=headers)
  # print(df)
  # df_schema = dict(df.dtypes)
  llm = ChatGoogleGenerativeAI(model='gemini-1.5-flash',google_api_key=GEMINI_API_KEY)
  #llm = ChatGroq(model='llama-3.1-70b-versatile',api_key=GROQ_API_KEY, temperature=0)
  image_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
  prompt_template = PromptTemplate(
        template="""You are an expert in visualizing data using Matplotlib, Seaborn
        . Your response should consist solely of the visualization command, without any additional text following or before the command.

You will be provided with the following:
1. **DataFrame Schema**: The structure of the data you will be visualizing.
2. **User Question**: The specific user input question.

### Instructions:
- **Axis values selection**: in line plots where dates are involved dont use all the date values in X axis, it would be complex for the user to understand. Hence only use as user requested. ( if user asks year wise data, plot only in year wise manner.)
- **Use the Provided Table Name**: Always refer to just the table name from the provided `sql_db_schema` and dont create the table on your own. Do not create or use any other new table names (e.g., 'df').
- **Determine the Best Plot Type**: If the type of visualization is not specified in the question, select the most suitable plot based on the available schema.
- **Specific Chart Requests**: If the user specifies a particular type of chart (e.g., pie chart), respond with the command for that specific plot only.
- **Label Alignment**: Ensure proper alignment of x and y labels with appropriate spacing in the commands.
- **Output Format**: Do not include any markdown characters (e.g., ```, ", etc.) at the beginning or end of your response. Your response should contain only the command.
- **Column Selction** : You should not whole dataset while plotting, you should be able to selectively choose the columns by referring the provided table schema.


### Suggested Plot Types:
- **Box Plot**: For checking outliers in any column.
- **Line Plot**: For examining trends in a column over a specified period. 
- **Bar Plot/KDE Plot**: For analyzing the distribution of a column.
- **Scatter Plot**: For investigating relationships between two numerical columns.
- **Pie Chart**: For displaying proportions of a categorical column.
- **Heatmap**: For assessing correlations between numerical columns.

------------------------------------------------------
**DataFrame Schema**:
\n\n{df_schema}\n\n
------------------------------------------------------
**User Question**:
\n\n{question}\n\n
------------------------------------------------------
"""
,
        input_variables=["df_schema","question"]
    )
  #Here is the query given : \n\n{query}\n\n
  prompt = prompt_template.format(df_schema=df_schema,question = question)
  messages = [{"role": "user", "content": prompt}]
  #print(prompt)
  response = llm.invoke(input=messages)
  command= response.content
  command = command.replace("```python", "").replace("```","").strip()
  save_command = f"\nplt.savefig('{image_filename}', bbox_inches='tight')\n"  # Specify your desired filename and format
  if 'plt.show()' in command:
     save_command = command.replace("plt.show()", f"{save_command}\nplt.show()")
  else:
     save_command = command+save_command
  print(save_command)


  # Execute the save command
  try:
    exec(save_command)
  except Exception as e:
    st.write(f"Error executing save_command: {e}")
  time.sleep(5)
  plot_img = plt.imread(f'{image_filename}')
  # Function to encode the image
  def encode_image(image_path):
    with open(f'{image_path}', "rb") as image_file:
      return base64.b64encode(image_file.read()).decode('utf-8')
  plot_base64 = encode_image(image_filename)
  #prompt for image summary
  image_prompt = """
    You are expert in analyzing the given plot with respect to the given question. \n
    You may be provided with box plots, pie charts, bar graphs, line plots and many more. \n
    Your Job is to analyze the plot and answer according to the given question without leaving any important information. \n
    """
  message = HumanMessage(
                content=[
                    {"type": "text", "text": image_prompt},
                    {"type": "text","text":question},
                    {
                        "type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{plot_base64}"},
                    },
                ]
            )


  # image_prompt = image_prompt.format(plot_image=plot_base64,question=question)
  # img_messages = [{"role": "user", "content": image_prompt}]
  # response = image_llm.invoke(input=img_messages)
  response = image_llm.invoke([message])

  return response.content

visualize_tool = StructuredTool.from_function(
      func=visualize_data,
      name='SQLVisualizeTool',
      description="""use this tool in case if user question can be used to visualize or plot the data,
                    input to this tool must be the sql_db_schema from \'InfoSQLDatabaseTool\'
                   and the user\'s input question that is required to visualize the data from the input.""",
      args_schema=visualize_input,
      return_direct=True,
  )


# print(visualize_tool.name)
# print(visualize_tool.description)
# print(visualize_tool.args)


toolkit = SQLDatabaseToolkit(db=db, llm=llm)

#print(toolkit.get_tools())





prompt = """
System Instructions:

You are an agent designed to interact with a SQL database and visualize data. Your task is to determine whether a given input question can be plotted or visualized.

Steps to Follow:

1. Analyze the Question: Determine if the question can be visualized.

2. If the Question Can Be Visualized:
   - First start by examining the tables in the database to understand what data is available.
   - Query the schema of the most relevant tables to inform your queries.
   - Provide that sql_db_schema(schema with Examples rows of table) along with the input question to the SQLVisualizeTool to create a visualization.
   - End the chain by responding " Visualization has been provided above".

3. If the Question Cannot Be Visualized:
   - Create a syntactically correct SQLite query to retrieve relevant data.
   - Order the results by a relevant column to present the most interesting examples.
   - In case if a table is requested return the results of a table only in HTML format with <table>, <tr>, <th>, and <td> tags. Do not include any other text or commentary.  .

Important Guidelines:
- Always start by examining the tables in the database to understand what data is available.
- Query the schema of the most relevant tables to inform your queries.
- Provide sql_db_schema as an input to SQLVisualizeTool. 
- dont utilise SQLVisualizeTool when the user question cant be answered visually. Use the remaining tools to answer the query.
- Avoid querying all columns from any specific table; only request the columns relevant to the user’s question.
- Double-check your queries for syntax errors before executing them.
- Do not perform any DML statements (INSERT, UPDATE, DELETE, DROP, etc.) on the database.

"""

# from langgraph.prebuilt import create_react_agent

# agent_executor = create_react_agent(
#     llm, tools, state_modifier=system_message

output_parser = ReActSingleInputOutputParser()

from langchain.agents import AgentType, tool, create_sql_agent
agent = create_sql_agent(llm, toolkit, prefix=prompt,extra_tools=[visualize_tool],verbose=True,
    output_parser=output_parser,  # Set the custom output parser
    handle_parsing_errors=True)

#query = 'i need proportion of top 10 companies of laptop in pie chart?'
query = st.text_input(label='Enter your query here:')

if st.button("PROCEED") and query and uploaded_file:
   img_path = '/mount/src/DOXPLORE/plots'
   os.makedirs(img_path, exist_ok=True)  # Ensure the plots directory exists
   image_filename = f"{img_path}/plot.jpeg"
   if os.path.exists(image_filename):
    os.remove(image_filename)
   response=agent.invoke({'input': query})
   #st.write(agent.stream({'input': query}))
   output = response['output']
   #print(response)
   if (bool(re.search(r'<table>.*</table>', output, re.DOTALL))):
      response_df = pd.read_html(output)[0]
      st.dataframe(response_df)
   else:
      st.write(response)
      if os.path.exists(image_filename):
         st.image('/mount/src/DOXPLORE/plots/plot.jpeg')
      else:
         pass
else:
   st.write('Please upload the csv, question and click PROCEED button.')

# print('- 2006: Open Price - 28.5, Close Price - 28\n- 2007: Open Price - 27.5, Close Price - 27.5\n- 2008: Open Price - 24, Close Price - 23.5\n- 2009: Open Price - 19, Close Price - 18.5\n- 2010: Open Price - 20, Close Price - 20\n- 2011: Open Price - 22, Close Price - 22\n- 2012: Open Price - 26, Close Price - 26\n- 2013: Open Price - 32, Close Price - 31.5\n- 2014: Open Price - 33, Close Price - 32.5\n- 2015: Open Price - 36.5, Close Price - 36.5\n- 2016: Open Price - 37.5, Close Price - 37.5')

# input_dataset.head()

# events = agent.stream({'input':user_input})

# events=agent.stream({'input':query})

# agent_executor.invoke({'messages':[('user',"give me the 20 row details about Acer laptops in this dataset?")]})

# for event in events:
#   print(event['messages'][-1].pretty_print())

# xxx= '''CREATE TABLE laptop_price (
# 	"Laptop" TEXT,
# 	"Status" TEXT,
# 	"Brand" TEXT,
# 	"Model" TEXT,
# 	"CPU" TEXT,
# 	"RAM" INTEGER,
# 	"Storage" INTEGER,
# 	"Storage type" TEXT,
# 	"GPU" TEXT,
# 	"Screen" REAL,
# 	"Touch" TEXT,
# 	"Final Price" REAL
# )

# /*
# 3 rows from laptop_price table:
# Laptop	Status	Brand	Model	CPU	RAM	Storage	Storage type	GPU	Screen	Touch	Final Price
# ASUS ExpertBook B1 B1502CBA-EJ0436X Intel Core i5-1235U/8GB/512GB SSD/15.6"	New	Asus	ExpertBook	Intel Core i5	8	512	SSD	None	15.6	No	1009.0
# Alurin Go Start Intel Celeron N4020/8GB/256GB SSD/15.6"	New	Alurin	Go	Intel Celeron	8	256	SSD	None	15.6	No	299.0
# ASUS ExpertBook B1 B1502CBA-EJ0424X Intel Core i3-1215U/8GB/256GB SSD/15.6"	New	Asus	ExpertBook	Intel Core i3	8	256	SSD	None	15.6	No	789.0
# */, Can you visualize top 10 brands of laptops in pie chart?'''

# visualize_tool.run(xxx)

# plt.figure(figsize=(10, 10))
# laptop_price['Brand'].value_counts().nlargest(10).plot(kind='pie', autopct='%1.1f%%', startangle=90)
# plt.title('Top 10 Laptop Brands')
# plt.axis('equal')
# plt.show()



# import pandas as pd
# from io import StringIO


# # Convert the Markdown table to a DataFrame
# data = xx.strip().split('\n')
# headers = [col.strip() for col in data[2].split('|') if col.strip()]
# rows = [[cell.strip() for cell in row.split('|') if cell.strip()] for row in data[4:]]

# # Create a DataFrame
# df = pd.DataFrame(rows, columns=headers)

# # Display the DataFrame
# print(df)



# visualize_data(df,"In Asus Brand,what is the count of each GPU type?")

# import matplotlib.pyplot as plt
# import seaborn as sns

# df['Brand'].value_counts(normalize=True).nlargest(10).plot(kind='pie', autopct='%1.1f%%')
# plt.show()

# ```python
# import matplotlib.pyplot as plt
# import seaborn as sns

# df['Brand'].value_counts(normalize=True).nlargest(10).plot(kind='pie', autopct='%1.1f%%')
# plt.title('Proportion of Top 10 Laptop Brands')
# plt.show()
# ```




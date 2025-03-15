



from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI embeddings and Chroma vector store
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
persist_directory = "db"
vector_store = None

# Custom prompt template
prompt_template = """You are an AI assistant and your name is Black Hole Created by Tharun Baikani. 
Use the following context to answer the question. If you don't know the answer, just say that you don't know.

Context: {context}

Question: {question}
Answer:"""
PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI is running with LangChain!"}

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    global vector_store
    
    # Save uploaded file
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Process PDF with LangChain
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    texts = text_splitter.split_documents(pages)
    
    # Create vector store
    vector_store = Chroma.from_documents(
        documents=texts,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    
    return {"message": "PDF uploaded and processed successfully."}

@app.post("/query/")
async def query_rag(query: str = Form(...)):
    if not vector_store:
        return {"response": "Please upload a document first."}
    
    try:
        # Create QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0),
            chain_type="stuff",
            retriever=vector_store.as_retriever(),
            chain_type_kwargs={"prompt": PROMPT}
        )
        
        result = qa_chain.invoke({"query": query})
        return {"response": result["result"]}
    
    except Exception as e:
        return {"response": f"Error processing query: {str(e)}"}
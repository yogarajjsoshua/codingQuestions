from dotenv import load_dotenv
from fastapi import FastAPI
from huggingface_hub import login
from pydantic import BaseModel

load_dotenv()
login(token=os.getenv("HF_TOKEN"))

class users(BaseModel):
    id: int
    usr_name: str
    usr_age: int


app = FastAPI()


@app.post("/users")
def create_user(user: users):
    return {"message": "User created successfully"}


@app.get("/users/{id}")
def get_users(id: int):
    return {"message": "Users fetched successfully", "id": id}

from fastapi import FastAPI
from pydantic import BaseModel

class users(BaseModel):
    id:int
    usr_name:str
    usr_age:int

app = FastAPI()

app.post("/users")
def create_user(user:users):
    return {"message":"User created successfully"}

app.get("/users/{id}")
def get_users(id:int):
    return {"message":"Users fetched successfully", "id":id}

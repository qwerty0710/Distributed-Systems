from fastapi import FastAPI, Body, HTTPException, status
from typing import Optional, List, Dict
import uvicorn
import mysql.connector as sql
app = FastAPI()

# Placeholder for shard data
shard_data: Dict[str, List] = {
    "sh1": [],
    "sh2": [],
}

sql.connect(host="localhost",user="root",password="abc")


@app.post("/config")
async def configure_shards(schema:str = Body(...), shards: List[str] = Body(...)):

    """Configures shards."""
    for shard in shards:
        shard_data[shard] = []
    return {
        "message": f"Server0:{', '.join(shards)} configured",
        "status": "success",
    }


@app.get("/heartbeat")
async def heartbeat(data:int = Body(...) ):
    """Responds to heartbeat requests."""
    return status.HTTP_200_OK
from fastapi import FastAPI, Body, HTTPException, status, Request


@app.get("/copy")
async def copy_data(shards: List[str] = Body(...)):
    """Copies data for specified shards."""
    response_data = {shard: shard_data[shard] for shard in shards}
    response_data["status"] = "success"
    return response_data


@app.post("/read")
async def read_data(shard: str, low: int, high: int):
    """Reads data within a specified range from a shard."""
    filtered_data = [
        entry for entry in shard_data[shard] if low <= entry["Stud_id"] <= high
    ]
    return {"data": filtered_data, "status": "success"}


@app.post("/write")
async def write_data(shard: str, data: dict):
    """Writes data to a shard."""
    shard_data[shard].append(data)
    return {"message": "Data entry added", "status": "success"}


@app.put("/update")
async def update_data(shard: str, stud_id: int, data: dict):
    """Updates data for a specific Stud_id in a shard."""
    for i, entry in enumerate(shard_data[shard]):
        if entry["Stud_id"] == stud_id:
            shard_data[shard][i] = data
            return {
                "message": f"Data entry for Stud_id:{stud_id} updated",
                "status": "success",
            }
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Data entry for Stud_id:{stud_id} not found",
    )


@app.delete("/del")
async def delete_data(shard: str, stud_id: int):
    """Deletes data for a specific Stud_id in a shard."""
    for i, entry in enumerate(shard_data[shard]):
        if entry["Stud_id"] == stud_id:
            del shard_data[shard][i]
            return {
                "message": f"Data entry with Stud_id:{stud_id} removed",
                "status": "success",
            }
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Data entry for Stud_id:{stud_id} not found",
    )


if __name__ == "__main__":

    uvicorn.run("server:app", host="0.0.0.0", port=5000, log_level="info")

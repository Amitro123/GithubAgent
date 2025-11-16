from fastapi import FastAPI, Request
import uvicorn
from repofactor.application.agent_service.multi_agent_orchestrator import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()
app = FastAPI()

@app.get("/agent/status")
async def agent_status():
    return {"status": "Agent is running", "health": "OK"}

@app.post("/agent/run")
async def agent_run(request: Request):
    payload = await request.json()
    # כאן תקרא ל-Flow שלך; אפשר לייבא orchestrator ולהפעיל אותו
    # לדוג':
    # from repofactor.application.agent_service.multi_agent_orchestrator import MultiAgentOrchestrator
    # orchestrator = MultiAgentOrchestrator()
    # result = await orchestrator.run_full_flow(...)
    return {"result": "Flow executed", "received": payload}

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)

import threading

import aiohttp


class Heartbeat(threading.Thread):
    fails={}
    server_list = []

    async def make_request(server_name, payload, path):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"http://{server_name}:5000/{path}", data=json.dumps(payload),
                                        timeout=2) as response:
                    content = await response.read()
                    if response.status != 404:
                        return response.json(content_type="application/json")
                    else:
                        return {"message": f"<Error> '/{path}’ endpoint does not exist in server replicas",
                                "status": "failure"}, 400
        except Exception as e:
            if e is aiohttp.ServerTimeoutError or
    async def run(self,*args,**kwargs):
        try:
            make_request()
    def add_server(self,server_name):

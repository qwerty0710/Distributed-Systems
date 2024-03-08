#!/bin/bash
uvicorn loadbalancer:app --port 5000 --host "0.0.0.0"
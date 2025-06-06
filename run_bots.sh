#!/bin/bash
cd "$(dirname "$0")"
nohup python3 run_all.py > bots.log 2>&1 &
echo $! > bots.pid
echo "Боты запущены (PID $(cat bots.pid))."

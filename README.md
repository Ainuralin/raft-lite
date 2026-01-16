# Raft Lite Cluster — Minimal Run Instructions

## Prerequisites
- Ubuntu EC2 instances
- Connect to Nodes from PowerShell
```bash
ssh -i <key-name.pem> ubuntu@<NODE_PUBLIC_IP> #For all three nodes
```
- Node Creation
```bash
nano node.py #For node A, B and C
```
- Package Updates
```bash
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install flask requests
```
## Start Nodes
```bash
# Node A
python3 node.py A 8000 172.31.24.36:8001,172.31.17.55:8002 #From node A to B and C

# Node B
python3 node.py B 8001 172.31.17.9:8000,172.31.17.55:8002 #From node B to A and C

# Node C
python3 node.py C 8002 172.31.17.9:8000,172.31.24.36:8001 #From node C to A and B
```

## Check Status
```bash
curl http://<NODE_PRIVATE_IP>:<PORT>/status #For checking the status of nodes after connecting to them
```

## Send Client Command
```bash
curl -X POST http://<LEADER_PRIVATE_IP>:<PORT>/client_command -H "Content-Type: application/json" -d '{"command":"SET x = 5"}'
```

## Failure Testing

# Leader crash
# Stop leader (CTRL+C), then check new leader
```bash
curl http://<NODE_PRIVATE_IP>:<PORT>/status #For node A, B and C
```

# Follower crash
# Stop a follower, send command to leader, restart follower
```bash
curl -X POST http://<LEADER_PRIVATE_IP>:<PORT>/client_command -d '{"command":"SET y = 5"}'
curl http://<RESTARTED_FOLLOWER_IP>:<PORT>/status #For nodes B and C
```

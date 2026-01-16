from flask import Flask, request, jsonify
import threading
import time
import sys
import requests
import random

app = Flask(__name__)

node_id = None
port = None
peers = []

currentTerm = 0
votedFor = None
log = [] # [{term, command}]
commitIndex = -1

state = "Follower" # Follower | Candidate | Leader
leaderId = None

lastHeartbeat = time.time()
votesReceived = 0

LOCK = threading.Lock()


def log_print(msg):
    print(f"[Node {node_id}] {msg}", flush=True)

def majority():
    return (len(peers) + 1) // 2 + 1


@app.route("/request_vote", methods=["POST"])
def request_vote():
    global currentTerm, votedFor, state

    data = request.json
    term = data["term"]
    candidate = data["candidateId"]

    with LOCK:
        if term < currentTerm:
            return jsonify({"term": currentTerm, "voteGranted": False})

        if term > currentTerm:
            currentTerm = term
            votedFor = None
            state = "Follower"

        if votedFor is None or votedFor == candidate:
            votedFor = candidate
            log_print(f"Voted for {candidate} (term {term})")
            return jsonify({"term": currentTerm, "voteGranted": True})

        return jsonify({"term": currentTerm, "voteGranted": False})


@app.route("/append_entries", methods=["POST"])
def append_entries():
    global currentTerm, state, lastHeartbeat, leaderId, log, commitIndex

    data = request.json
    term = data["term"]
    leaderId = data["leaderId"]
    entries = data["entries"]
    leaderCommit = data.get("leaderCommit", commitIndex)

    with LOCK:
        if term < currentTerm:
            return jsonify({"success": False, "term": currentTerm})

        currentTerm = term
        state = "Follower"
        lastHeartbeat = time.time()

        if entries:
            for entry in entries:
                log.append(entry)
                log_print(f"Appended entry {entry}")

        if leaderCommit > commitIndex:
            commitIndex = min(leaderCommit, len(log) - 1)
            log_print(f"Commit index updated to {commitIndex}")

        return jsonify({"success": True, "term": currentTerm})


@app.route("/client_command", methods=["POST"])
def client_command():
    global log, commitIndex

    if state != "Leader":
        return jsonify({"error": "Not leader", "leader": leaderId}), 403

    cmd = request.json["command"]

    with LOCK:
        entry = {"term": currentTerm, "command": cmd}
        log.append(entry)
        index = len(log) - 1
        log_print(f"Append log entry (term={currentTerm}, cmd={cmd})")

    acks = 1  # leader itself

    for peer in peers:
        try:
            r = requests.post(
                f"http://{peer}/append_entries",
                json={
                    "term": currentTerm,
                    "leaderId": node_id,
                    "entries": [entry],
                    "leaderCommit": commitIndex
                },
                timeout=2
            )
            if r.json()["success"]:
                acks += 1
        except:
            pass

    if acks >= majority():
        commitIndex = index
        log_print(f"Entry committed (index={commitIndex})")
        return jsonify({"status": "committed"})

    return jsonify({"status": "not_committed"})


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "id": node_id,
        "state": state,
        "term": currentTerm,
        "leader": leaderId,
        "log": log,
        "commitIndex": commitIndex
    })


def election_timer():
    global state, currentTerm, votedFor, votesReceived

    while True:
        time.sleep(0.3)
        timeout = random.uniform(3, 5)

        with LOCK:
            if state == "Follower" and time.time() - lastHeartbeat > timeout:
                state = "Candidate"
                currentTerm += 1
                votedFor = node_id
                votesReceived = 1
                log_print(f"Timeout → Candidate (term {currentTerm})")

        if state == "Candidate":
            start_election()


def start_election():
    global votesReceived, state, leaderId

    for peer in peers:
        try:
            r = requests.post(
                f"http://{peer}/request_vote",
                json={"term": currentTerm, "candidateId": node_id},
                timeout=2
            )
            if r.json()["voteGranted"]:
                votesReceived += 1
        except:
            pass

    if votesReceived >= majority():
        state = "Leader"
        leaderId = node_id
        log_print("Elected Leader")


def heartbeat_loop():
    while True:
        time.sleep(1)
        if state == "Leader":
            for peer in peers:
                try:
                    requests.post(
                        f"http://{peer}/append_entries",
                        json={
                            "term": currentTerm,
                            "leaderId": node_id,
                            "entries": [],
                            "leaderCommit": commitIndex
                        },
                        timeout=1
                    )
                except:
                    pass


if __name__ == "__main__":
    node_id = sys.argv[1]
    port = int(sys.argv[2])
    peers = sys.argv[3].split(",")

    threading.Thread(target=election_timer, daemon=True).start()
    threading.Thread(target=heartbeat_loop, daemon=True).start()

    log_print("Node started")
    app.run(host="0.0.0.0", port=port)

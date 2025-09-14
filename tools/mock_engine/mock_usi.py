import sys, time

pos = "startpos"

def send(s): 
    sys.stdout.write(s + "\n"); sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    if line == "usi":
        send("id name MockUSI")
        send("id author dev")
        send("usiok")
    elif line == "isready":
        send("readyok")
    elif line.startswith("setoption"):
        pass
    elif line.startswith("position"):
        pos = line
    elif line.startswith("go"):
        import random
        start_time = time.time()
        depth = 1
        while time.time() - start_time < 2.0:
            cp_score = random.randint(-200, 200)
            nps = random.randint(100000, 500000)
            moves = ["7g7f", "3c3d", "2g2f", "4c4d", "2f2e"]
            pv = " ".join(moves[:random.randint(1, 4)])
            send(f"info depth {depth} score cp {cp_score} nps {nps} pv {pv}")
            time.sleep(0.2)
            depth += 1
            if depth > 10:
                depth = 10
        best_moves = ["7g7f", "2g2f", "6g6f", "8g8f", "9g9f"]
        bestmove = random.choice(best_moves)
        send(f"bestmove {bestmove}")
    elif line == "quit":
        break

"""
Start bot and worker simultaneously
"""
import subprocess
import sys

def main():
    print("🚀 Starting OpiPoliX Bot + Auto-Trade Worker...", flush=True)
    
    # Start both processes
    processes = []
    
    # Pass all environment variables
    import os
    env = os.environ.copy()
    
    # Bot
    print("▶️ Starting bot...", flush=True)
    bot_process = subprocess.Popen(
        [sys.executable, "app/bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True,
        env=env
    )
    processes.append(("bot", bot_process))
    
    # Worker
    print("▶️ Starting worker...", flush=True)
    worker_process = subprocess.Popen(
        [sys.executable, "app/auto_trade_worker.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True,
        env=env
    )
    processes.append(("worker", worker_process))
    
    print("✅ Both processes started!", flush=True)
    print("📊 Monitoring outputs...\n", flush=True)
    
    # Read output from both processes
    import select
    
    while True:
        for name, process in processes:
            # Check if process exited
            if process.poll() is not None:
                print(f"❌ {name} stopped! Exit code: {process.returncode}", flush=True)
                # Kill all processes
                for _, p in processes:
                    p.kill()
                sys.exit(1)
            
            # Read stdout
            try:
                line = process.stdout.readline()
                if line:
                    print(f"[{name}] {line.strip()}", flush=True)
            except:
                pass
            
            # Read stderr (critical errors only)
            try:
                line = process.stderr.readline()
                if line:
                    # Ignore traceback lines, show only final error
                    if not any(x in line for x in ['File "', 'Traceback', '^^^^', '^^^', 'yield']):
                        print(f"[{name}] ERROR: {line.strip()}", file=sys.stderr, flush=True)
            except:
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Shutting down...")
        sys.exit(0)

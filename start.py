"""
Запуск бота и worker одновременно
"""
import subprocess
import sys

def main():
    print("🚀 Starting OpiPoliX Bot + Auto-Trade Worker...", flush=True)
    
    # Запускаем оба процесса
    processes = []
    
    # Передаём все переменные окружения
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
        env=env  # ← ПЕРЕДАЁМ ENV!
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
        env=env  # ← ПЕРЕДАЁМ ENV!
    )
    processes.append(("worker", worker_process))
    
    print("✅ Both processes started!", flush=True)
    print("📊 Monitoring outputs...\n", flush=True)
    
    # Читаем вывод обоих процессов
    import select
    
    while True:
        for name, process in processes:
            # Проверяем завершился ли процесс
            if process.poll() is not None:
                print(f"❌ {name} stopped! Exit code: {process.returncode}", flush=True)
                # Убиваем все процессы
                for _, p in processes:
                    p.kill()
                sys.exit(1)
            
            # Читаем stdout
            try:
                line = process.stdout.readline()
                if line:
                    print(f"[{name}] {line.strip()}", flush=True)
            except:
                pass
            
            # Читаем stderr
            try:
                line = process.stderr.readline()
                if line:
                    print(f"[{name}] ERROR: {line.strip()}", file=sys.stderr)
            except:
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Shutting down...")
        sys.exit(0)

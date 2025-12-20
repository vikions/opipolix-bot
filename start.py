"""
Запуск бота и worker одновременно
"""
import subprocess
import sys

def main():
    print("🚀 Starting OpiPoliX Bot + Auto-Trade Worker...")
    
    # Запускаем оба процесса
    processes = []
    
    # Bot
    print("▶️ Starting bot...")
    bot_process = subprocess.Popen(
        [sys.executable, "app/bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    processes.append(("bot", bot_process))
    
    # Worker
    print("▶️ Starting worker...")
    worker_process = subprocess.Popen(
        [sys.executable, "app/auto_trade_worker.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    processes.append(("worker", worker_process))
    
    print("✅ Both processes started!")
    print("📊 Monitoring outputs...\n")
    
    # Читаем вывод обоих процессов
    import select
    
    while True:
        for name, process in processes:
            # Проверяем завершился ли процесс
            if process.poll() is not None:
                print(f"❌ {name} stopped! Exit code: {process.returncode}")
                # Убиваем все процессы
                for _, p in processes:
                    p.kill()
                sys.exit(1)
            
            # Читаем stdout
            try:
                line = process.stdout.readline()
                if line:
                    print(f"[{name}] {line.strip()}")
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

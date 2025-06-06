#!/bin/bash
cd "$(dirname "$0")"
# Убиваем все процессы run_all.py
echo "Убиваем все процессы run_all.py..."
pkill -f run_all.py
# Ждём пару секунд (на всякий случай)
sleep 2
# Проверяем ещё раз — вдруг кто-то уцелел
pgrep -fl run_all.py
if [ $? -eq 0 ]; then
    echo "ВНИМАНИЕ! Некоторые процессы все еще живы! Убиваю повторно..."
    pkill -9 -f run_all.py
fi
rm -f bots.pid
echo "Боты остановлены. Все процессы run_all.py убиты."

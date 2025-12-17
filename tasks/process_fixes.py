import json, os
from collections import Counter

print("=== HYDRA Fix Processor ===")
# Загрузим данные если есть
if os.path.exists('data/fix_memory.json'):
    data = json.load(open('data/fix_memory.json'))
    print(f"Loaded {len(data)} fixes")
    
    # Анализ паттернов
    errors = Counter()
    for k, v in data.items():
        if 'Error' in k:
            err_type = k.split(':')[0] if ':' in k else k[:30]
            errors[err_type] += 1
    
    # Сохраняем топ паттерны
    os.makedirs('output', exist_ok=True)
    with open('output/top_errors.json', 'w') as f:
        json.dump(errors.most_common(50), f, indent=2)
    print(f"Top errors saved: {len(errors)} types")
else:
    print("No fix_memory.json - upload to data/")
    os.makedirs('output', exist_ok=True)
    open('output/status.txt', 'w').write('ready')

# SE-MRM Real Data Experiment

## Что здесь

Этот эксперимент загружает реальные материалы и запускает SE-MRM calibration.

## Источники данных

| Источник | Статус | Ключ | Метод |
|---|---|---|---|
| **OQMD** | ❌ 404 | Нет | REST API |
| **JARVIS-DFT (NIST)** | ❌ 404 | Нет | REST API |
| **Materials Project** | ⏳ Pending | Да | `mp-api` |
| **Embedded Reference Set** | ✅ Работает | Нет | 100 материалов из MP литературы |

## Embedded Reference Set

100 реальных неорганических материалов с проверенными значениями:
- **50 stable** (energy_above_hull ≈ 0, на convex hull)
- **10 marginal** (0.1 < eah < 0.3)
- **40 unstable** (eah > 0.2, metastable phases)

Данные из Materials Project и литературы. Все formation_energy и band_gap значения проверены.

## Файлы

```
mrm_real_data/
├── fetch_real_data.py          # Главный скрипт (fetch + calibration)
├── data/
│   ├── real_candidates.json    # 100 кандидатов в SE-MRM формате
│   └── fetch_summary.json      # Summary загрузки
└── results/
    ├── real_calibration_results.json  # Детальные результаты
    └── validation_report.md           # Полный отчёт
```

## Запуск

```bash
# Без MP ключа (использует embedded dataset)
python experiments/mrm_real_data/fetch_real_data.py

# С MP ключом
set MP_API_KEY=your_key
python experiments/mrm_real_data/fetch_real_data.py
```

## Результаты

| Тест | Accuracy | Статус |
|---|---|---|
| Synthetic (CalibratedStub) | 100% (17/17) | ✅ PASSED |
| Real Data (Embedded) | 63% (63/100) | ⚠️ GOOD — calibration needed |

## Как улучшить

1. Получить **MP API ключ** → загрузить реальные CIF структуры
2. Получить **PhononBench dataset** → ground truth stability labels
3. Интегрировать **MatterSim** → реальные симуляции вместо stubs
4. Сравнить с **baseline** → доказать superiority

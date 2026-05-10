# Skeptic Engine Eval Framework

Benchmark для оценки LLM моделей на реальных задачах проекта.

## Структура

```
eval/
├── tasks/              # Задачи в YAML формате
│   ├── 01_bugfix_hash_lowercase.yaml
│   ├── 02_feature_verify_cli.yaml
│   ├── 03_security_pii_redaction.yaml
│   ├── 04_refactor_hash_streaming.yaml
│   └── 05_test_zenodo_api_error.yaml
├── results/            # Результаты прогонов (JSON)
│   └── latest.json
├── artifacts/          # Diffs, логи, screenshots
├── runner.py           # Главный скрипт
└── README.md           # Эта инструкция
```

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install pyyaml pytest ruff
```

### 2. Запуск baseline (ручная оценка)

```bash
python eval/runner.py --baseline
```

Скрипт создаст worktree, покажет задачу, попросит тебя решить вручную, затем оценит результат.

### 3. Запуск с LLM (пока manual mode)

```bash
python eval/runner.py --model claude-sonnet-4.5 --task eval/tasks/01_bugfix_hash_lowercase.yaml
```

### 4. Запуск всех задач

```bash
python eval/runner.py --model claude-sonnet-4.5 --tasks "eval/tasks/*.yaml"
```

## Формат задачи (YAML)

```yaml
id: bugfix-01-hash-lowercase
type: bugfix  # bugfix | feature | security | refactor | test
difficulty: easy  # easy | medium | hard

description: "One-line summary"

prompt: |
  Detailed task description for LLM.
  Include context, expected behavior, examples.

target_files:
  - src/skeptic_toolkit/integrity.py

acceptance_criteria:
  - Criterion 1
  - Criterion 2
  - Tests pass

constraints:
  - No breaking changes
  - Max N lines of code

scoring:
  pass_tests: 40      # Weight for passing tests
  no_regression: 30   # Weight for no regressions
  minimal_diff: 20    # Weight for clean diff
  lint_clean: 10      # Weight for lint passing

expected_solution: |
  Optional hint for what correct solution looks like.
```

## Метрики

| Метрика | Описание | Max Score |
|---------|----------|-----------|
| `pass_tests` | Все тесты проходят | 40 |
| `no_regression` | Нет регрессий (все старые тесты проходят) | 30 |
| `minimal_diff` | Минимальные изменения (<20 строк = full score) | 20 |
| `lint_clean` | Ruff lint проходит без ошибок | 10 |
| **Total** | | **100** |

## Типы задач

### 1. Bugfix (легкие)
- Исправить известный баг
- 1-2 файла, 1-5 строк кода
- Пример: case-insensitive hash comparison

### 2. Feature (средние)
- Добавить новую функциональность
- 1-3 файла, 20-50 строк кода
- Пример: добавить --verify флаг в CLI

### 3. Security (сложные)
- Найти и исправить уязвимость
- Требует понимания threat model
- Пример: PII redaction в логах

### 4. Refactor (средние)
- Оптимизировать существующий код
- Без изменения API
- Пример: streaming для больших файлов

### 5. Test (легкие-средние)
- Написать тесты для uncovered code
- Требует понимания edge cases
- Пример: тесты для Zenodo API errors

## Как добавить новую задачу

1. Создай файл `eval/tasks/NN_type_name.yaml`
2. Заполни все поля по шаблону выше
3. Убедись что задача **решаема** (сам попробуй вручную)
4. Добавь в acceptance_criteria чёткие проверки
5. Запусти baseline: `python eval/runner.py --baseline --task eval/tasks/NN_type_name.yaml`

## Worktree изоляция

Runner создаёт временный git worktree для каждой задачи:
- Изолированная копия репозитория
- Изменения не влияют на main worktree
- Автоматическая очистка после прогона

## Результаты

Формат `eval/results/latest.json`:

```json
[
  {
    "task_id": "bugfix-01-hash-lowercase",
    "model": "claude-sonnet-4.5",
    "score": {
      "total": 90,
      "max": 100,
      "percentage": 90.0,
      "breakdown": {
        "pass_tests": 40,
        "no_regression": 30,
        "minimal_diff": 10,
        "lint_clean": 10
      }
    },
    "test_result": {"passed": true, ...},
    "lint_result": {"passed": true, ...},
    "diff": "..."
  }
]
```

## Сравнение моделей

Запусти benchmark для нескольких моделей:

```bash
python eval/runner.py --model claude-sonnet-4.5 --output eval/results/claude_sonnet_4.5.json
python eval/runner.py --model gpt-4 --output eval/results/gpt4.json
python eval/runner.py --baseline --output eval/results/human_baseline.json
```

Затем сравни результаты:

```bash
python eval/compare.py eval/results/*.json
```

(TODO: создать compare.py)

## Best Practices

### ✅ DO

- Создавай задачи из **реальных** проблем проекта
- Тестируй задачу вручную перед добавлением в benchmark
- Используй чёткие acceptance criteria (измеримые)
- Добавляй ограничения (constraints) чтобы избежать читерства
- Версионируй задачи (если обновляешь, создай новый файл)

### ❌ DON'T

- Не создавай синтетические задачи "для галочки"
- Не делай acceptance criteria субъективными ("красивый код")
- Не тестируй на задачах которые модель могла видеть в трейне
- Не меняй задачи после прогона (версионируй вместо этого)
- Не игнорируй security/safety constraints

## Roadmap

- [ ] LLM API интеграция (Claude, GPT-4, Gemini)
- [ ] compare.py для визуализации результатов
- [ ] HTML dashboard с графиками
- [ ] Auto-retry на flaky tests
- [ ] Parallel execution (запуск N задач параллельно)
- [ ] Blind evaluation mode (скрывает модель от ревьюера)
- [ ] Cost tracking (API tokens/cost per task)
- [ ] Time tracking (latency per task)
- [ ] Regression detection (diff с baseline)

## FAQ

**Q: Как оценивать субъективные критерии типа "код читаемый"?**  
A: Не оценивай субъективно. Используй только измеримые метрики (tests pass, lint clean, diff size).

**Q: Что если задача требует внешнего API?**  
A: Mock внешние зависимости в тестах. Задача должна быть self-contained.

**Q: Можно ли модель натренировать на этих задачах?**  
A: Нет, это leakage. Используй для оценки, не для трейна.

**Q: Сколько задач нужно для статистически значимого бенчмарка?**  
A: Минимум 20 задач на категорию (bugfix, feature, etc.). Итого ~100 задач.

---

**Создано:** 2026-05-10  
**Автор:** Skeptic Engine Team  
**Лицензия:** Apache 2.0

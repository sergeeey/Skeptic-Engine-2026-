# Skeptic Engine — план переноса активов из других проектов

**Статус:** PARKED. Исполнять ТОЛЬКО после GeoScan blind test (2026-06-20).
**Создан:** 2026-06-05
**Каноническая копия:** E:\ (эта). D:\github-repos копия устарела (HEAD 2026-03-30), E:\ свежее (HEAD 2026-05-10).

---

## Зачем

Оценка проекта: 5.5/10. Узкое место: научная валидность 6/10 — **H23/H29 используют реальные метки** (Reproducibility Project + MaveDB/ClinVar), но **H24/H25 детектируют симулированную fabrication** (AUC 1.000 = theater по triggers.md).

Ключевой факт: дисциплина валидации на РЕАЛЬНЫХ данных уже построена в 4 других проектах. Golden-set harness (VeriFind) даст **real fraud ground truth** вместо симуляции.

**Reconciliation (2026-06-05):** parked plan wrote "вся валидация синтетическая" до проверки H23/H29. Фактически: H23 = real fraud labels (replicated vs failed), H29 = expert labels (benign vs pathogenic). Но H24/H25 = synthetic fabrication.

Парето: активы 1 и 2 дают 80% эффекта (валидность 6.0 → 8+, добавляя real fraud ground truth). Остальное — украшения.

---

## Phase 0 — Консолидация копий (30 мин, ОБЯЗАТЕЛЬНО первым)

Сейчас три расходящиеся копии Skeptic. Источник правды не определён.

1. Подтвердить: E:\ = каноническая (самый свежий коммит).
2. git push E:\ в origin.
3. Архивировать или удалить D:\github-repos\Skeptic-Engine-2026- (устарела).
4. Переименовать папку E:\ из "nobel premia Boiko - 2026" в нейтральное (skeptic-engine-manuscript). Имя противоречит собственному PROJECT_CANON ("not a Nobel-ready discovery claim").

Критерий приёмки: одна локальная копия, синхронная с origin, нейтральное имя.

---

## Phase 1 — Два актива, которые чинят валидность (приоритет)

### Актив 1: Golden-set harness из VeriFind  (сила: высшая)

- Источник: D:/github-repos/VeriFind-/GOLDEN_SET_BASELINE_REPORT.md плюс golden_set/financial_queries_v1.json
- Что брать: структуру harness — набор запросов с известным ответом (expected), полосы HIT (ошибка под 1 процент) / NEAR (под 10) / MISS (свыше 10), реальный провайдер вместо mock, честный отчёт о systematic bias.
- Куда в Skeptic: новый каталог eval/golden_set/ плюс раннер по образцу VeriFind. Заменяет синтетические H-эксперименты на набор реальных датасетов с известной разметкой (retracted статьи, известные fraud-кейсы, чистые контроли).
- Почему: прямо лечит AUC 1.000. Дает [VERIFIED-REAL] вместо [VERIFIED-SYNTHETIC].
- Критерий приёмки: минимум 10 реальных датасетов с источником-URL, отчёт показывает неидеальные числа (если снова 1.000 — данные синтетические, не приняты).

### Актив 2: ChernoffPy из MarkovChains  (сила: высшая)

- Источник: D:/github-repos/MarkovChains/chernoffpy/ (модули certified.py, analysis.py, functions.py)
- Что брать: сертифицированные статистические границы (Chernoff bounds). Дает доказуемую меру "насколько удивительно это распределение" вместо ad-hoc score.
- Куда в Skeptic: src/discovery_engine/skeptic/ как слой статистических границ под детекторами аномалий.
- Бонус: мост к Saule Anafinova (ее hook — Markov chains). Общий технический язык для контакта с COS-сетью.
- Критерий приёмки: хотя бы один детектор аномалий выдает сертифицированную границу, а не только бинарный флаг.

---

## Phase 2 — Полировка (опционально, только если Phase 1 закрыта)

### Актив 3: Дисциплина honest-validation из GeoScan
- Источник: D:/github-repos/Geosran-Gold-2026/LIMITATIONS.md
- Что брать: метод, не код. Baseline-first, spatial-null vs seed-bootstrap, GT-collision check, правило "красивый AUC = красный флаг". Урок ретракции 1.13 процента.
- Куда: docs/LIMITATIONS.md для Skeptic по образцу.

### Актив 4: Failure-matrix из CogniML
- Источник: D:/github-repos/CogniML-2026/failure-matrix.md плюс tests_contract/
- Что брать: явный перечень режимов отказа вместо "302 теста зелёные". Contract-тесты.

### Актив 5: Release-scaffold из ContextProof
- Источник: D:/github-repos/ContextProof-2026/PRODUCTION_READINESS_REPORT.md
- Что брать: упаковку и чеклист продакшна, если Skeptic поедет публично. Не строить заново.

### Актив 6: Null-results реестр из ARCHCODE
- Источник: D:/github-repos/ARCHCODE/
- Что брать: каталог null_results/ и baseline-first протокол. Честные отрицательные результаты как часть репо.

---

## Анти-scope (что НЕ делать)

- Не добавлять эксперименты H29 и далее. Уже 7 на диске, все синтетические. Больше синтетики не равно лучше.
- Не тащить все 6 активов сразу. Минимум жизнеспособного = активы 1 и 2.
- Не начинать до 20 июня. GeoScan имеет клиента и дату, Skeptic — нет.

## Порядок исполнения (после GeoScan)

Phase 0, затем Актив 1, затем Актив 2. Остановиться. Переоценить проект (ожидаемо валидность 3.0 в сторону 6, общая 5.5 в сторону 7). Только потом решать про Phase 2.

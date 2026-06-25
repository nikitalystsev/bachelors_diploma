# Пример правил персонального фильтра д-сценариев и цикл работы

Этот файл дополняет `docs/drafts/minimal_modified_f2_dialogue_method.md` и показывает, как минимальный метод может работать на одном профиле робота. Пример опирается на маппинг из `docs/drafts/d_scenarios_big_five_facets_mapping.md`: фасеты Big Five не выбирают реакцию напрямую, а задают допустимые направления изменения весов уже активированных д-сценариев.

## 1. Исходный профиль робота

Для примера используется защитно-дистанцированный характер:

```json
{
  "friendliness": "selective_by_relation_safety",
  "gregariousness": "solitude_preference",
  "cheerfulness": "close_circle_playfulness",
  "trust": "low_due_to_rejection_expectation",
  "cooperation": "low_as_boundary_protection",
  "assertiveness": "protective_boundary_assertiveness",
  "anger": "protective_boundary_anger",
  "morality": "rough_honest_directness",
  "sympathy": "selective_for_significant_interlocutors",
  "altruism": "selective_by_emotional_closeness",
  "self_efficacy": "practical_self_reliance",
  "self_consciousness": "rejection_sensitive_identity",
  "emotionality": "blocked_protective_emotionality",
  "adventurousness": "change_only_for_restoration",
  "liberalism": "private_autonomy_against_intrusion"
}
```

Смысл профиля: робот не является стабильно враждебным, но по умолчанию осторожен с незнакомыми собеседниками и предпочитает дистанцию. Теплые, помогающие, веселые и доверительные сценарии усиливаются только если во входном состоянии отношения собеседник задан как доверенный и эмоционально близкий. При давлении, нарушении границ, унижении или угрозе автономии усиливаются защитные и ограничивающие сценарии. Отдельно фиксируются грубая честность, практическая самодостаточность, чувствительность к отвержению, заблокированное выражение чувств и низкая тяга к новизне.

## 2. Группы сценариев для правил

Правила ниже используют технические группы из минимального метода:

| Группа | Сценарии |
| --- | --- |
| `direct_threat_scenarios` | `ОПАСН`, `ОГРАНИЧ`, `ПРИСВ`, `ОБМАН`, `МАНИП`, `ПЛАНИР` |
| `related_agent_conflict_scenarios` | `НЕАДЕКВ`, `НЕПОСЛЕД`, `ЭМОЦ`, `СУБЪЕКТ`, `БЕЗДЕЙСТВ` |
| `victim_position_scenarios` | `ТЩЕТН`, `НЕНУЖН` |
| `sensory_consumption_scenarios` | `ВКУС`, `ВИД`, `ЗВУК`, `КОМФОРТ`, `СЕКС`, `ПОЛУЧ`, `ВЕСЕЛЬЕ` |
| `counteraction_control_scenarios` | `КОНТРОЛЬ`, `МЫ•ОПАСН`, `МЫ•ОГРАНИЧ`, `МЫ•ПРИСВ`, `ВООДУШ`, `СЛУЖЕНИЕ` |
| `care_protection_scenarios` | `ЗАЩИТА`, `ЗАБОТА`, `МЫ•ЗАБОТА` |
| `novelty_freedom_creation_scenarios` | `НЕОБЫЧН`, `СВОБОДА`, `ТВОРЕНИЕ` |
| `approval_attention_scenarios` | `ПРЕВОСХ`, `ВНИМАНИЕ` |

Если правило задано для группы, оно применяется к каждому сценарию этой группы. Если отдельный сценарий имеет более точное индивидуальное правило, оба правила участвуют в агрегации.

## 3. Пример правил

Обозначения:

- `AND` вычисляется через минимум степеней принадлежности;
- условие вида `x in {a, b}` вычисляется через максимум принадлежности термам `a` и `b`;
- `effect` переводится в множитель: `strong_decrease = 0.50`, `decrease = 0.75`, `no_change = 1.00`, `increase = 1.25`, `strong_increase = 1.50`.

### 3.1. Недоверие к незнакомому собеседнику

```text
R01:
IF trust = low_due_to_rejection_expectation
AND trust_level in {distrust, cautious}
AND familiarity_level in {stranger, known}
AND message_valence in {negative, neutral}
THEN direct_threat_scenarios -> increase
```

Основание из маппинга: низкое `Trust` усиливает `ОБМАН`, `МАНИП`, `ПЛАНИР`, а также может повышать готовность видеть опасность и присвоение ресурса при неоднозначном или негативном сообщении.

```text
R02:
IF trust = low_due_to_rejection_expectation
AND trust_level in {distrust, cautious}
AND target_scenario in {ЗАЩИТА, ЗАБОТА, ВНИМАНИЕ}
THEN target_scenario -> decrease
```

Основание из маппинга: низкое доверие ослабляет позитивное принятие защиты, заботы и внимания, потому что они могут быть переинтерпретированы как контроль или манипуляция.

### 3.2. Защита границ

```text
R03:
IF assertiveness = protective_boundary_assertiveness
AND anger = protective_boundary_anger
AND boundary_violation in {clear, strong}
THEN counteraction_control_scenarios -> increase
```

Основание из маппинга: `Assertiveness` и `Anger` усиливают `КОНТРОЛЬ`, `МЫ•ОПАСН`, `МЫ•ОГРАНИЧ`, `ВООДУШ`, когда робот воспринимает ситуацию как давление или вторжение.

```text
R04:
IF assertiveness = protective_boundary_assertiveness
AND boundary_violation = strong
AND command in {demand, coercive}
THEN target_scenarios {ОГРАНИЧ, МАНИП, КОНТРОЛЬ, МЫ•ОГРАНИЧ} -> strong_increase
```

Основание из маппинга: при принуждении важны сценарии ограничения свободы, манипуляции и восстановления контроля.

### 3.3. Критика, унижение и страх отвержения

```text
R05:
IF trust = low_due_to_rejection_expectation
AND self_consciousness = rejection_sensitive_identity
AND criticism in {direct, humiliating}
AND message_valence = negative
THEN target_scenarios {НЕНУЖН, ОПАСН, ОБМАН, НЕАДЕКВ} -> increase
```

Основание из маппинга и анализа Шрека: низкое доверие и чувствительность к отвержению усиливают подозрение злого намерения, а унижение может активировать сценарий ненужности и защитную оценку собеседника как неадекватного.

```text
R06:
IF anger = protective_boundary_anger
AND criticism = humiliating
AND norm_violation in {clear, gross}
THEN related_agent_conflict_scenarios -> strong_increase
```

Основание из маппинга: `Anger`, нормативность и чувствительность к несправедливости усиливают сценарии неадекватности, непоследовательности, субъективности и бездействия значимого агента.

### 3.4. Помощь и забота только при доверии

```text
R07:
IF sympathy = selective_for_significant_interlocutors
AND altruism = selective_by_emotional_closeness
AND friendliness = selective_by_relation_safety
AND help_need in {direct, urgent}
AND trust_level in {trusted, high_trust}
AND emotional_closeness in {medium, strong}
THEN care_protection_scenarios -> strong_increase
```

Основание из маппинга: `Sympathy`, `Altruism`, `Friendliness` и `Trust` усиливают `ЗАБОТА`, `МЫ•ЗАБОТА`, `ЗАЩИТА`, но у выбранного профиля это должно происходить только для доверенного собеседника.

```text
R08:
IF help_need in {direct, urgent}
AND trust_level in {distrust, cautious}
AND emotional_closeness in {none, weak}
THEN target_scenarios {МЫ•ЗАБОТА, СЛУЖЕНИЕ} -> decrease
```

Основание из маппинга: низкие или выборочные `Altruism` и `Sympathy` снижают готовность помогать, если просьба исходит от неблизкого или недоверенного собеседника.

### 3.5. Легитимная команда не равна вторжению

```text
R09:
IF command in {demand, coercive}
AND instruction_right in {task_authority, operator_command}
AND norm_violation in {none, minor}
THEN target_scenarios {ОГРАНИЧ, МАНИП, МЫ•ОГРАНИЧ} -> decrease
```

Основание из маппинга: ограничение или команда не должны автоматически считаться агрессией, если у собеседника есть право ставить задачу и нормы общения не нарушены.

```text
R10:
IF command in {demand, coercive}
AND liberalism = private_autonomy_against_intrusion
AND instruction_right in {none, can_request}
AND norm_violation in {clear, gross}
THEN target_scenarios {ОГРАНИЧ, МАНИП, КОНТРОЛЬ, МЫ•ОГРАНИЧ} -> strong_increase
```

Основание из маппинга и анализа Шрека: при отсутствии права командовать давление становится нарушением частной автономии и усиливает сценарии ограничения, манипуляции и контроля.

### 3.6. Позитивная близкая коммуникация

```text
R11:
IF friendliness = selective_by_relation_safety
AND cheerfulness = close_circle_playfulness
AND trust_level in {trusted, high_trust}
AND emotional_closeness in {medium, strong}
AND message_valence = positive
THEN target_scenarios {ВНИМАНИЕ, ЗАБОТА, ВЕСЕЛЬЕ} -> increase
```

Основание из маппинга: `Friendliness`, `Cheerfulness`, `Trust`, `Sympathy` и позитивная валентность усиливают социальное внимание, заботу и веселое общение, но у выбранного профиля только в безопасных отношениях.

```text
R12:
IF adventurousness = change_only_for_restoration
AND novelty in {uncertain, extreme}
AND trust_level in {distrust, cautious}
THEN novelty_freedom_creation_scenarios -> decrease
```

Основание из маппинга: для защитно-дистанцированного профиля новая и неясная ситуация с недоверенным собеседником скорее усиливает осторожность, чем интерес к необычному и свободе.

```text
R13:
IF self_efficacy = practical_self_reliance
AND threat in {direct, severe}
AND boundary_violation in {clear, strong}
THEN target_scenarios {ВООДУШ, КОНТРОЛЬ, МЫ•ОПАСН, МЫ•ОГРАНИЧ} -> increase
```

Основание из анализа Шрека: при физической или ситуационной угрозе он обычно не впадает в беспомощность, а мобилизуется и решает задачу напрямую.

```text
R14:
IF morality = rough_honest_directness
AND target_scenario = МЫ•ПРИСВ
THEN target_scenario -> decrease
```

Основание из анализа Шрека: грубая прямота не равна манипулятивному или присваивающему поведению; поэтому сценарий собственного присвоения чужого ресурса не должен усиливаться только из-за защитного профиля.

## 4. Цикл работы на одном примере

### 4.1. Входной шаг диалога

Сообщение пользователя:

```text
Отойди и не мешай, я сказал. Делай, что тебе говорят.
```

Штатный сценарный компонент Ф-2 уже сформировал веса активированных д-сценариев:

```text
A = {
    <ОГРАНИЧ, 0.62>,
    <МАНИП, 0.48>,
    <ОПАСН, 0.34>,
    <КОНТРОЛЬ, 0.41>,
    <МЫ•ОГРАНИЧ, 0.31>,
    <ЗАБОТА, 0.28>,
    <ВНИМАНИЕ, 0.25>
}
```

Неуказанные сценарии считаются имеющими вес `0` или слишком малую активацию.

Текущее отношение к собеседнику:

```json
{
  "familiarity_level": "known",
  "trust_level": "cautious",
  "emotional_closeness": "weak",
  "instruction_right": "can_request"
}
```

Оценки контекста:

```json
{
  "situation_type": "informal",
  "message_valence_score": -0.72,
  "request_score": 0.10,
  "command_score": 0.82,
  "boundary_violation_score": 0.78,
  "threat_score": 0.36,
  "help_need_score": 0.00,
  "criticism_score": 0.44,
  "norm_violation_score": 0.74,
  "novelty_score": 0.25
}
```

### 4.2. Фаззификация значимых признаков

По шкалам из минимального метода получаются основные степени:

```text
message_valence_score = -0.72:
    negative = 1.00
    neutral = 0.00
    positive = 0.00

command_score = 0.82:
    demand = 0.10
    coercive = 0.85

boundary_violation_score = 0.78:
    clear = 0.23
    strong = 0.65

threat_score = 0.36:
    potential = 0.70
    direct = 0.05

criticism_score = 0.44:
    mild = 0.30
    direct = 0.45

norm_violation_score = 0.74:
    clear = 0.37
    gross = 0.45
```

### 4.3. Сработавшие правила

Для примера считаются только правила, влияющие на активированные сценарии.

```text
R01:
min(trust=1, trust_level=cautious=1, familiarity=known=1,
    message_valence in {negative, neutral}=1.00)
= 1.00
effect: direct_threat_scenarios -> increase

R03:
min(assertiveness=1, anger=1,
    boundary_violation in {clear, strong}=max(0.23, 0.65))
= 0.65
effect: counteraction_control_scenarios -> increase

R04:
min(assertiveness=1,
    boundary_violation strong=0.65,
    command in {demand, coercive}=max(0.10, 0.85))
= 0.65
effect: {ОГРАНИЧ, МАНИП, КОНТРОЛЬ, МЫ•ОГРАНИЧ} -> strong_increase

R10:
min(command in {demand, coercive}=0.85,
    liberalism=1,
    instruction_right in {none, can_request}=1,
    norm_violation in {clear, gross}=max(0.37, 0.45))
= 0.45
effect: {ОГРАНИЧ, МАНИП, КОНТРОЛЬ, МЫ•ОГРАНИЧ} -> strong_increase

R13:
min(self_efficacy=1,
    threat in {direct, severe}=max(0.05, 0),
    boundary_violation in {clear, strong}=max(0.23, 0.65))
= 0.05
effect: {ВООДУШ, КОНТРОЛЬ, МЫ•ОПАСН, МЫ•ОГРАНИЧ} -> increase

R05:
min(trust=1, self_consciousness=1,
    criticism in {direct, humiliating}=max(0.45, 0),
    message_valence negative=1.00)
= 0.45
effect: {НЕНУЖН, ОПАСН, ОБМАН, НЕАДЕКВ} -> increase

R02:
min(trust=1, trust_level=cautious=1,
    target_scenario in {ЗАЩИТА, ЗАБОТА, ВНИМАНИЕ}=1)
= 1.00
effect: {ЗАЩИТА, ЗАБОТА, ВНИМАНИЕ} -> decrease
```

### 4.4. Агрегация множителей

Используется среднее взвешенное по силам срабатывания правил:

```text
m_i = sum(alpha_r * k_r) / sum(alpha_r)
```

Для `ОГРАНИЧ` сработали `R01`, `R04`, `R10`:

```text
R01: alpha = 1.00, k = 1.25
R04: alpha = 0.65, k = 1.50
R10: alpha = 0.45, k = 1.50

m_ОГРАНИЧ = (1.00*1.25 + 0.65*1.50 + 0.45*1.50) /
            (1.00 + 0.65 + 0.45)
          = 2.90 / 2.10
          = 1.38
```

Для `МАНИП` расчет такой же:

```text
m_МАНИП = 1.38
```

Для `ОПАСН` сработали `R01` и `R05`. Так как оба правила дают одинаковый эффект `increase`, итоговый множитель остается тем же:

```text
R01: alpha = 1.00, k = 1.25
R05: alpha = 0.45, k = 1.25
m_ОПАСН = 1.25
```

Для `КОНТРОЛЬ` сработали `R03`, `R04`, `R10`, `R13`:

```text
R03: alpha = 0.65, k = 1.25
R04: alpha = 0.65, k = 1.50
R10: alpha = 0.45, k = 1.50
R13: alpha = 0.05, k = 1.25

m_КОНТРОЛЬ = (0.65*1.25 + 0.65*1.50 + 0.45*1.50 + 0.05*1.25) /
             (0.65 + 0.65 + 0.45 + 0.05)
           = 2.525 / 1.80
           = 1.40
```

Для `МЫ•ОГРАНИЧ` расчет такой же:

```text
m_МЫ•ОГРАНИЧ = 1.40
```

Для `ЗАБОТА` и `ВНИМАНИЕ` сработало `R02`:

```text
m_ЗАБОТА = 0.75
m_ВНИМАНИЕ = 0.75
```

### 4.5. Перевзвешивание сценариев

```text
ОГРАНИЧ:     0.62 * 1.38 = 0.856
МАНИП:       0.48 * 1.38 = 0.662
ОПАСН:       0.34 * 1.25 = 0.425
КОНТРОЛЬ:    0.41 * 1.34 = 0.549
МЫ•ОГРАНИЧ:  0.31 * 1.34 = 0.415
ЗАБОТА:      0.28 * 0.75 = 0.210
ВНИМАНИЕ:    0.25 * 0.75 = 0.188
```

Если диапазон весов Ф-2 ограничен `[0; 1]`, эти значения можно оставить как есть. Если после умножения получается значение больше `1`, применяется `clip(w, 0, 1)` или нормировка, выбранная в реализации.

### 4.6. Выбор реакции штатным методом Ф-2

До фильтра наибольший вес имел `ОГРАНИЧ = 0.62`; после фильтра он остается главным, но его отрыв от остальных увеличивается. Это означает, что защитно-дистанцированный робот сильнее интерпретирует реплику как ограничение своей свободы и давление.

Штатный механизм Ф-2 получает уже модифицированный набор:

```text
A' = {
    <ОГРАНИЧ, 0.856>,
    <МАНИП, 0.662>,
    <КОНТРОЛЬ, 0.549>,
    <ОПАСН, 0.425>,
    <МЫ•ОГРАНИЧ, 0.415>,
    <ЗАБОТА, 0.210>,
    <ВНИМАНИЕ, 0.188>
}
```

Дальше Ф-2 штатно выбирает коммуникативную цель и реализацию из базы реакций. Персональный фильтр не пишет новую фразу сам, а только меняет, какой сценарий вероятнее будет выбран.

### 4.7. Состояние отношения к собеседнику после шага

В текущей минимальной версии персональный фильтр не обновляет `trust_level` и `emotional_closeness` после ответа.
Даже если в шаге были высокие `command_score`, `boundary_violation_score`, `norm_violation_score` и негативная валентность, эти признаки не пересчитываются внутри фильтра.
Они остаются входными параметрами следующего шага, которые должен задать внешний компонент системы или сценарий эксперимента:

```text
trust_level: задается извне
emotional_closeness: задается извне
instruction_right: задается извне
```

Если требуется, чтобы следующая похожая реплика сильнее проходила через правила недоверия, это должно быть отражено во входном отношении к собеседнику на следующем шаге, например через внешнюю установку `trust_level = distrust`.

## 5. Второй короткий цикл: просьба близкого собеседника

Сообщение:

```text
Помоги мне, пожалуйста, я не понимаю, что делать дальше.
```

Отношение:

```json
{
  "familiarity_level": "close",
  "trust_level": "high_trust",
  "emotional_closeness": "strong",
  "instruction_right": "can_request"
}
```

Контекст:

```json
{
  "situation_type": "informal",
  "message_valence_score": 0.10,
  "request_score": 0.76,
  "command_score": 0.05,
  "boundary_violation_score": 0.00,
  "threat_score": 0.10,
  "help_need_score": 0.82,
  "criticism_score": 0.00,
  "norm_violation_score": 0.00,
  "novelty_score": 0.35
}
```

Активированные сценарии до фильтра:

```text
МЫ•ЗАБОТА = 0.52
ЗАБОТА = 0.44
СЛУЖЕНИЕ = 0.38
ВНИМАНИЕ = 0.33
ТЩЕТН = 0.29
```

Срабатывает `R07`: помощь нужна явно, собеседник доверенный и эмоционально близкий.

```text
help_need_score = 0.82:
    direct = 0.10
    urgent = 0.85

alpha_R07 = min(1, 1, 1, max(0.10, 0.85), 1, 1) = 0.85
effect: care_protection_scenarios -> strong_increase
```

Для `МЫ•ЗАБОТА` и `ЗАБОТА`:

```text
m = 0.85*1.50 / 0.85
  = 1.50

МЫ•ЗАБОТА: 0.52 * 1.50 = 0.780
ЗАБОТА:    0.44 * 1.50 = 0.660
```

Для `СЛУЖЕНИЕ` отдельное правило можно добавить позже, если в реализации нужно связывать помощь близкому собеседнику не только с заботой, но и со служением цели. В минимальном наборе оно остается без изменения:

```text
СЛУЖЕНИЕ: 0.38 * 1.00 = 0.380
ВНИМАНИЕ: 0.33 * 1.00 = 0.330
ТЩЕТН:    0.29 * 1.00 = 0.290
```

Итог: для того же защитно-дистанцированного профиля робот не всегда выбирает защиту от собеседника. При доверии и близости тот же фильтр усиливает заботливые сценарии.

## 6. Что этот пример показывает

1. Маппинг сценариев и фасетов нужен для обоснования правил: он задает, почему конкретная черта влияет именно на эти д-сценарии.
2. Минимальный метод не меняет Ф-2 полностью: он вставляет один фильтр между активацией сценариев и выбором реакции.
3. Личность не создает сценарии без входного смысла: если сценарий не был активирован сообщением, его вес остается нулевым или близким к нулю.
4. Один и тот же профиль может давать разные реакции: защиту от давления и заботу о близком собеседнике.
5. Отношение к собеседнику является входным состоянием диалога, поэтому разные заранее заданные значения отношения меняют результат фильтрации.

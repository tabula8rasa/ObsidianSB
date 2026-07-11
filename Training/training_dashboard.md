
# Последние тренировки

```dataviewjs
const pages = dv.pages('"Training/Logs"').array();

const METRICS = [
    "energy",
    "focus",
    "target_muscle_feel",
    "technique",
    "breathing_control",
    "plan_completed",
    "progression",
    "recovery_feeling",
    "pain_free",
    "mood_after",
];

function getMetricValue(page, metric) {
    const value = page[metric];

    if (value === undefined || value === null || value === "") {
        return null;
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return null;
    }

    return numberValue;
}

function isCompletedTraining(page) {
    return METRICS.every(metric => getMetricValue(page, metric) !== null);
}

function totalScore(page) {
    return METRICS.reduce((sum, metric) => {
        return sum + getMetricValue(page, metric);
    }, 0);
}

function gradeFromScore(score) {
    if (score >= 18) return "Отлично";
    if (score >= 14) return "Хорошо";
    if (score >= 10) return "Нормально";
    if (score >= 6) return "Плохо";
    return "Провал";
}

function normalizeDate(value) {
    if (value === undefined || value === null) {
        return "";
    }

    return String(value);
}

const completedPages = pages
    .filter(isCompletedTraining)
    .sort((a, b) => normalizeDate(b.date).localeCompare(normalizeDate(a.date)))
    .slice(0, 20);

dv.table(
    ["Дата", "Тренировка", "Тип", "Балл", "Оценка", "Вес", "Сон"],
    completedPages.map(page => {
        const score = totalScore(page);

        return [
            page.date ?? "",
            page.file.link,
            page.training_type ?? "",
            score,
            gradeFromScore(score),
            page.body_weight ?? "",
            page.sleep_hours ?? "",
        ];
    })
);
```

---

# Статистика по оценкам

```dataviewjs
const pages = dv.pages('"Training/Logs"').array();

const METRICS = [
    "energy",
    "focus",
    "target_muscle_feel",
    "technique",
    "breathing_control",
    "plan_completed",
    "progression",
    "recovery_feeling",
    "pain_free",
    "mood_after",
];

function getMetricValue(page, metric) {
    const value = page[metric];

    if (value === undefined || value === null || value === "") {
        return null;
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return null;
    }

    return numberValue;
}

function isCompletedTraining(page) {
    return METRICS.every(metric => getMetricValue(page, metric) !== null);
}

function totalScore(page) {
    return METRICS.reduce((sum, metric) => {
        return sum + getMetricValue(page, metric);
    }, 0);
}

function gradeFromScore(score) {
    if (score >= 18) return "Отлично";
    if (score >= 14) return "Хорошо";
    if (score >= 10) return "Нормально";
    if (score >= 6) return "Плохо";
    return "Провал";
}

const completedPages = pages.filter(isCompletedTraining);

const stats = {
    "Отлично": 0,
    "Хорошо": 0,
    "Нормально": 0,
    "Плохо": 0,
    "Провал": 0,
};

for (const page of completedPages) {
    const score = totalScore(page);
    const grade = gradeFromScore(score);

    stats[grade] += 1;
}

const max = Math.max(...Object.values(stats), 1);

dv.table(
    ["Оценка", "Кол-во", "График"],
    Object.entries(stats).map(([grade, count]) => {
        const width = Math.round((count / max) * 30);

        return [
            grade,
            count,
            count === 0 ? "" : "█".repeat(width),
        ];
    })
);
```

---

# Средние метрики

```dataviewjs
const pages = dv.pages('"Training/Logs"').array();

const METRICS = [
    "energy",
    "focus",
    "target_muscle_feel",
    "technique",
    "breathing_control",
    "plan_completed",
    "progression",
    "recovery_feeling",
    "pain_free",
    "mood_after",
];

function getMetricValue(page, metric) {
    const value = page[metric];

    if (value === undefined || value === null || value === "") {
        return null;
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return null;
    }

    return numberValue;
}

function isCompletedTraining(page) {
    return METRICS.every(metric => getMetricValue(page, metric) !== null);
}

function totalScore(page) {
    return METRICS.reduce((sum, metric) => {
        return sum + getMetricValue(page, metric);
    }, 0);
}

function avg(values) {
    const filtered = values
        .map(value => Number(value))
        .filter(value => !Number.isNaN(value));

    if (filtered.length === 0) {
        return "-";
    }

    return (filtered.reduce((a, b) => a + b, 0) / filtered.length).toFixed(2);
}

function avgField(pages, field) {
    return avg(pages.map(page => page[field]));
}

const completedPages = pages.filter(isCompletedTraining);

dv.table(
    ["Метрика", "Среднее"],
    [
        ["Итоговый балл", avg(completedPages.map(page => totalScore(page)))],
        ["Энергия", avgField(completedPages, "energy")],
        ["Фокус", avgField(completedPages, "focus")],
        ["Чувство целевой мышцы", avgField(completedPages, "target_muscle_feel")],
        ["Техника", avgField(completedPages, "technique")],
        ["Контроль дыхания", avgField(completedPages, "breathing_control")],
        ["Выполнение плана", avgField(completedPages, "plan_completed")],
        ["Прогрессия", avgField(completedPages, "progression")],
        ["Восстановление", avgField(completedPages, "recovery_feeling")],
        ["Без боли", avgField(completedPages, "pain_free")],
        ["Настроение после", avgField(completedPages, "mood_after")],
        ["Сон", avgField(completedPages, "sleep_hours")],
    ]
);
```

---

# Тренировки по типам

```dataviewjs
const pages = dv.pages('"Training/Logs"')
    .where(page => page.training_type !== undefined && page.training_type !== null && page.training_type !== "")
    .array();

const stats = {};

for (const page of pages) {
    const type = String(page.training_type);
    stats[type] = (stats[type] ?? 0) + 1;
}

const max = Math.max(...Object.values(stats), 1);

dv.table(
    ["Тип", "Кол-во", "График"],
    Object.entries(stats).map(([type, count]) => [
        type,
        count,
        "█".repeat(Math.round((count / max) * 30)),
    ])
);
```

---

# Прогресс итогового балла

```dataviewjs
const pages = dv.pages('"Training/Logs"').array();

const METRICS = [
    "energy",
    "focus",
    "target_muscle_feel",
    "technique",
    "breathing_control",
    "plan_completed",
    "progression",
    "recovery_feeling",
    "pain_free",
    "mood_after",
];

function getMetricValue(page, metric) {
    const value = page[metric];

    if (value === undefined || value === null || value === "") {
        return null;
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return null;
    }

    return numberValue;
}

function isCompletedTraining(page) {
    return METRICS.every(metric => getMetricValue(page, metric) !== null);
}

function totalScore(page) {
    return METRICS.reduce((sum, metric) => {
        return sum + getMetricValue(page, metric);
    }, 0);
}

function gradeFromScore(score) {
    if (score >= 18) return "Отлично";
    if (score >= 14) return "Хорошо";
    if (score >= 10) return "Нормально";
    if (score >= 6) return "Плохо";
    return "Провал";
}

function normalizeDate(value) {
    if (value === undefined || value === null) {
        return "";
    }

    return String(value);
}

const completedPages = pages
    .filter(page => page.date && isCompletedTraining(page))
    .sort((a, b) => normalizeDate(a.date).localeCompare(normalizeDate(b.date)));

const rows = completedPages.map(page => {
    const score = totalScore(page);
    const bar = "█".repeat(Math.max(0, Math.round(score)));

    return [
        page.date,
        page.file.link,
        score,
        gradeFromScore(score),
        bar,
    ];
});

dv.table(["Дата", "Тренировка", "Балл", "Оценка", "График"], rows);
```

---

# Прогресс веса

```dataviewjs
const pages = dv.pages('"Training/Logs"')
    .where(page => page.date && page.body_weight !== undefined && page.body_weight !== null && page.body_weight !== "")
    .array();

function normalizeDate(value) {
    if (value === undefined || value === null) {
        return "";
    }

    return String(value);
}

const rows = pages
    .sort((a, b) => normalizeDate(a.date).localeCompare(normalizeDate(b.date)))
    .map(page => [
        page.date,
        page.file.link,
        Number(page.body_weight),
    ]);

dv.table(["Дата", "Тренировка", "Вес"], rows);
```

---

# Кардио-метрики

```dataviewjs
const pages = dv.pages('"Training/Logs"')
    .where(page => page.training_type === "cardio")
    .array();

const METRICS = [
    "energy",
    "focus",
    "target_muscle_feel",
    "technique",
    "breathing_control",
    "plan_completed",
    "progression",
    "recovery_feeling",
    "pain_free",
    "mood_after",
];

function getMetricValue(page, metric) {
    const value = page[metric];

    if (value === undefined || value === null || value === "") {
        return null;
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return null;
    }

    return numberValue;
}

function isCompletedTraining(page) {
    return METRICS.every(metric => getMetricValue(page, metric) !== null);
}

function totalScore(page) {
    return METRICS.reduce((sum, metric) => {
        return sum + getMetricValue(page, metric);
    }, 0);
}

function gradeFromScore(score) {
    if (score >= 18) return "Отлично";
    if (score >= 14) return "Хорошо";
    if (score >= 10) return "Нормально";
    if (score >= 6) return "Плохо";
    return "Провал";
}

function normalizeDate(value) {
    if (value === undefined || value === null) {
        return "";
    }

    return String(value);
}

const rows = pages
    .sort((a, b) => normalizeDate(b.date).localeCompare(normalizeDate(a.date)))
    .slice(0, 20)
    .map(page => {
        const completed = isCompletedTraining(page);
        const score = completed ? totalScore(page) : "";

        return [
            page.date ?? "",
            page.file.link,
            page.sport ?? "",
            page.distance_km ?? "",
            page.duration_min ?? "",
            page.avg_pace ?? "",
            page.avg_hr ?? "",
            page.max_hr ?? "",
            score,
            completed ? gradeFromScore(score) : "",
        ];
    });

dv.table(
    ["Дата", "Тренировка", "Спорт", "Дистанция", "Время", "Темп", "Пульс ср.", "Пульс макс.", "Балл", "Оценка"],
    rows
);
```

---

# Зал-метрики

```dataviewjs
const pages = dv.pages('"Training/Logs"')
    .where(page => page.training_type === "gym")
    .array();

const METRICS = [
    "energy",
    "focus",
    "target_muscle_feel",
    "technique",
    "breathing_control",
    "plan_completed",
    "progression",
    "recovery_feeling",
    "pain_free",
    "mood_after",
];

function getMetricValue(page, metric) {
    const value = page[metric];

    if (value === undefined || value === null || value === "") {
        return null;
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return null;
    }

    return numberValue;
}

function isCompletedTraining(page) {
    return METRICS.every(metric => getMetricValue(page, metric) !== null);
}

function totalScore(page) {
    return METRICS.reduce((sum, metric) => {
        return sum + getMetricValue(page, metric);
    }, 0);
}

function gradeFromScore(score) {
    if (score >= 18) return "Отлично";
    if (score >= 14) return "Хорошо";
    if (score >= 10) return "Нормально";
    if (score >= 6) return "Плохо";
    return "Провал";
}

function normalizeDate(value) {
    if (value === undefined || value === null) {
        return "";
    }

    return String(value);
}

const rows = pages
    .sort((a, b) => normalizeDate(b.date).localeCompare(normalizeDate(a.date)))
    .slice(0, 20)
    .map(page => {
        const completed = isCompletedTraining(page);
        const score = completed ? totalScore(page) : "";

        return [
            page.date ?? "",
            page.file.link,
            score,
            completed ? gradeFromScore(score) : "",
            page.target_muscle_feel ?? "",
            page.technique ?? "",
            page.progression ?? "",
            page.pain_free ?? "",
        ];
    });

dv.table(
    ["Дата", "Тренировка", "Балл", "Оценка", "Целевая мышца", "Техника", "Прогрессия", "Без боли"],
    rows
);
```

---

# Незаполненные тренировки

```dataviewjs
const pages = dv.pages('"Training/Logs"').array();

const METRICS = [
    "energy",
    "focus",
    "target_muscle_feel",
    "technique",
    "breathing_control",
    "plan_completed",
    "progression",
    "recovery_feeling",
    "pain_free",
    "mood_after",
];

function getMetricValue(page, metric) {
    const value = page[metric];

    if (value === undefined || value === null || value === "") {
        return null;
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
        return null;
    }

    return numberValue;
}

function missingMetrics(page) {
    return METRICS.filter(metric => getMetricValue(page, metric) === null);
}

function normalizeDate(value) {
    if (value === undefined || value === null) {
        return "";
    }

    return String(value);
}

const incompletePages = pages
    .filter(page => missingMetrics(page).length > 0)
    .sort((a, b) => normalizeDate(b.date).localeCompare(normalizeDate(a.date)))
    .slice(0, 20);

dv.table(
    ["Дата", "Тренировка", "Не заполнено"],
    incompletePages.map(page => [
        page.date ?? "",
        page.file.link,
        missingMetrics(page).join(", "),
    ])
);
```

---

# Как заполнять тренировку

В каждой заметке тренировки заполняй только поля из шаблона.

## Обязательные поля для расчёта оценки

```yaml
energy: 2
focus: 2
target_muscle_feel: 1
technique: 2
breathing_control: 1
plan_completed: 2
progression: 1
recovery_feeling: 2
pain_free: 2
mood_after: 2
```

## Шкала каждого пункта

| Балл | Значение |
|---:|---|
| `0` | плохо / не выполнено |
| `1` | средне / частично |
| `2` | хорошо / выполнено |

## Итоговая оценка считается автоматически

| Сумма | Оценка |
|---:|---|
| `18–20` | Отлично |
| `14–17` | Хорошо |
| `10–13` | Нормально |
| `6–9` | Плохо |
| `0–5` | Провал |

## Для зала

```yaml
training_type: gym
body_weight: 74.5
sleep_hours: 8
```

## Для кардио

```yaml
training_type: cardio
sport: run
distance_km: 5.2
duration_min: 32
avg_pace: "6:10"
avg_hr: 155
max_hr: 178
```

## Для отдыха

```yaml
training_type: rest
body_weight: 74.5
sleep_hours: 8
```
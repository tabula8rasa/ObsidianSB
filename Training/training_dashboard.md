---
title: Дашборд тренировок
tags:
  - training
  - dashboard
---

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

const completedPages = pages
    .filter(isCompletedTraining)
    .sort((a, b) => {
        const dateA = String(a.date ?? "");
        const dateB = String(b.date ?? "");
        return dateB.localeCompare(dateA);
    })
    .slice(0, 20);

dv.table(
    ["Дата", "Тренировка", "Тип", "Фокус", "Балл", "Оценка", "Вес", "Сон"],
    completedPages.map(page => {
        const score = totalScore(page);

        return [
            page.date,
            page.file.link,
            page.training_type ?? "",
            page.training_focus ?? "",
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
            "█".repeat(width),
        ];
    })
);
```

---

# Средние метрики

```dataviewjs
const pages = dv.pages('"Training/Logs"')
    .where(p => p.total_score !== undefined)
    .array();

function avg(field) {
    const values = pages
        .map(p => Number(p[field]))
        .filter(v => !Number.isNaN(v));

    if (values.length === 0) return "-";

    return (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2);
}

dv.table(
    ["Метрика", "Среднее"],
    [
        ["Итоговый балл", avg("total_score")],
        ["Энергия", avg("energy")],
        ["Фокус", avg("focus")],
        ["Чувство целевой мышцы", avg("target_muscle_feel")],
        ["Техника", avg("technique")],
        ["Контроль дыхания", avg("breathing_control")],
        ["Выполнение плана", avg("plan_completed")],
        ["Прогрессия", avg("progression")],
        ["Восстановление", avg("recovery_feeling")],
        ["Без боли", avg("pain_free")],
        ["Настроение после", avg("mood_after")],
        ["Сон", avg("sleep_hours")],
        ["Вес", avg("body_weight")],
    ]
);
```

---

# Тренировки по типам

```dataviewjs
const pages = dv.pages('"Training/Logs"').array();

const stats = {};

for (const page of pages) {
    const type = page.training_type ?? "unknown";
    stats[type] = (stats[type] ?? 0) + 1;
}

const max = Math.max(...Object.values(stats), 1);

dv.table(
    ["Тип", "Кол-во", "График"],
    Object.entries(stats).map(([type, count]) => [
        type,
        count,
        "█".repeat(Math.round((count / max) * 30))
    ])
);
```

---

# Прогресс итогового балла

```dataviewjs
const pages = dv.pages('"Training/Logs"')
    .where(p => p.date && p.total_score !== undefined)
    .sort(p => p.date, "asc")
    .array();

const rows = pages.map(p => {
    const score = Number(p.total_score);
    const bar = "█".repeat(Math.max(0, Math.round(score)));
    return [p.date, p.file.link, score, bar];
});

dv.table(["Дата", "Тренировка", "Балл", "График"], rows);
```

---

# Кардио-метрики

```dataview
TABLE
  date as "Дата",
  sport as "Спорт",
  training_focus as "Фокус",
  distance_km as "Дистанция",
  duration_min as "Время",
  avg_pace as "Средний темп",
  avg_hr as "Средний пульс",
  max_hr as "Макс. пульс",
  total_score as "Балл"
FROM "Training/Logs"
WHERE training_type = "cardio"
SORT date DESC
LIMIT 20
```

---

# Зал-метрики

```dataview
TABLE
  date as "Дата",
  training_focus as "Фокус",
  total_score as "Балл",
  target_muscle_feel as "Целевая мышца",
  technique as "Техника",
  progression as "Прогрессия",
  pain_free as "Без боли"
FROM "Training/Logs"
WHERE training_type = "gym"
SORT date DESC
LIMIT 20
```

---

# Как заполнять, чтобы дашборд работал

В каждой заметке тренировки должны быть поля:

```yaml
date: 2026-07-11
training_type: gym
body_weight: 74.5
sleep_hours: 8
energy: 2
focus: 2
target_muscle_feel: 2
technique: 2
breathing_control: 1
plan_completed: 2
progression: 2
recovery_feeling: 2
pain_free: 2
mood_after: 1
```

Для кардио дополнительно:

```yaml
sport: run
distance_km: 5.2
duration_min: 32
avg_pace: "6:10"
avg_hr: 155
max_hr: 178
```

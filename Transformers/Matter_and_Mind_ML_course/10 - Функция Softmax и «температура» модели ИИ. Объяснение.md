---
title: "Функция Softmax и «температура» модели ИИ. Объяснение"
course: "Математические основы машинного обучения — Matter and Mind"
lesson: 10
youtube: "https://www.youtube.com/watch?v=Sm04Fub2f6o"
tags:
  - машинное-обучение
  - softmax
  - temperature
---
## Главная идея

Для $\large K$ классов модель выдаёт logits:

$$\large 
z_1,\dots,z_K
$$

Softmax превращает их в вероятности:

$$\large 
\boxed{
p_i
=
\frac{e^{z_i}}{\sum_j e^{z_j}}
}
$$

Получается:

$$\large 
p_i\ge0
$$

и:

$$\large 
\sum_i p_i=1
$$

## Пример

Если:

$$\large 
z=[2,1,0]
$$

то:

$$\large 
e^z\approx[7.39,2.72,1]
$$

После нормализации:

$$\large 
p\approx[0.665,0.245,0.090]
$$

## Почему «soft max»

Hardmax оставил бы только номер победившего класса.

Softmax сохраняет распределение уверенности по всем классам.

## Инвариантность к сдвигу

$$\large 
softmax(z_i+c)=softmax(z_i)
$$

Поэтому для численной стабильности вычитают максимальный logit:

$$\large 
z'_i=z_i-\max_jz_j
$$

## Температура

$$\large 
\boxed{
p_i
=
\frac{e^{z_i/T}}{\sum_je^{z_j/T}}
}
$$

### $\large T<1$

Распределение острее, лидер становится ещё вероятнее.

### $\large T>1$

Распределение площе, вероятности становятся ближе друг к другу.

### Пределы

$$\large 
T\to0
$$

приближает hard argmax.

$$\large 
T\to\infty
$$

приближает равномерное распределение.

## В LLM

Языковая модель выдаёт logits всех возможных следующих токенов.

Softmax превращает их в:

$$\large 
p(token_{t+1}|context)
$$

Температура меняет форму этого распределения перед sampling.

Она не добавляет модели знания — только меняет степень концентрации вероятностей.

## Softmax + cross-entropy

Если правильный класс $\large k$:

$$\large 
L=-\log p_k
$$

Для этой связки:

$$\large 
\boxed{
\frac{\partial L}{\partial z_i}=p_i-y_i
}
$$

Очень удобный gradient.

## Связь с attention

В self-attention Softmax превращает similarity scores в веса:

$$\large 
Attention(Q,K,V)
=
softmax
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)V
$$

→ [[13 - Механизм внимания в LLM. Self-Attention]]

## Что запомнить

$$\large 
\boxed{
softmax(z_i)=\frac{e^{z_i}}{\sum_je^{z_j}}
}
$$

Softmax превращает logits в распределение вероятностей, а temperature регулирует его остроту.

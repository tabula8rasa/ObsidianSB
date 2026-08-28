---
title: "Механизм внимания в LLM. Self-Attention"
course: "Математические основы машинного обучения — Matter and Mind"
lesson: 13
youtube: "https://www.youtube.com/watch?v=qMAHKHBU4WI"
tags:
  - машинное-обучение
  - attention
  - self-attention
  - transformer
---

# Механизм внимания в LLM. Self-Attention

> Видео: https://www.youtube.com/watch?v=qMAHKHBU4WI

> Формат: смысловой учебный конспект, а не дословная стенограмма.
## Главная идея

Token embedding сам по себе не знает контекст.

Self-Attention позволяет каждому токену посмотреть на остальные токены и собрать из них релевантную информацию.

## Вход

Пусть:

\[
X\in\mathbb R^{n\times d_{model}}
\]

где:

- \(n\) — число токенов;
- \(d_{model}\) — размер vector каждого токена.

## Query, Key, Value

Из \(X\) строятся:

\[
Q=XW_Q
\]

\[
K=XW_K
\]

\[
V=XW_V
\]

Интуитивно:

```text
Query = что токен ищет
Key   = как токен себя описывает
Value = какую информацию он передаёт
```

## Оценка связи

Для token \(i\) и token \(j\):

\[
score_{ij}=q_i\cdot k_j
\]

Для всех сразу:

\[
S=QK^T
\]

Размер матрицы:

\[
n\times n
\]

Каждый token сравнивается с каждым.

## Масштабирование

Используется:

\[
\frac{QK^T}{\sqrt{d_k}}
\]

При большой размерности скалярные произведения могут быть слишком большими и загонять Softmax в насыщение.

Деление на \(\sqrt{d_k}\) стабилизирует значения.

## Softmax

\[
A=
softmax
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)
\]

Каждая строка \(A\) — веса внимания одного токена ко всем остальным.

## Итоговый context vector

\[
\boxed{
Attention(Q,K,V)
=
softmax
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)V
}
\]

Получается взвешенная сумма Value-векторов.

```text
Query × Keys
   ↓
scores
   ↓ softmax
weights
   ↓ × Values
contextual representation
```

## Почему это даёт контекст

Слово `bank` в:

```text
river bank
```

может сильнее обратить внимание на `river`.

А в:

```text
bank account
```

— на `account`.

После attention representation одного и того же token меняется в зависимости от окружения.

## Multi-Head Attention

Одна голова учит один способ взаимодействия.

Несколько голов:

\[
head_h=Attention(Q_h,K_h,V_h)
\]

\[
MultiHead
=
Concat(head_1,\dots,head_H)W_O
\]

Разные heads могут специализироваться на разных отношениях:

- синтаксис;
- дальние зависимости;
- семантика;
- кореференция.

## Masked attention

При генерации токен на позиции \(t\) не должен видеть будущее.

Поэтому запрещённым позициям перед Softmax дают:

\[
-\infty
\]

После Softmax их weight становится 0.

## Cross-attention

Self-attention:

```text
Q, K, V из одной последовательности
```

Cross-attention:

```text
Q из одной последовательности
K,V из другой
```

Это используется в классическом encoder-decoder Transformer.

## Сложность

Матрица \(QK^T\) имеет размер \(n\times n\), поэтому стандартный attention имеет квадратичную сложность по длине последовательности:

\[
O(n^2)
\]

## Связь с предыдущими темами

```text
Embeddings
 ↓
Linear projections Q,K,V
 ↓
Dot products
 ↓
Scaling
 ↓
Softmax
 ↓
Weighted sum
```

→ [[14 - Архитектура Transformer. Объяснение]]

## Что запомнить

\[
\boxed{
Attention(Q,K,V)
=
softmax
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)V
}
\]

Q — что ищем.  
K — с чем сравниваем.  
V — что переносим.

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
## Главная идея

Token embedding сам по себе не знает контекст.

Self-Attention позволяет каждому токену посмотреть на остальные токены и собрать из них релевантную информацию.

## Вход

Пусть:

$$\large 
X\in\mathbb R^{n\times d_{model}}
$$

где:

- $\large n$ — число токенов;
- $\large d_{model}$ — размер vector каждого токена.

## Query, Key, Value

Из $\large X$ строятся:

$$\large 
Q=XW_Q
$$

$$\large 
K=XW_K
$$

$$\large 
V=XW_V
$$

Интуитивно:

```text
Query = что токен ищет
Key   = как токен себя описывает
Value = какую информацию он передаёт
```

## Оценка связи

Для token $\large i$ и token $\large j$:

$$\large 
score_{ij}=q_i\cdot k_j
$$

Для всех сразу:

$$\large 
S=QK^T
$$

Размер матрицы:

$$\large 
n\times n
$$

Каждый token сравнивается с каждым.

## Масштабирование

Используется:

$$\large 
\frac{QK^T}{\sqrt{d_k}}
$$

При большой размерности скалярные произведения могут быть слишком большими и загонять Softmax в насыщение.

Деление на $\large \sqrt{d_k}$ стабилизирует значения.

## Softmax

$$\large 
A=
softmax
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)
$$

Каждая строка $\large A$ — веса внимания одного токена ко всем остальным.

## Итоговый context vector

$$\large 
\boxed{
Attention(Q,K,V)
=
softmax
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)V
}
$$

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

$$\large 
head_h=Attention(Q_h,K_h,V_h)
$$

$$\large 
MultiHead
=
Concat(head_1,\dots,head_H)W_O
$$

Разные heads могут специализироваться на разных отношениях:

- синтаксис;
- дальние зависимости;
- семантика;
- кореференция.

## Masked attention

При генерации токен на позиции $\large t$ не должен видеть будущее.

Поэтому запрещённым позициям перед Softmax дают:

$$\large 
-\infty
$$

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

Матрица $\large QK^T$ имеет размер $\large n\times n$, поэтому стандартный attention имеет квадратичную сложность по длине последовательности:

$$\large 
O(n^2)
$$

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

$$\large 
\boxed{
Attention(Q,K,V)
=
softmax
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)V
}
$$

Q — что ищем.  
K — с чем сравниваем.  
V — что переносим.

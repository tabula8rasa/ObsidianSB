Node.js = один процесс ОС

Внутри него:

1. Main OS thread
   - V8
   - твой JS
   - async functions
   - callbacks
   - Promise/microtasks
   - event loop

2. libuv machinery
   - управление async I/O
   - интеграция с механизмами ОС

3. libuv thread pool
   - по умолчанию 4 worker thread
   - используется конкретными native API
   - твой JS туда сам по себе не уходит

4. дополнительные потоки V8/Node
   - служебные внутренние задачи

5. worker_threads
   - отдельные потоки для реального параллельного JS
   - создаются явно
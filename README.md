# Runio

Bot de Telegram de RPG de progresión. Creas un personaje, bajas a la mazmorra, combates por
turnos pulsando botones, subes de nivel, consigues objetos con rarezas y compites en un
ranking. La energía limita cuántas veces puedes jugar al día.

Todo es lógica determinista y balanceada a mano: no hay llamadas a ningún modelo de lenguaje.

## Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # y pega tu token
python -m bot
```

En Linux y macOS, `./run.sh` hace los cuatro pasos de una vez.

El token se saca hablando con [@BotFather](https://t.me/BotFather) → `/newbot`. El fichero
`.env` no se sube al repositorio.

| Variable | Para qué sirve |
|---|---|
| `BOT_TOKEN` | El token de BotFather. Obligatorio |
| `DB_PATH` | Fichero SQLite. Por defecto `./rpg.db` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`… Por defecto `INFO` |
| `ADMIN_IDS` | Lista de identificadores separados por comas. Opcional |

## Comandos

| Comando | Qué hace |
|---|---|
| `/start` | Crea el personaje y muestra el teclado principal |
| `/perfil` | Ficha completa: nivel, vida, energía, estadísticas, equipo, oro y récord |
| `/mazmorra` | Gasta 1 de energía y empieza un combate |
| `/equipo` | Mochila paginada con botones para equipar |
| `/tienda` | Compra pociones y vende lo que no llevas puesto |
| `/ranking` | Top 10 por nivel y XP, más tu puesto |
| `/diario` | Recompensa cada 20 h: oro, pociones y energía llena |
| `/ayuda` | Explicación breve de las mecánicas |

## Cómo está montado

```
bot/
├── __main__.py     arranque: conexión, migraciones, polling
├── config.py       Settings validados con pydantic-settings
├── db.py           conexión única (WAL), migraciones y transacciones
├── models.py       dataclasses del dominio
├── texts.py        TODOS los strings visibles para el jugador
├── keyboards.py    constructores de teclados
├── callbacks.py    CallbackData tipado
├── middlewares.py  throttling, carga del jugador y captura de errores
├── game/           lógica pura: sin I/O, sin base de datos, sin aiogram
├── repo/           acceso a datos, una función por operación
└── handlers/       un router por comando
```

Dos reglas sostienen el diseño:

- **`bot/game/` es puro.** No importa `aiogram`, ni `aiosqlite`, ni `bot/repo/`. El azar entra
  siempre como parámetro `rng: random.Random`, nunca se llama a `random.foo()` directamente.
  Por eso el juego entero se puede probar sin bot y sin base de datos.
- **Un combate por jugador**, impuesto por un `UNIQUE` en `fights.user_id`, no por un `if`.
  Los turnos se escriben con una comparación-e-intercambio sobre la columna `turn`, así el
  doble toque no duplica el daño ni cobra dos veces la recompensa.

La energía y la vida no se regeneran con tareas programadas: se recalculan al leerlas a partir
de la marca de tiempo guardada, consumiendo solo los ciclos completos y arrastrando el resto.

## Desarrollo

```bash
pytest            # tests de la lógica pura y del acceso a datos
ruff check .      # lint
ruff format .     # formato
```

Los tests cubren `bot/game/` (progresión, regeneración, combate y botín) y `bot/repo/` sobre
una base de datos temporal. Incluyen comprobaciones de balanceo: la distribución de rarezas
sobre 100.000 tiradas y la tasa de victoria de un nivel 5 sobre 1.000 combates.

## Notas de balanceo

Dos cosas que conviene tener presentes al tocar `bot/game/balance.py`:

- La tabla de XP de referencia del `CLAUDE.md` (465 en el nivel 5, 1.588 en el 10, 4.869 en el
  20) no la produce ningún exponente. Manda la fórmula `int(40 * nivel ** 1.6)`, que da 525,
  1.592 y 4.827. Los tests comprueban la fórmula.
- Un combate ganado cuesta en torno al 70 % de la vida máxima, y la vida se recupera al 2 %
  cada 2 minutos: 100 minutos para curarse del todo frente a los 6 minutos que tarda en llegar
  cada punto de energía. Encadenando los 20 puntos de energía de una sentada se ganan sobre
  1 de cada 20 combates. Si el ritmo se quiere más suave, la palanca es `HP_REGEN_PERCENT`.

## Ideas futuras

Fuera del alcance actual, cada una cambia el balanceo:

- Pisos de mazmorra encadenados
- PvP y gremios
- Clases de personaje y habilidades activas
- Mercado entre jugadores
- Pagos con Telegram Stars
- Mini App

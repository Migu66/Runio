# CLAUDE.md

Instrucciones de proyecto para Claude Code. Léelas enteras antes de escribir código.

---

## 1. Qué estamos construyendo

Un **bot de Telegram de RPG de progresión**: el jugador crea un personaje, entra a mazmorras, combate por turnos, sube de nivel, consigue objetos con rarezas y compite en un ranking. La energía limita cuántas veces puede jugar al día.

**No** es un asistente de mesa (no tira dados para partidas de D&D), **no** es un narrador con IA, **no** hay llamadas a ningún LLM. Todo es lógica determinista y balanceada a mano.

**Producto mínimo viable:** un jugador puede escribir `/start`, `/mazmorra`, ganar el combate pulsando botones, subir a nivel 2 y equiparse un arma que ha soltado el enemigo. Si eso funciona de punta a punta, el resto es incremental.

---

## 2. Stack y decisiones cerradas

No las cambies sin preguntarme.

| Elemento | Decisión | Motivo |
|---|---|---|
| Lenguaje | Python 3.11+ | `tomllib`, tipos modernos |
| Framework | `aiogram` 3.x | FSM, middlewares y `CallbackData` tipado |
| Base de datos | SQLite vía `aiosqlite` | Cero infraestructura; suficiente para miles de jugadores |
| Config | `pydantic-settings` + `.env` | Validación al arrancar, no a mitad de partida |
| Tests | `pytest` | — |
| Lint/format | `ruff` | Formatea y lintea con una sola herramienta |
| Modo de conexión | *Long polling* | Sin dominio ni HTTPS en desarrollo |
| Parse mode | `HTML` | Menos frágil que Markdown con nombres de usuario |

**Prohibido sin consultarme:** ORMs (SQLAlchemy, Tortoise), Postgres, Redis, Docker Compose, webhooks, cualquier dependencia que no esté en la tabla o en `requirements.txt`.

---

## 3. Estructura del repositorio

Créala exactamente así:

```
rpg-bot/
├── CLAUDE.md
├── README.md                 # instalación y comandos, para humanos
├── .env.example
├── .gitignore                # .env, *.db, __pycache__, .venv, .pytest_cache
├── requirements.txt
├── pyproject.toml            # config de ruff y pytest
├── migrations/
│   └── 001_initial.sql
├── bot/
│   ├── __init__.py
│   ├── __main__.py           # punto de entrada: python -m bot
│   ├── config.py             # Settings (pydantic-settings)
│   ├── db.py                 # conexión, migraciones, helper de transacciones
│   ├── models.py             # dataclasses: Player, Item, Monster, Fight
│   ├── callbacks.py          # CallbackData factories
│   ├── keyboards.py          # constructores de teclados inline
│   ├── texts.py              # TODOS los strings visibles al usuario
│   ├── middlewares.py        # ensure_player, throttling, captura de errores
│   ├── game/                 # LÓGICA PURA: sin I/O, sin DB, sin aiogram
│   │   ├── __init__.py
│   │   ├── balance.py        # todas las constantes numéricas
│   │   ├── formulas.py       # xp, hp, energía, daño
│   │   ├── monsters.py       # generación de enemigos
│   │   ├── loot.py           # generación de objetos
│   │   └── combat.py         # motor de combate por turnos
│   ├── repo/                 # acceso a datos, una función por operación
│   │   ├── __init__.py
│   │   ├── players.py
│   │   ├── items.py
│   │   └── fights.py
│   └── handlers/
│       ├── __init__.py       # register_all(dp)
│       ├── start.py
│       ├── profile.py
│       ├── dungeon.py        # el más grande: inicio de combate + callbacks
│       ├── inventory.py
│       ├── shop.py
│       ├── ranking.py
│       └── daily.py
└── tests/
    ├── test_formulas.py
    ├── test_combat.py
    ├── test_loot.py
    └── test_repo.py
```

**Regla de oro de la arquitectura:** `bot/game/` no importa nada de `aiogram`, `aiosqlite` ni `bot/repo/`. Son funciones puras que reciben datos y devuelven datos. El azar entra siempre como parámetro `rng: random.Random`, nunca se usa `random.foo()` directamente. Así el juego entero es testeable sin bot y sin base de datos.

---

## 4. Esquema de base de datos

`migrations/001_initial.sql`, literal:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS players (
    user_id       INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    level         INTEGER NOT NULL DEFAULT 1,
    xp            INTEGER NOT NULL DEFAULT 0,
    hp            INTEGER NOT NULL,
    gold          INTEGER NOT NULL DEFAULT 0,
    potions       INTEGER NOT NULL DEFAULT 3,
    energy        INTEGER NOT NULL,
    energy_ts     INTEGER NOT NULL,
    hp_ts         INTEGER NOT NULL,
    weapon_id     INTEGER REFERENCES items(id) ON DELETE SET NULL,
    armor_id      INTEGER REFERENCES items(id) ON DELETE SET NULL,
    amulet_id     INTEGER REFERENCES items(id) ON DELETE SET NULL,
    wins          INTEGER NOT NULL DEFAULT 0,
    losses        INTEGER NOT NULL DEFAULT 0,
    last_daily    INTEGER NOT NULL DEFAULT 0,
    created_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id   INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    slot       TEXT    NOT NULL CHECK (slot IN ('weapon','armor','amulet')),
    name       TEXT    NOT NULL,
    rarity     TEXT    NOT NULL,
    item_level INTEGER NOT NULL,
    atk        INTEGER NOT NULL DEFAULT 0,
    def        INTEGER NOT NULL DEFAULT 0,
    crit       INTEGER NOT NULL DEFAULT 0,   -- puntos porcentuales
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_id, slot);

CREATE TABLE IF NOT EXISTS fights (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE REFERENCES players(user_id) ON DELETE CASCADE,
    monster     TEXT    NOT NULL,           -- JSON del Monster
    player_hp   INTEGER NOT NULL,
    monster_hp  INTEGER NOT NULL,
    turn        INTEGER NOT NULL DEFAULT 0,
    chat_id     INTEGER NOT NULL,
    message_id  INTEGER NOT NULL,
    log         TEXT    NOT NULL DEFAULT '[]',  -- JSON, últimas 4 líneas
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ranking ON players(level DESC, xp DESC);
```

Notas:

- `UNIQUE` en `fights.user_id` garantiza **un solo combate activo por jugador**. Es una invariante del juego impuesta por el motor de la base de datos, no por un `if`.
- `energy_ts` y `hp_ts` son marcas de tiempo Unix en segundos. La energía y la vida **no se regeneran con tareas programadas**: se recalculan al leerlas (ver §5.1).
- Guarda todos los tiempos como `INTEGER` (epoch UTC). Nunca `TEXT` con fechas.

---

## 5. Reglas del juego (implementación exacta)

Todas las constantes viven en `bot/game/balance.py` y **solo ahí**. Si escribes un número mágico en un handler, está mal.

```python
# bot/game/balance.py
ENERGY_MAX = 20
ENERGY_REGEN_SECONDS = 360  # 1 punto cada 6 min → lleno en 2 h
ENERGY_COST_DUNGEON = 1

HP_REGEN_SECONDS = 120  # cada 2 min...
HP_REGEN_PERCENT = 0.02  # ...recupera un 2% de la vida máxima

XP_BASE, XP_EXPONENT = 40, 1.6
HP_BASE, HP_PER_LEVEL = 40, 12
ATK_BASE, ATK_PER_LEVEL = 6, 2
DEF_BASE, DEF_PER_LEVEL = 2, 1

DAMAGE_VARIANCE = (0.90, 1.10)
DEFENSE_K = 6  # constante de mitigación
CRIT_BASE_CHANCE = 5  # %
CRIT_MULTIPLIER = 1.8
FLEE_CHANCE = 0.6
MAX_TURNS = 40  # corta combates eternos

LOOT_CHANCE = 0.45
POTION_HEAL_PERCENT = 0.40
DEATH_GOLD_PENALTY = 0.10  # pierde el 10% del oro
DEATH_HP_RESTORE = 0.50

DAILY_GOLD, DAILY_POTIONS = 100, 2
```

### 5.1 Energía y vida (regeneración perezosa)

Este patrón se repite para las dos. Nunca uses `apscheduler` ni bucles de fondo.

```python
def regen_energy(energy: int, energy_ts: int, now: int) -> tuple[int, int]:
    """Devuelve (energía_actual, nuevo_ts).

    Si ya está al máximo, el ts se adelanta a `now` para que no se
    acumule crédito invisible. Si no, solo se consumen los ciclos
    completos y el resto se arrastra al siguiente cálculo.
    """
```

Reglas concretas:

- Si `energy >= ENERGY_MAX` → devuelve `(ENERGY_MAX, now)`.
- Si no → `ganados = (now - energy_ts) // ENERGY_REGEN_SECONDS`; nueva energía `min(MAX, energy + ganados)`; nuevo ts `energy_ts + ganados * ENERGY_REGEN_SECONDS` (**no** `now`, o pierdes el resto y la regeneración se ralentiza).
- Al gastar energía, si estaba al máximo hay que fijar `energy_ts = now` antes de restar, o empieza a regenerar desde una marca antigua y se rellena al instante.

La vida sigue la misma lógica con `HP_REGEN_SECONDS` y `ceil(max_hp * HP_REGEN_PERCENT)` por ciclo, con tope en `max_hp`. **La vida no se regenera durante un combate activo.**

### 5.2 Progresión

```python
def xp_to_next(level: int) -> int:       # int(40 * level ** 1.6)
def max_hp(level: int) -> int:           # 40 + 12 * level
def base_atk(level: int) -> int:         # 6 + 2 * level
def base_def(level: int) -> int:         # 2 + level
```

Valores de referencia que deben cumplirse (úsalos como test):

| Nivel | XP para subir | Vida máx. | Ataque base | Defensa base |
|---|---|---|---|---|
| 1 | 40 | 52 | 8 | 3 |
| 5 | 465 | 100 | 16 | 7 |
| 10 | 1.588 | 160 | 26 | 12 |
| 20 | 4.869 | 280 | 46 | 22 |

Al subir de nivel: la vida se rellena al máximo, el excedente de XP se arrastra, y **puede subir varios niveles de golpe** (usa un `while xp >= xp_to_next(level)`).

### 5.3 Estadísticas efectivas

`atk_total = base_atk(nivel) + suma de atk de los 3 objetos equipados`, igual para `def` y `crit`. Calcúlalo en una única función `effective_stats(player, equipped_items) -> Stats` y no lo repliques en ningún sitio.

### 5.4 Combate

```python
def compute_damage(
    atk: int, defense: int, crit_chance: int, rng: random.Random
) -> tuple[int, bool]:
    raw = atk * rng.uniform(*DAMAGE_VARIANCE)
    mitigated = raw * 100 / (100 + defense * DEFENSE_K)
    is_crit = rng.randint(1, 100) <= crit_chance
    if is_crit:
        mitigated *= CRIT_MULTIPLIER
    return max(1, round(mitigated)), is_crit
```

**Nunca `daño = ataque - defensa`.** Con esa fórmula el daño llega a cero y el juego se rompe. La mitigación con rendimientos decrecientes garantiza que siempre se hace al menos 1 de daño y que subir defensa siempre aporta algo sin volverte invulnerable.

Un turno (`resolve_turn`) es una función pura que recibe el estado del combate, la acción y un `rng`, y devuelve `(nuevo_estado, lista_de_eventos)`:

1. **Atacar** → el jugador golpea; si el monstruo sobrevive, contraataca.
2. **Poción** → cura `40%` de la vida máxima, gasta una poción, el monstruo ataca igualmente (curarse cuesta el turno).
3. **Huir** → 60% de éxito, termina el combate sin recompensa; si falla, el monstruo golpea gratis.

Al llegar a `MAX_TURNS` el combate se declara empate y termina. Esto no es opcional: sin ese tope, dos entidades con mucha defensa y poco ataque pueden quedarse atascadas.

**Victoria:** `xp = int(18 * nivel_monstruo ** 1.2)`, `oro = rng.randint(8, 15) * nivel_monstruo`, tirada de botín al 45%. Los jefes multiplican XP y oro por 2.5.

**Derrota:** pierde el 10% del oro (mínimo 0), la vida se restaura al 50% del máximo, `losses += 1`. **No se pierde XP ni objetos**: castigar duro en un juego de chat hace que la gente lo abandone.

### 5.5 Monstruos

Nivel del monstruo = nivel del jugador, con `rng.choice([-1, 0, 0, 0, +1])` acotado a mínimo 1.

```
hp  = 30 + 14 * lvl
atk = round(5 + 2.2 * lvl)
def = round(1 + 0.8 * lvl)
```

Cada 5 niveles del jugador (nivel % 5 == 0) hay un 35% de que aparezca un **jefe**: vida ×1.6, ataque ×1.3, recompensas ×2.5, nombre con prefijo y emoji distinto.

Nombres: combina una lista de ~12 criaturas (Rata gigante, Goblin, Esqueleto, Lobo huargo, Bandido, Araña, Gólem, Espectro, Ogro, Basilisco, Quimera, Dragón joven) con ~8 epítetos por franja de nivel. No hace falta que sea sofisticado, pero que no salga siempre el mismo bicho.

### 5.6 Botín

Tabla de rarezas, exacta:

| Rareza | Probabilidad | Multiplicador | Emoji |
|---|---|---|---|
| Común | 60,0% | 1,00 | ⚪ |
| Poco común | 25,0% | 1,25 | 🟢 |
| Raro | 11,0% | 1,60 | 🔵 |
| Épico | 3,5% | 2,10 | 🟣 |
| Legendario | 0,5% | 3,00 | 🟠 |

Potencia base del objeto: `2 + 1.2 * nivel_objeto`, multiplicada por la rareza y por `rng.uniform(0.9, 1.1)`, redondeada, mínimo 1. Reparto por ranura:

- **Arma** → todo a `atk`; los raros o mejores añaden `crit = rng.randint(1, 5)`.
- **Armadura** → todo a `def`.
- **Amuleto** → 50% a `atk`, 50% a `def`, más `crit = rng.randint(1, 3)`.

Como el nivel del objeto es el del monstruo, un legendario temprano es potente pero se queda obsoleto solo. Eso es intencionado: no rompe la curva.

Al soltar un objeto, el mensaje de victoria debe indicar si mejora al equipado actual (comparando la suma de estadísticas) con un ▲ o un ▼. Es la información que el jugador necesita para decidir en un segundo.

---

## 6. Comandos y flujos

| Comando | Qué hace |
|---|---|
| `/start` | Crea el personaje si no existe (nombre = `first_name`), da la bienvenida y muestra el teclado principal |
| `/perfil` | Ficha completa: nivel, barra de XP, vida, energía con tiempo hasta el siguiente punto, estadísticas efectivas, equipo, oro, victorias/derrotas |
| `/mazmorra` | Gasta 1 de energía y empieza un combate. Si ya hay uno activo, reengancha ese mensaje en vez de crear otro |
| `/equipo` | Inventario paginado (8 por página) con botones para equipar |
| `/tienda` | Comprar pociones (50 de oro) y vender objetos no equipados (10 × nivel × multiplicador de rareza) |
| `/ranking` | Top 10 por nivel y XP, más la posición del jugador si no está en el top |
| `/diario` | Recompensa cada 20 h: oro, pociones y energía llena |
| `/ayuda` | Explicación breve de las mecánicas |

Barra de progreso: usa bloques `█` y `░` sobre 10 caracteres. Nada de porcentajes sueltos, se lee peor en móvil.

Registra los comandos en el menú de Telegram al arrancar con `bot.set_my_commands()`.

---

## 7. Interfaz y callbacks

Usa las factorías tipadas de aiogram, no strings a mano:

```python
class FightCB(CallbackData, prefix="f"):
    action: str  # "atk" | "potion" | "flee"
    fight_id: int
    turn: int
    user_id: int


class EquipCB(CallbackData, prefix="eq"):
    item_id: int
    user_id: int
```

**Tres validaciones obligatorias en cada callback de combate**, en este orden:

1. `cb.from_user.id != data.user_id` → `cb.answer("Ese no es tu combate", show_alert=True)` y salir. Sin esto, en un grupo cualquiera pulsa el botón de otro.
2. El combate existe y su `id` coincide → si no, `cb.answer("Este combate ya terminó")` y limpia el teclado del mensaje.
3. `data.turn != fight.turn` → `cb.answer("Ya has actuado")` y salir. Esto es la **idempotencia**: protege del doble toque y de los reintentos de Telegram, que reenvía la misma actualización si tardas en responder.

Reglas de UI:

- **Siempre** `cb.answer()` antes de terminar, aunque sea vacío. Si no, al usuario le queda el botón girando varios segundos.
- Durante el combate se **edita el mismo mensaje** (`edit_text`), no se envían nuevos. Al terminar, se quitan los botones y se manda uno nuevo con el resumen.
- Captura `TelegramBadRequest` cuando el texto no ha cambiado (`message is not modified`): es inofensivo, ignóralo.
- Escapa siempre los nombres de usuario con `html.escape()` antes de meterlos en el mensaje. Un jugador que se llame `<b>` te rompe el parseo.
- El registro de combate muestra solo las **últimas 4 líneas**, o el mensaje crece sin control.

---

## 8. Acceso a datos y concurrencia

Aunque solo hay un combate activo por jugador, el doble toque provoca lecturas-modificaciones-escrituras simultáneas. Regla: **toda operación que lea y luego escriba el mismo dato va dentro de una transacción `BEGIN IMMEDIATE`.**

```python
@asynccontextmanager
async def transaction(db):
    await db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
```

Configura al abrir la conexión: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`. Una sola conexión compartida en el ciclo de vida del bot, guardada en `dispatcher["db"]` e inyectada a los handlers.

Las funciones de `bot/repo/` reciben la conexión como primer parámetro y devuelven dataclasses de `bot/models.py`, nunca `sqlite3.Row` crudos. Ningún handler escribe SQL.

---

## 9. Middlewares

- **`EnsurePlayerMiddleware`**: carga el jugador y lo inyecta como `data["player"]`. Si no existe y el comando no es `/start`, responde pidiendo que use `/start` y corta.
- **`ThrottlingMiddleware`**: máximo 1 acción cada 0,7 s por usuario (caché en memoria con TTL). Los mensajes descartados no se responden, solo se ignoran.
- **Manejador global de errores**: registra la traza completa con el `update_id` y responde al usuario un texto genérico. **Nunca** enseñes trazas al jugador.

Límites de Telegram que debes respetar: 30 mensajes por segundo globales y 20 por minuto en un mismo grupo. Con la limitación por usuario ya vas sobrado, pero no montes bucles que envíen mensajes masivos.

---

## 10. Tests

Ejecuta `pytest` antes de dar por terminada cualquier fase. Los tests van sobre `bot/game/` (puro) y `bot/repo/` (con una base de datos temporal). No hace falta testear los handlers.

Casos que **tienen que** existir:

**`test_formulas.py`**
- `xp_to_next` es estrictamente creciente y coincide con la tabla de §5.2.
- La energía nunca supera `ENERGY_MAX` ni baja de 0, con saltos de tiempo de 0 s, 359 s, 360 s, 1 día y un `energy_ts` en el futuro (reloj desajustado).
- Regenerar 359 s dos veces seguidas acaba dando 1 punto de energía (el resto se arrastra, no se pierde).
- La vida nunca supera `max_hp(level)`.

**`test_combat.py`**
- `compute_damage` devuelve ≥ 1 con `atk=1, defense=9999`.
- Un combate completo con `random.Random(42)` termina siempre y en menos de `MAX_TURNS` turnos.
- Simula 1.000 combates de un jugador de nivel 5 sin equipo contra monstruos de su nivel: la tasa de victoria debe quedar **entre el 55% y el 80%**. Si se sale de ahí, el balanceo está mal, no el test.
- Una poción nunca sube la vida por encima del máximo.
- Un turno resuelto con el mismo `turn` dos veces no aplica el daño dos veces.

**`test_loot.py`**
- Con 100.000 tiradas, la distribución de rarezas se aproxima a la tabla con un margen del 10% relativo.
- Las estadísticas de un objeto son siempre ≥ 1.
- Un legendario de nivel 1 tiene menos potencia total que un común de nivel 20 (la curva de nivel domina a la rareza).

**`test_repo.py`**
- Insertar dos combates para el mismo `user_id` falla (la invariante `UNIQUE`).
- Borrar un jugador borra sus objetos en cascada.

---

## 11. Plan de construcción por fases

Trabaja **una fase completa cada vez**, con sus tests pasando, y para. No adelantes funcionalidad de fases posteriores.

**Fase 0 — Esqueleto.** Estructura de carpetas, `requirements.txt`, `pyproject.toml`, `.env.example`, `config.py`, `__main__.py` que arranca el polling y responde `/start` con un texto fijo.
*Hecho cuando:* `python -m bot` arranca y el bot contesta en Telegram.

**Fase 1 — Datos y personaje.** `db.py` con migraciones, `models.py`, `repo/players.py`, `/start` que crea el personaje, `/perfil`.
*Hecho cuando:* el personaje persiste tras reiniciar el bot.

**Fase 2 — Energía y regeneración.** `formulas.py` completo con sus tests.
*Hecho cuando:* `/perfil` muestra la energía y el tiempo exacto hasta el siguiente punto, y `pytest tests/test_formulas.py` pasa.

**Fase 3 — Combate.** `monsters.py`, `combat.py`, `repo/fights.py`, `handlers/dungeon.py` con sus callbacks. Sin botín todavía: al ganar solo da XP y oro.
*Hecho cuando:* se puede pelear, ganar, perder, huir y subir de nivel, y el doble toque no duplica daño.

**Fase 4 — Botín y equipo.** `loot.py`, `repo/items.py`, `/equipo` con paginación, comparación ▲/▼ en la victoria.
*Hecho cuando:* un objeto soltado se puede equipar y las estadísticas del perfil cambian.

**Fase 5 — Economía y social.** `/tienda`, `/diario`, `/ranking`.

**Fase 6 — Pulido.** Middlewares, manejador de errores, `set_my_commands`, logging estructurado, `README.md`, y un script `run.sh`.

---

## 12. Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # y pega tu token
python -m bot
```

`.env.example`:

```
BOT_TOKEN=123456:AAAA-token-de-BotFather
DB_PATH=./rpg.db
LOG_LEVEL=INFO
ADMIN_IDS=
```

El token se saca hablando con [@BotFather](https://t.me/BotFather) → `/newbot`. **El `.env` nunca se sube al repositorio**; asegúrate de que está en `.gitignore` desde el primer commit.

En VS Code: instala la extensión de Python y crea un `.vscode/launch.json` con una configuración de tipo `module` apuntando a `bot`, para poder depurar con puntos de interrupción dentro de los handlers.

---

## 13. Cómo quiero que trabajes

- **Escribe primero las funciones puras de `bot/game/` y sus tests, después los handlers.** Es donde está toda la sustancia del juego y donde los errores duelen.
- Tipa todas las firmas. `ruff check .` y `ruff format .` limpios antes de terminar una fase.
- Docstrings en español, de una línea, solo donde la función no sea obvia. Nada de comentarios que repitan lo que dice el código.
- Los mensajes de commit, en español y en imperativo: `añade motor de combate por turnos`.
- Si una decisión del documento choca con la realidad al implementarla, **párate y dímelo** en vez de improvisar una alternativa.
- Si algo no está especificado aquí (por ejemplo el texto exacto de un mensaje), elige tú y sigue adelante; solo pregunta por decisiones de arquitectura o de balanceo.

### Errores concretos que no quiero ver

- Estado de partida en un diccionario global en memoria.
- `daño = ataque - defensa`.
- Números de balanceo escritos dentro de un handler.
- `random.randint()` directamente dentro de `bot/game/` en vez de `rng.randint()`.
- Un callback que no llama a `cb.answer()`.
- `except Exception: pass`.
- `time.sleep()` en código asíncrono (es `await asyncio.sleep()`).
- Enviar un mensaje nuevo en cada turno de combate en lugar de editar el existente.

---

## 14. Fuera de alcance por ahora

No implementes nada de esto aunque parezca una mejora evidente: pisos de mazmorra encadenados, PvP, gremios, clases de personaje, habilidades activas, mercado entre jugadores, pagos con Telegram Stars, Mini App. Son la fase 2 del proyecto y cada uno cambia el balanceo. Si se te ocurre algo bueno, apúntalo al final del `README.md` en una sección de ideas futuras.

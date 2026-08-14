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

## Alojarlo en un servidor

El bot usa *long polling*: no necesita dominio, ni certificado, ni puertos abiertos, solo salida
a internet. Lo que sí necesita es **disco persistente**, porque las partidas viven en un fichero
SQLite. Eso descarta los planes gratuitos con sistema de ficheros efímero, que borrarían
`rpg.db` en cada reinicio: hace falta una máquina de verdad, sea alquilada o la de tu casa.

Con Python 3.11 o superior instalado, en la máquina:

```bash
sudo adduser --system --group --home /opt/runio runio
sudo -u runio git clone https://github.com/Migu66/Runio.git /opt/runio
cd /opt/runio
sudo -u runio python3 -m venv .venv
sudo -u runio .venv/bin/pip install -r requirements.txt
sudo -u runio cp .env.example .env
sudo -u runio nano .env      # y pega el token
```

Y para que arranque al encender la máquina y se levante solo si se cae, en
`/etc/systemd/system/runio.service`:

```ini
[Unit]
Description=Runio, bot de Telegram
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=runio
WorkingDirectory=/opt/runio
ExecStart=/opt/runio/.venv/bin/python -m bot
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now runio
sudo journalctl -u runio -f      # ver el log en directo
```

La ruta de trabajo es la que hace que el bot encuentre su `.env` y deje el `rpg.db` al lado.

### Copia de seguridad

Las partidas son un único fichero. Esta línea saca una copia en caliente, con el bot en marcha,
sin instalar nada:

```bash
/opt/runio/.venv/bin/python -c \
  "import sqlite3; sqlite3.connect('/opt/runio/rpg.db').backup(sqlite3.connect('/opt/runio/copia.db'))"
```

Métela en un `cron` diario y llévate la copia fuera de la máquina de vez en cuando.

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
- Ganar un combate se lleva la mayor parte de la vida, y la vida se recupera al 2 % cada 2
  minutos: 100 minutos para curarse del todo frente a los 6 minutos que tarda en llegar cada
  punto de energía. Simulando sesiones completas de 20 puntos de energía, un nivel 5 gana el
  6,6 % de los combates si los encadena y el 43 % si espera una hora entre uno y otro. Con los
  tests de combate no se ve porque cada combate simulado empieza a vida llena. Si el ritmo se
  quiere más suave, la palanca es `HP_REGEN_PERCENT`.

## Ideas futuras

Fuera del alcance actual, cada una cambia el balanceo:

- Pisos de mazmorra encadenados
- PvP y gremios
- Clases de personaje y habilidades activas
- Mercado entre jugadores
- Pagos con Telegram Stars
- Mini App

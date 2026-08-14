# Runio

Bot de Telegram de RPG de progresión: crea un personaje, baja a la mazmorra, combate por
turnos, sube de nivel, consigue objetos y compite en el ranking.

## Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # y pega tu token
python -m bot
```

El token se saca hablando con [@BotFather](https://t.me/BotFather) → `/newbot`.

## Desarrollo

```bash
pytest            # tests
ruff check .      # lint
ruff format .     # formato
```

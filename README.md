# Bot Inmobiliario 🏠

Bot que busca diariamente monoambientes en alquiler en CABA (dueño directo) en ZonaProp, Argenprop y MercadoLibre, rankea los 5 mejores por relación m²/precio y los manda por Telegram.

## Configuración inicial

### 1. Clonar y subir a GitHub
```bash
git init
git add .
git commit -m "primer commit"
git remote add origin https://github.com/TU_USUARIO/bot-inmobiliario.git
git push -u origin main
```

### 2. Agregar los secrets en GitHub
Ir a **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor |
|--------|-------|
| `TELEGRAM_TOKEN` | El token que te dio @BotFather |
| `TELEGRAM_CHAT_ID` | Tu ID numérico de @userinfobot |

### 3. Activar GitHub Actions
Ir a la pestaña **Actions** del repo y habilitar los workflows.

### 4. Probar manualmente
En la pestaña **Actions → Bot Inmobiliario Diario → Run workflow**.

## Ajustar filtros

Editá `config.json`:
```json
{
  "precio_min": 400000,
  "precio_max": 550000
}
```

## Cómo funciona el scoring

El bot rankea por **relación m²/precio** — cuánto m² obtenés por cada peso. Un monoambiente de 38m² a $450.000 puntúa mejor que uno de 28m² a $420.000.

También suma puntos si el precio está en la mitad baja del rango y si supera los 35/45 m².

## Archivos

```
bot.py              ← lógica principal
config.json         ← tus filtros
vistos.json         ← historial (se actualiza solo)
requirements.txt    ← dependencias Python
.github/workflows/  ← scheduler diario
```

# Siguiente: lo que ya está hecho y lo que tenés que hacer vos

## Ya hecho

- **Paso A:** Tu archivo **`.streamlit/secrets.toml`** ya tiene la contraseña de Supabase y está listo para usar (no se sube a GitHub; está en .gitignore).
- **Paso B:** El código ya está subido a GitHub: https://github.com/gianfrancoeliggi/PriceScraperT  
- Hay un script **`run_scrape_once.py`** para llenar la base de datos una vez desde la terminal (sin abrir la app en el navegador).

---

## Paso C: Llenar la base de datos (una vez, en tu computadora)

Cuando hayas hecho el Paso A:

1. Abrí la **terminal** en Cursor (menú **Terminal** → **New Terminal**) y asegurate de estar en la carpeta del proyecto.
2. Ejecutá:

   ```bash
   python3 run_scrape_once.py
   ```

3. Esperá a que termine (puede tardar varios minutos). Cuando termine, los datos ya están en Supabase.

**Alternativa:** Si preferís usar la app en el navegador: ejecutá `streamlit run app.py`, entrá con la contraseña de admin (la de `SCRAPE_PASSWORD` en secrets.toml), andá a la pestaña **Run scrape** y hacé clic en **Execute scrape**.

---

## Paso D: Desplegar en Streamlit Cloud

Cuando el Paso C haya terminado bien:

1. Entrá en **https://share.streamlit.io** e iniciá sesión con **GitHub**.
2. Clic en **New app**.
3. **Repository:** `gianfrancoeliggi/PriceScraperT`
4. **Branch:** `main`
5. **Main file path:** `app.py` (debe ser exactamente eso).
6. Clic en **Advanced settings** → **Secrets**.
7. Abrí tu archivo **`.streamlit/secrets.toml`** en tu proyecto y **copiá todo su contenido** (las dos líneas: SCRAPE_PASSWORD y DATABASE_URL). Pegalo en el cuadro de Secrets de Streamlit Cloud. Clic en **Save**.
8. Clic en **Deploy**. Esperá unos minutos.
9. Te va a dar una URL (ej. `https://pricescrapert-xxx.streamlit.app`). Esa es tu app en internet.

Compartí esa URL con tu equipo. Ellos van a poder ver los datos; no van a poder actualizar nada a menos que conozcan la contraseña de admin (no se la des si no querés).

---

## Importante: revocar el token de GitHub

El token de GitHub que usaste para el push quedó expuesto en el chat. Por seguridad, **revocalo** y creá uno nuevo si lo necesitás:

1. Entrá en GitHub → **Settings** (tu foto arriba a la derecha) → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. Buscá el token que usaste para PriceScraperT y hacé clic en **Revoke**.
3. Si más adelante necesitás hacer push de nuevo, generá un **nuevo token** y usalo solo desde tu PC, sin compartirlo.

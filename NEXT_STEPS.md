# Siguiente: completar y desplegar

## 1. Poner tu contraseña real en secrets (solo tú la ves)

1. Abre el archivo **`.streamlit/secrets.toml`** en tu proyecto.
2. Donde dice **`REPLACE_WITH_YOUR_SUPABASE_DB_PASSWORD`**, bórralo y escribe la **contraseña de la base de datos** de Supabase (la que pusiste al crear el proyecto en Supabase). Si no la recuerdas: Supabase → tu proyecto → **Settings** → **Database** → **Database password** (o resetéala).
3. Donde dice **`my-admin-password`**, puedes dejarlo o cambiarlo por una contraseña que solo tú sepas (esa será la que uses para poder hacer "Execute scrape" en la app).
4. Guarda el archivo.

---

## 2. Subir el proyecto a GitHub

En la **terminal** (en Cursor: Terminal → New Terminal), dentro de la carpeta del proyecto, ejecuta estos comandos **uno por uno**:

```bash
git init
git add .
git commit -m "Add Shapermint price scraper app"
git branch -M main
git remote add origin https://github.com/gianfrancoeliggi/PriceScraperT.git
git push -u origin main --force
```

(El `--force` es porque tu repo en GitHub ya tiene un README; así se reemplaza con este proyecto.)

Si te pide usuario y contraseña de GitHub: usa tu usuario y, como contraseña, un **Personal Access Token** (GitHub → Settings → Developer settings → Personal access tokens → Generate new token). Si no tienes Git instalado, instálalo antes: https://git-scm.com/downloads

---

## 3. Llenar la base de datos (una vez, desde tu computadora)

1. En la terminal, en la carpeta del proyecto:

   ```bash
   streamlit run app.py
   ```

2. Se abrirá la app en el navegador. En la **barra lateral**, escribe la contraseña de admin (la de `SCRAPE_PASSWORD` en secrets.toml) y haz clic en **Log in**.
3. Ve a la pestaña **Run scrape** y haz clic en **Execute scrape**. Espera a que termine (varios minutos).
4. Cuando termine, los datos ya están en Supabase. Puedes cerrar la app (Ctrl+C en la terminal).

---

## 4. Desplegar en Streamlit Cloud

1. Entra en **https://share.streamlit.io** e inicia sesión con **GitHub**.
2. Clic en **New app**.
3. **Repository:** `gianfrancoeliggi/PriceScraperT`
4. **Branch:** `main`
5. **Main file path:** `app.py`
6. Clic en **Advanced settings** → **Secrets**.
7. Pega esto y **sustituye** las dos contraseñas por las mismas que usaste en `.streamlit/secrets.toml` (contraseña de Supabase y contraseña de admin):

   ```
   SCRAPE_PASSWORD = "la-misma-contraseña-de-admin-que-en-secrets"
   DATABASE_URL = "postgresql://postgres:TU_CONTRASEÑA_SUPABASE@db.yiybgogqeehgrrbhrgti.supabase.co:5432/postgres"
   ```

   Clic en **Save**.
8. Clic en **Deploy**. Espera unos minutos.
9. Te dará una URL (ej. `https://pricescrapert-xxx.streamlit.app`). Esa es tu app en internet.

---

## 5. Compartir con tu equipo

Envía a tu equipo la **URL** que te dio Streamlit. Ellos podrán ver los datos; no podrán actualizar nada a menos que conozcan la contraseña de admin (no se la des si no quieres).

Para actualizar los datos más adelante: en tu PC ejecuta otra vez `streamlit run app.py`, entra con la contraseña de admin y haz **Execute scrape**. Los datos se guardan en Supabase y todo el mundo verá los datos nuevos al abrir la URL.

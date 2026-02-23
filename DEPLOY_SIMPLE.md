# Cómo poner la app en internet para que tu equipo la use (solo ver datos)

Sigue estos pasos en orden. No hace falta ser programador.

---

## Qué vas a lograr

- Una **página web** que tu equipo puede abrir desde el navegador.
- Ellos **solo ven** los precios y el historial (no pueden actualizar nada).
- **Tú** puedes actualizar los datos cuando quieras, desde tu computadora (opcional).

---

## Paso 1: Crear una base de datos en la nube (gratis)

La app necesita un lugar donde guardar los datos. En la nube es gratis con Supabase.

1. Entra en **https://supabase.com** y haz clic en **Start your project**.
2. Crea una cuenta (con Google o email).
3. Crea un **nuevo proyecto**: ponle un nombre (ej. "shapermint-prices"), una contraseña para la base de datos (guárdala), y elige una región cercana. Clic en **Create new project**.
4. Espera unos minutos. Cuando termine, entra al proyecto.
5. En el menú izquierdo ve a **Settings** (engranaje) → **Database**.
6. Busca la sección **Connection string** y elige **URI**.
7. Copia la URL que aparece (algo como `postgresql://postgres.xxxx:TU_CONTRASEÑA@aws-0-us-east-1.pooler.supabase.com:6543/postgres`).
8. En esa URL, **reemplaza** donde dice `[YOUR-PASSWORD]` por la contraseña que pusiste al crear el proyecto. Guarda esta URL completa en un archivo de texto; la usarás más adelante como **DATABASE_URL**.

---

## Paso 2: Llenar la base de datos con datos (una vez, desde tu computadora)

Antes de poner la app en internet, hay que tener datos en esa base de datos.

1. En tu computadora, abre la carpeta del proyecto (donde está `app.py`).
2. Crea una carpeta llamada **`.streamlit`** (con el punto delante) si no existe.
3. Dentro de `.streamlit`, crea un archivo llamado **`secrets.toml`** (no el que termina en `.example`).
4. Abre `secrets.toml` con un editor de texto y escribe exactamente esto (cambia la URL por la que copiaste en el Paso 1):

   ```
   DATABASE_URL = "postgresql://postgres.xxxx:TU_CONTRASEÑA@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
   SCRAPE_PASSWORD = "una-contraseña-solo-tuya"
   ```

   Guarda el archivo.

5. Abre la **terminal** (o Cursor/VS Code terminal) en la carpeta del proyecto y ejecuta:

   ```
   streamlit run app.py
   ```

6. En el navegador, entra a la app. En la barra lateral, escribe la contraseña que pusiste en `SCRAPE_PASSWORD` y haz clic en **Log in**.
7. Ve a la pestaña **Run scrape** y haz clic en **Execute scrape**. Espera a que termine (puede tardar unos minutos).
8. Cuando termine, los datos ya están guardados en la base de datos de Supabase. Puedes cerrar la app.

---

## Paso 3: Subir el proyecto a GitHub

Streamlit Cloud necesita el código en GitHub.

1. Entra en **https://github.com** e inicia sesión (o crea una cuenta).
2. Clic en el **+** arriba a la derecha → **New repository**.
3. Nombre del repositorio: por ejemplo **`shapermint-prices`**. Deja **Public**. No marques "Add a README". Clic en **Create repository**.
4. En tu computadora, abre la terminal en la carpeta del proyecto. Si nunca usaste Git, ejecuta estos comandos uno por uno (cambia `TU_USUARIO` por tu usuario de GitHub):

   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/shapermint-prices.git
   git push -u origin main
   ```

   Te pedirá usuario y contraseña de GitHub (o que uses un token). Si no tienes Git instalado, búscalo en internet: "install Git" para tu sistema.

5. **Importante:** No subas el archivo con contraseñas. Asegúrate de que `.streamlit/secrets.toml` esté en `.gitignore` (ya está en el proyecto). Así nadie verá tu contraseña en GitHub.

---

## Paso 4: Desplegar en Streamlit Cloud

1. Entra en **https://share.streamlit.io** e inicia sesión con **GitHub**.
2. Clic en **New app**.
3. **Repository:** elige tu usuario y el repo (ej. `shapermint-prices`).
4. **Branch:** `main`.
5. **Main file path:** escribe **`app.py`**.
6. Clic en **Advanced settings** y luego en **Secrets**.
7. En el cuadro de texto, pega esto y **completa** con tus datos reales (la misma URL de Supabase y la misma contraseña de admin que usaste en el Paso 2):

   ```
   SCRAPE_PASSWORD = "una-contraseña-solo-tuya"
   DATABASE_URL = "postgresql://postgres.xxxx:TU_CONTRASEÑA@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
   ```

   Clic en **Save**.

8. Clic en **Deploy**. Espera unos minutos.
9. Cuando termine, te dará una **URL** (ej. `https://shapermint-prices-xxx.streamlit.app`). Esa es la app en internet.

---

## Paso 5: Compartir con tu equipo

- Envía a tu equipo la **URL** de la app (la que te dio Streamlit).
- Ellos la abren en el navegador y ven **Current prices** y **Price history**. No verán la opción de actualizar datos a menos que conozcan la contraseña de admin (no se la des si no quieres que actualicen).

---

## Cómo actualizar los datos más adelante (solo tú)

Cuando quieras refrescar los precios:

1. En tu computadora, abre la carpeta del proyecto y ejecuta otra vez: **`streamlit run app.py`**.
2. Entra con la contraseña de admin, ve a **Run scrape** y haz clic en **Execute scrape**.
3. Los datos se guardan en la misma base de datos de Supabase. Cuando tu equipo vuelva a abrir la URL de la app, verá los datos nuevos.

No hace falta volver a desplegar en Streamlit Cloud para eso.

---

## Resumen

| Paso | Qué haces |
|------|-----------|
| 1 | Crear cuenta y proyecto en Supabase, copiar la URL de la base de datos. |
| 2 | En tu PC: crear `.streamlit/secrets.toml` con esa URL y una contraseña, ejecutar la app y hacer **Execute scrape** una vez. |
| 3 | Subir el proyecto a GitHub (repo público, sin subir `secrets.toml`). |
| 4 | En share.streamlit.io: conectar el repo, poner `app.py`, y en Secrets pegar la misma URL y contraseña. Desplegar. |
| 5 | Compartir la URL de la app con tu equipo. |

Si algo no te cuadra en un paso, dime en cuál estás y qué ves en pantalla y lo afinamos.

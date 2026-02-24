# Estado actual del proyecto

## Todo listo ✓

- Supabase conectado y funcionando (usando Session Pooler, compatible con IPv4).
- App desplegada en Streamlit Cloud: conectada al repo de GitHub y a Supabase.
- Los 3 scrapers funcionan: Spanx (requests), SKIMS y Honeylove (Playwright).
- El scraper escribe directamente a Supabase — no hace falta script de sync.
- El equipo puede ver precios e historial desde la URL pública.

---

## Cómo actualizar los datos (flujo normal)

Desde la terminal en la carpeta del proyecto:

```bash
python3 run_scrape_once.py
```

Los datos aparecen en la app pública de inmediato. No hace falta reiniciar nada.

---

## Cuándo usar GitHub

Solo cuando cambies el **código** (app.py, scrapers, etc.):

```bash
git add .
git commit -m "descripción del cambio"
git push
```

Streamlit Cloud detecta el push y redespliega la app automáticamente.

Para actualizar **datos** nunca hace falta tocar GitHub.

---

## Cuándo usar sync_local_to_supabase.py

Solo si scrapeás sin internet (el scraper cae a SQLite local). Después de reconectarte:

```bash
python3 sync_local_to_supabase.py
```

El script ahora omite registros duplicados de forma segura.

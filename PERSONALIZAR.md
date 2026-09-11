# Cómo personalizar el perfil

Todo lo visual sale de dos sitios:

| Archivo | Qué controla |
|---|---|
| `profile.json` | usuario, nombre, tagline, snippet de código del banner, repos destacados (nombre, descripción, decoración), stack (`skills`), experiencia (`experience`), formación (`education`), logros (`honors`) |
| `README.md` | el orden de las secciones, los badges de tecnologías y los enlaces |

Los SVG de `assets/` **no se editan a mano**: los genera `scripts/build_profile.py`.

## Cambiar los repos destacados

Edita la lista `pinned` de `profile.json`. Cada entrada acepta:

```json
{
  "repo": "nombre-del-repo",
  "description": "Descripción corta (máx. 2 líneas).",
  "decoration": "peek | mug | note | laptop | sleep | none"
}
```

Decoraciones disponibles:

- `peek` – la mascota asoma por la izquierda saludando
- `laptop` – portátil con la mascota en pantalla (izquierda)
- `mug` – taza `</>` con vapor (derecha)
- `note` – nota adhesiva con checks (derecha)
- `sleep` – mascota durmiendo con luna y zzz (derecha)
- `none` – tarjeta sola

Después añade o quita la etiqueta `<img>` correspondiente en `README.md`
(el nombre del archivo es el repo en minúsculas y con guiones, por ejemplo
`Tienda-Online-` → `assets/pins/tienda-online.svg`).

Si un repo no tiene lenguaje detectado por GitHub, puedes forzarlo:

```json
"language_overrides": { "Farmasys-": "TypeScript" }
```

## Stack, experiencia y formación (datos del CV)

- `skills`: lista de categorías; cada una tiene `category` y `items` como
  pares `["Nombre", "#color"]`. Las píldoras se reparten solas en filas.
- `experience`: lista de puestos con `role`, `company`, `period` y `summary`
  (el resumen se corta a 3 líneas).
- `education`: `school`, `degree`, `date` y `thesis`.
- `honors`: lista de textos cortos (máximo 2 líneas cada uno).

La cabecera (nombre, ubicación, portafolio, email) y el párrafo "sobre mí"
están escritos directamente en `README.md`.

## Regenerar los SVG en tu máquina

```bash
python3 scripts/build_profile.py            # usa la API de GitHub (opcional: export GITHUB_TOKEN=...)
python3 scripts/build_profile.py --offline  # usa solo scripts/cache.json
```

No necesita dependencias, solo Python 3.10 o superior.

## Actualización automática

`.github/workflows/update-profile.yml` ejecuta el generador cada día y en cada
push. Con el `GITHUB_TOKEN` del propio workflow obtiene followers, stars, forks
y el calendario de contribuciones, y hace commit de los SVG si cambiaron.

Si prefieres contar también las contribuciones privadas, crea un token
personal con permiso `read:user` y guárdalo como secreto `PROFILE_TOKEN`.

## Foto de perfil

`assets/avatar.png` es la mascota lista para subir como foto de perfil
(Settings → Public profile → Profile picture).

## Para que aparezca en tu perfil

GitHub solo muestra el README del repositorio que se llama **igual que tu
usuario** y es público. Este repo ya se llama `cajacuenta767-sketch`, así que
el perfil se ve en https://github.com/cajacuenta767-sketch. Si algún día lo
renombras, el diseño dejará de aparecer en el perfil (aunque el repo siga
funcionando).

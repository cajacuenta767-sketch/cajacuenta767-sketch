# Cómo personalizar el perfil

Todo lo visual sale de dos sitios:

| Archivo | Qué controla |
|---|---|
| `profile.json` | usuario, nombre, tagline, snippet de código del banner, repos destacados (nombre, descripción, decoración) |
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
usuario** y es público. Renombra este repo a `cajacuenta767-sketch`
(Settings → General → Repository name) y el perfil se verá al instante.

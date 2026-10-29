# Repositorio del equipo · TC5065

Aquí vive el flujo de su equipo para las etapas del caso Refacciones del Bajío. Cada integrante
construye un subflujo en su propio n8n y lo sube aquí; el integrador los reúne en la instancia del
equipo. Git es el camino entre las dos: de *desarrollo* (tu n8n) a *integración* (el n8n del
integrador).

## Integrantes

Cada integrante agrega su renglón en su **primer push** (semana 2). Solo el nombre de usuario de
GitHub. El integrador es dueño del flujo principal y del subflujo más corto, S4.

**Equipo de cuatro:**

| Usuario de GitHub | Papel | Archivos que le pertenecen |
|---|---|---|
| | integrador | `flujos/principal.json` y `flujos/S4.json` |
| | integrante | `flujos/S1.json` |
| | integrante | `flujos/S2.json` |
| | integrante | `flujos/S3.json` |

**Equipo de tres** (cuando el grupo no se divide exacto entre cuatro): borra la tabla de arriba y
usa esta. Quien tiene dos subflujos se queda con S1 y S2: S2 es una regla corta que recibe lo
que entrega S1, así que los prueba seguidos en su n8n, y S3, con los reintentos y las rutas de error,
queda completo para otra persona. Cuando la libreta te pregunte tu subflujo, escribe `S1, S2`.

| Usuario de GitHub | Papel | Archivos que le pertenecen |
|---|---|---|
| | integrador | `flujos/principal.json` y `flujos/S4.json` |
| | integrante | `flujos/S1.json` y `flujos/S2.json` |
| | integrante | `flujos/S3.json` |

**Si el equipo agrega un flujo de error** (Etapa 1): es del integrador y vive en `flujos/error.json`. No hay que
hacer nada especial: cuando el integrador exporta el principal, la libreta exporta también el flujo de error que
tiene asignado.

## Dónde clonarlo

Con GitHub Desktop o con `git clone`, **clónalo dentro de la carpeta `equipo/` del repositorio del entorno**. Así lo
ve JupyterLab y puedes abrir `protocolo-equipo.ipynb`. La carpeta `equipo/` ya viene en el repositorio del
entorno, y su contenido está en el `.gitignore` del entorno: no se mezclan los dos repositorios.

**Git corre en tu computadora; la libreta, en el JupyterLab del entorno** (<http://localhost:8888>), que
corre dentro de Docker junto a tu n8n. Los dos ven la misma carpeta: lo que la libreta exporta aparece en
GitHub Desktop o en `git status` sin que lo copies.

## El protocolo

1. **Pull** (GitHub Desktop, o `git pull`): trae lo último del equipo.
2. En el **JupyterLab del entorno** (<http://localhost:8888>), entra a `equipo/`, a la carpeta de este
   repositorio, y abre `protocolo-equipo.ipynb`. Tiene que ser ese JupyterLab, no VS Code ni un Jupyter
   instalado en tu computadora: ya trae lo que la libreta necesita, así que no instalas nada ni creas ningún
   ambiente de Python, y desde otro lado la libreta no encuentra tu n8n ni su llave (termina con
   `FileNotFoundError: … '/config/n8n-api-key'`). **Run → Run All Cells**. **La primera vez te pregunta tu
   papel y tu subflujo** y lo guarda en `mi-papel.json`, que es solo tuyo y no se sube a Git. Importa en tu
   n8n lo de tus compañeros, exporta lo tuyo a `flujos/` y verifica las referencias.
3. **Commit** y **Push** de tu archivo. **No subas la libreta**: es de todo el equipo, y
   correrla guarda sus resultados, así que GitHub Desktop la marcará como cambiada; desmárcala. Con git, agrega solo tu
   archivo por su ruta (`git add flujos/S2.json`, `git commit -m "…"`, `git push`) y nunca `git add .`.
   Con git necesitas iniciar sesión una vez con `gh auth login` (Primeros pasos → Git con interfaz gráfica).

El integrador hace lo mismo con el papel `integrador`: así reúne los subflujos en su n8n y sube el
flujo principal. Si te equivocas de papel o de subflujo, borra `mi-papel.json` en el panel de archivos de
JupyterLab y la libreta te lo vuelve a preguntar.

## Tus laboratorios individuales

El Lab 3 y el Lab 4 (semanas 6 y 7) son individuales, pero viven aquí, en la carpeta de su dueño:
`individual/<tu-usuario>/lab3/` y `individual/<tu-usuario>/lab4/`.
Ver `individual/README.md`.

## Tres reglas que evitan casi todos los problemas

- **Un archivo, un dueño.** Nadie edita el archivo de otro. Si necesitas un cambio en el contrato
  de otro subflujo, se acuerda en el equipo y lo hace su dueño.
- **El nombre de cada subflujo es parte de su contrato.** El flujo principal lo encuentra por su
  nombre. No lo cambies.
- **Pull antes de Push.** Si GitHub rechaza tu Push, haz Pull y vuelve a intentarlo.

## Qué no se sube

Las credenciales viven en tu n8n, no en los archivos: al exportar, la libreta las deja solo con su
nombre (`ERP API key`, `ERP OAuth`). El `.gitignore` excluye además archivos de entorno y llaves.

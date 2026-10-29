"""Exportar e importar los flujos del equipo entre tu n8n y este repositorio.

Lo usa la libreta `protocolo-equipo.ipynb`; no hace falta abrir este archivo. Corre dentro del
contenedor `workspace` del entorno del curso, que ve tu n8n en http://n8n:5678 y su llave de API
en /config/n8n-api-key (la crea la página de estado al preparar tu n8n).

Por qué existe: cada n8n asigna ids propios a los flujos, y el nodo que llama a un subflujo lo guarda
por id. Si importas el flujo principal tal cual en otra instancia, cada llamada **muestra el nombre
correcto pero apunta a un id que ahí no existe**. Este script importa primero los subflujos y luego
reconecta cada llamada del principal **por el nombre del subflujo**. Por eso el nombre de cada
subflujo es parte de su contrato. Lo mismo pasa con el flujo de error que se elige en Settings: se
guarda por id, así que en el repositorio se escribe su nombre y al importar se vuelve a buscar. Y con
las Data Tables (Etapa 2): el nodo guarda el id de la tabla, que en otro n8n no existe; en el
repositorio queda su nombre y al importar se busca la tabla con ese nombre.
"""
import json
from pathlib import Path

import httpx

N8N = "http://n8n:5678"
LLAVE = Path("/config/n8n-api-key")
LLAMADA = "n8n-nodes-base.executeWorkflow"
ERROR_TRIGGER = "n8n-nodes-base.errorTrigger"
TABLA = "n8n-nodes-base.dataTable"
CAMPOS = ("name", "nodes", "connections", "settings")   # lo que se guarda en el repositorio


def conectar(url=N8N, llave=None):
    llave = llave or LLAVE.read_text().strip()
    cliente = httpx.Client(base_url=f"{url}/api/v1", headers={"X-N8N-API-KEY": llave}, timeout=60)
    cliente.get("/workflows", params={"limit": 1}).raise_for_status()
    return cliente


PAPELES = ("integrante", "integrador")
SUBFLUJOS = ("S1", "S2", "S3", "S4", "P1", "P2")   # P1 y P2: los flujos de la pasarela (Etapa 2)


def _error_de_papel(papel, subflujos):
    """Por qué (papel, subflujos) no sirve, o None si está bien."""
    if papel not in PAPELES:
        return "Escribe exactamente «integrante» o «integrador»."
    if any(s not in SUBFLUJOS for s in subflujos):
        return "Los subflujos son S1, S2, S3 y S4 (desde la Etapa 2, también P1 y P2)."
    if len(set(subflujos)) != len(subflujos):
        return "Escribiste un subflujo dos veces."
    if papel == "integrante" and not subflujos:
        return "Un integrante necesita al menos un subflujo."
    return None


def mi_papel(archivo="mi-papel.json", preguntar=input):
    """Tu papel y tus subflujos. La primera vez te los pregunta y los guarda en `mi-papel.json`.

    Ese archivo es solo tuyo: el `.gitignore` del equipo lo excluye, así que nadie edita la libreta
    compartida para escribir su papel y no hay conflictos en Git. Para cambiarlo, borra el archivo.
    Devuelve (papel, lista de subflujos).
    """
    ruta = Path(archivo)
    if ruta.exists():
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            papel, subflujos = datos["papel"], list(datos["subflujos"])
            error = _error_de_papel(papel, subflujos)
        except (ValueError, KeyError, TypeError):
            error = "no se pudo leer"
        if error:
            raise ValueError(f"{archivo} no sirve ({error}). Bórralo en el panel de archivos y corre la libreta otra vez.")
        return papel, subflujos
    while True:
        papel = preguntar("Tu papel (integrante o integrador): ").strip().lower()
        if papel in PAPELES:
            break
        print("Escribe exactamente «integrante» o «integrador».")
    while True:
        texto = preguntar("Tu subflujo (S1, S2, S3 o S4, y desde la Etapa 2 también P1 o P2; si tienes más de uno, "
                          "sepáralos con coma; integrador sin subflujo: Enter): ")
        subflujos = [s.strip().upper() for s in texto.replace(";", ",").split(",") if s.strip()]
        error = _error_de_papel(papel, subflujos)
        if error is None:
            break
        print(error)
    ruta.write_text(json.dumps({"papel": papel, "subflujos": subflujos}, indent=2), encoding="utf-8")
    print(f"Guardé tu papel en {archivo} (solo en tu equipo; no se sube a Git). Para cambiarlo, borra ese archivo.")
    return papel, subflujos


def _flujos(cliente):
    salida, cursor = {}, None
    while True:
        r = cliente.get("/workflows", params={"limit": 250, **({"cursor": cursor} if cursor else {})}).json()
        salida.update({w["name"]: w["id"] for w in r["data"]})
        cursor = r.get("nextCursor")
        if not cursor:
            return salida


def _tablas(cliente):
    """{nombre: id} de las Data Tables de tu n8n."""
    salida, cursor = {}, None
    while True:
        r = cliente.get("/data-tables", params={"limit": 250, **({"cursor": cursor} if cursor else {})})
        if r.status_code == 403:
            raise ValueError("Tu llave de n8n no puede leer Data Tables. Abre la página de estado y conecta tu n8n "
                             "otra vez (correo y contraseña): la llave se renueva.")
        r.raise_for_status()
        salida.update({t["name"]: t["id"] for t in r.json()["data"]})
        cursor = r.json().get("nextCursor")
        if not cursor:
            return salida


def _refs_tabla(wf):
    return [n["parameters"]["dataTableId"] for n in wf["nodes"]
            if n["type"] == TABLA and isinstance(n["parameters"].get("dataTableId"), dict)]


def _tablas_por_id(wf, tablas):
    """Apunta cada nodo de Data Table a la tabla de esta instancia que tiene su nombre."""
    for ref in _refs_tabla(wf):
        nombre = ref.get("cachedResultName")
        if nombre not in tablas:
            raise ValueError(f"«{wf['name']}» usa la Data Table «{nombre}», que no existe en tu n8n. Abre la página de "
                             "estado y conecta tu n8n otra vez: el alta crea las tablas del curso.")
        ref.update({"mode": "list", "value": tablas[nombre]})


def _es_principal(wf):
    return any(n["type"] == LLAMADA for n in wf["nodes"])


def _es_flujo_de_error(wf):
    return any(n["type"] == ERROR_TRIGGER for n in wf["nodes"])


def _limpio(wf, por_id, tablas_por_id=None):
    """Lo que va al repositorio: sin ids de esta instancia. Las credenciales se resuelven por nombre y el
    flujo de error y las Data Tables se guardan con su nombre."""
    wf = {k: wf[k] for k in CAMPOS}
    for n in wf["nodes"]:
        for ref in n.get("credentials", {}).values():
            ref["id"] = None
    for ref in _refs_tabla(wf):
        nombre = (tablas_por_id or {}).get(ref.get("value")) or ref.get("cachedResultName")
        ref.clear()
        ref.update({"__rl": True, "mode": "list", "value": "", "cachedResultName": nombre})
    error = (wf.get("settings") or {}).get("errorWorkflow")
    if error in por_id:
        wf["settings"]["errorWorkflow"] = por_id[error]
    return wf


def _flujo_de_error_por_id(wf, ids):
    """Cambia el nombre del flujo de error (como viene del repositorio) por su id en esta instancia.
    Si ese flujo no está, el flujo se importa sin flujo de error y se avisa (no se detiene la importación:
    a un integrante no le hace falta el flujo de error del equipo para probar su subflujo)."""
    error = (wf.get("settings") or {}).get("errorWorkflow")
    if error and error not in ids.values():
        if error not in ids:
            wf["settings"]["errorWorkflow"] = ""
            return f"aviso     «{wf['name']}» usa como flujo de error «{error}», que no está en la carpeta ni en tu n8n: se importa sin él"
        wf["settings"]["errorWorkflow"] = ids[error]


def exportar(cliente, carpeta, nombres):
    """Escribe en `carpeta` un archivo por flujo. `nombres`: {nombre del flujo en n8n: archivo}."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ids = _flujos(cliente)
    por_id = {v: k for k, v in ids.items()}
    hechos, tablas_por_id = [], None
    for nombre, archivo in nombres.items():
        if nombre not in ids:
            raise ValueError(f"No encuentro en tu n8n un flujo llamado «{nombre}». ¿Le cambiaste el nombre?")
        wf = cliente.get(f"/workflows/{ids[nombre]}").json()
        if _refs_tabla(wf) and tablas_por_id is None:
            tablas_por_id = {v: k for k, v in _tablas(cliente).items()}
        wf = _limpio(wf, por_id, tablas_por_id)
        (carpeta / archivo).write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hechos.append(f"{nombre} → {carpeta.name}/{archivo}")
        # El flujo de error que este flujo nombra viaja con él (flujos/error.json): sin él, quien importe el
        # principal en otro n8n no tendría a quién avisar
        error = wf["settings"].get("errorWorkflow")
        if error and error in ids and error not in nombres:
            otro = _limpio(cliente.get(f"/workflows/{ids[error]}").json(), por_id)
            (carpeta / "error.json").write_text(json.dumps(otro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            hechos.append(f"{error} → {carpeta.name}/error.json  (su flujo de error)")
    return hechos


def _guardar(cliente, wf, ids):
    """Crea el flujo o, si ya hay uno con ese nombre, lo reemplaza (no se duplica)."""
    if wf["name"] in ids:
        wid = ids[wf["name"]]
        # al reemplazar, n8n conserva los ajustes que no vienen en el archivo: sin esto, un flujo de error
        # que se quitó seguiría asignado (probado el 12 oct)
        wf = {**wf, "settings": {"errorWorkflow": "", **(wf.get("settings") or {})}}
        r = cliente.put(f"/workflows/{wid}", json=wf)
        if r.status_code == 400 and "no trigger" in r.text:
            # estaba publicado y la versión nueva no tiene disparador automático: se despublica y se reemplaza
            cliente.post(f"/workflows/{wid}/deactivate")
            r = cliente.put(f"/workflows/{wid}", json=wf)
    else:
        r = cliente.post("/workflows", json=wf)
    if r.status_code >= 400:
        raise ValueError(f"n8n no aceptó «{wf['name']}»: {r.text[:200]}")
    return r.json()["id"]


def importar(cliente, carpeta, excepto=()):
    """Importa todos los flujos de `carpeta`: primero los flujos de error y los subflujos (y los publica),
    luego los principales, reconectando cada llamada y el flujo de error por su nombre.

    `excepto`: nombres de flujos que **no** se reemplazan si ya existen en tu n8n (lo que tú estás
    construyendo: así traer los cambios de tus compañeros no borra tu trabajo sin exportar)."""
    archivos = sorted(Path(carpeta).glob("*.json"))
    ids, informe = _flujos(cliente), []
    flujos = []
    for f in archivos:
        wf = json.loads(f.read_text(encoding="utf-8"))
        if wf["name"] in excepto and wf["name"] in ids:
            informe.append(f"se queda  {wf['name']}  (es tuyo y ya está en tu n8n: no se reemplaza)")
        else:
            flujos.append(wf)
    flujos.sort(key=lambda w: not _es_flujo_de_error(w))   # primero los flujos de error: los demás los nombran
    if any(_refs_tabla(w) for w in flujos):
        tablas = _tablas(cliente)
        for wf in flujos:
            _tablas_por_id(wf, tablas)
    for wf in (w for w in flujos if not _es_principal(w)):
        aviso = _flujo_de_error_por_id(wf, ids)
        informe += [aviso] if aviso else []
        ids[wf["name"]] = wid = _guardar(cliente, wf, ids)
        publicado = cliente.post(f"/workflows/{wid}/activate").status_code < 300
        informe.append(f"subflujo  {wf['name']}" + ("" if publicado else "  (no se pudo publicar)"))
    for wf in (w for w in flujos if _es_principal(w)):
        for n in wf["nodes"]:
            if n["type"] == LLAMADA:
                sub = n["parameters"]["workflowId"]["cachedResultName"]
                if sub not in ids:
                    raise ValueError(f"«{wf['name']}» llama a «{sub}», que no está en la carpeta ni en tu n8n. "
                                     "¿Ya subió su dueño el archivo al repositorio?")
                n["parameters"]["workflowId"]["value"] = ids[sub]
        aviso = _flujo_de_error_por_id(wf, ids)
        informe += [aviso] if aviso else []
        ids[wf["name"]] = _guardar(cliente, wf, ids)
        informe.append(f"principal {wf['name']}  (llamadas reconectadas por nombre)")
    return informe


def verificar(cliente):
    """Revisa cada llamada a un subflujo (¿el id existe en esta instancia y es del subflujo que dice el
    nombre?), que el flujo de error elegido en Settings exista y que cada Data Table apunte a la suya."""
    ids = _flujos(cliente)
    por_id = {v: k for k, v in ids.items()}
    problemas, revisadas, tablas = [], 0, None
    for nombre, wid in ids.items():
        wf = cliente.get(f"/workflows/{wid}").json()
        for ref in _refs_tabla(wf):
            revisadas += 1
            tablas = _tablas(cliente) if tablas is None else tablas
            real = {v: k for k, v in tablas.items()}.get(ref.get("value"))
            if real is None or real != ref.get("cachedResultName", real):
                problemas.append(f"«{nombre}» → su Data Table «{ref.get('cachedResultName')}» apunta a "
                                 f"{'una tabla que no existe aquí' if real is None else f'«{real}»'}")
        error = (wf.get("settings") or {}).get("errorWorkflow")
        if error:
            revisadas += 1
            if error not in por_id:
                problemas.append(f"«{nombre}» → su flujo de error apunta a un flujo que no existe aquí")
        for n in wf["nodes"]:
            if n["type"] != LLAMADA:
                continue
            revisadas += 1
            ref = n["parameters"]["workflowId"]
            real = por_id.get(ref["value"])
            if real != ref.get("cachedResultName"):
                problemas.append(f"«{nombre}» → nodo «{n['name']}» dice «{ref.get('cachedResultName')}» pero apunta a "
                                 f"{'un flujo que no existe aquí' if real is None else f'«{real}»'}")
    return revisadas, problemas

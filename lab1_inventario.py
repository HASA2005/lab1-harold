import os
import getpass
from datetime import datetime

import yaml
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)


COMANDOS = {
    "mikrotik_routeros": {
        "identidad": "/system identity print",
        "recursos": "/system resource print",
        "interfaces": "/ip address print terse",
        "ruta_default": "/ip route print terse where dst-address=0.0.0.0/0",
    }
}


def cargar_inventario():
    with open("inventario.yaml", "r", encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo)

    return datos["equipos"]


def obtener_password(nombre_equipo):
    variable = "LAB_PASS_" + nombre_equipo.upper().replace("-", "_")

    password = os.getenv(variable)

    if password:
        return password

    return getpass.getpass(
        f"Contraseña para {nombre_equipo}: "
    )


def extraer_valor(texto, clave):
    for linea in texto.splitlines():
        linea = linea.strip()

        if linea.startswith(f"{clave}:"):
            return linea.split(":", 1)[1].strip()

    return None


def parsear_terse(texto):
    registros = []

    for linea in texto.splitlines():
        linea = linea.strip()

        if not linea:
            continue

        registro = {}

        for parte in linea.split():
            if "=" in parte:
                clave, valor = parte.split("=", 1)
                registro[clave] = valor

        if registro:
            registros.append(registro)

    return registros


def parsear_routeros(salidas):
    interfaces_crudas = parsear_terse(
        salidas["interfaces"]
    )

    rutas_crudas = parsear_terse(
        salidas["ruta_default"]
    )

    interfaces = []

    for interfaz in interfaces_crudas:
        interfaces.append({
            "interfaz": interfaz.get("interface"),
            "ip": interfaz.get("address"),
        })

    ruta_default = {}

    if rutas_crudas:
        ruta = rutas_crudas[0]

        ruta_default = {
            "destino": ruta.get("dst-address"),
            "gateway": ruta.get("gateway"),
        }

    return {
        "nombre": extraer_valor(
            salidas["identidad"],
            "name",
        ),
        "uptime": extraer_valor(
            salidas["recursos"],
            "uptime",
        ),
        "interfaces": interfaces,
        "ruta_default": ruta_default,
    }


def conectar_equipo(equipo):
    nombre = equipo["nombre"]

    password = obtener_password(nombre)

    os.makedirs("logs", exist_ok=True)

    dispositivo = {
        "device_type": equipo["device_type"],
        "host": equipo["host"],
        "username": equipo["usuario"],
        "password": password,
        "session_log": f"logs/{nombre}.log",
    }

    fecha_hora = datetime.now().isoformat(
        timespec="seconds"
    )

    try:
        with ConnectHandler(**dispositivo) as conexion:
            print(f"[OK] Conectado a {nombre}")

            comandos = COMANDOS[
                equipo["device_type"]
            ]

            salidas = {}

            for clave, comando in comandos.items():
                salidas[clave] = conexion.send_command(
                    comando
                )

            datos = parsear_routeros(salidas)

            return {
                "equipo": nombre,
                "ip": equipo["host"],
                "fecha_hora": fecha_hora,
                "estado": "ok",
                "datos": datos,
            }

    except NetmikoTimeoutException:
        mensaje = (
            f"Timeout al conectar con {nombre}"
        )
        print(f"[ERROR] {mensaje}")

        return {
            "equipo": nombre,
            "ip": equipo["host"],
            "fecha_hora": fecha_hora,
            "estado": mensaje,
            "datos": {},
        }

    except NetmikoAuthenticationException:
        mensaje = (
            f"Credenciales incorrectas para {nombre}"
        )
        print(f"[ERROR] {mensaje}")

        return {
            "equipo": nombre,
            "ip": equipo["host"],
            "fecha_hora": fecha_hora,
            "estado": mensaje,
            "datos": {},
        }

    except Exception as error:
        mensaje = str(error)

        print(
            f"[ERROR] {nombre}: {mensaje}"
        )

        return {
            "equipo": nombre,
            "ip": equipo["host"],
            "fecha_hora": fecha_hora,
            "estado": mensaje,
            "datos": {},
        }


def main():
    equipos = cargar_inventario()
    resultados = []

    for equipo in equipos:
        resultado = conectar_equipo(equipo)
        resultados.append(resultado)

    print(resultados)


if __name__ == "__main__":
    main()

import os
import getpass
import yaml

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException
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


def conectar_equipo(equipo):
    nombre = equipo["nombre"]

    password = obtener_password(nombre)

    dispositivo = {
        "device_type": equipo["device_type"],
        "host": equipo["host"],
        "username": equipo["usuario"],
        "password": password,
        "session_log": f"logs/{nombre}.log"
    }

    try:
        with ConnectHandler(**dispositivo) as conexion:
            print(f"[OK] Conectado a {nombre}")

            salida = conexion.send_command(
                "/system identity print"
            )

            print(salida)

    except NetmikoTimeoutException:
        print(f"[ERROR] Timeout al conectar con {nombre}")

    except NetmikoAuthenticationException:
        print(f"[ERROR] Credenciales incorrectas para {nombre}")

    except Exception as error:
        print(f"[ERROR] {nombre}: {error}")


def main():
    equipos = cargar_inventario()

    for equipo in equipos:
        conectar_equipo(equipo)


if __name__ == "__main__":
    main()

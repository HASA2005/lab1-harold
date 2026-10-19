import os
import getpass
import json
import argparse
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

def asegurar_loopback(conexion, numero):
    if numero < 1 or numero > 254:
        raise ValueError(
            "El numero de lista debe estar entre 1 y 254"
        )

    interfaz = f"lo-ssh-{numero}"
    direccion_ip = f"10.253.0.{numero}/32"
    comentario = "Harold Saborio - Lab1"

    cambios = []

    salida_bridge = conexion.send_command(
        f"/interface bridge print terse where name={interfaz}"
    )

    if not salida_bridge.strip():
        conexion.send_command(
            f'/interface bridge add '
            f'name={interfaz} '
            f'comment="{comentario}"'
        )

        cambios.append("bridge creado")

    salida_ip = conexion.send_command(
        f"/ip address print terse where interface={interfaz}"
    )

    if f"address={direccion_ip}" not in salida_ip:
        conexion.send_command(
            f'/ip address add '
            f'address={direccion_ip} '
            f'interface={interfaz} '
            f'comment="{comentario}"'
        )

        cambios.append("IP agregada")

    verificar_bridge = conexion.send_command(
        f"/interface bridge print terse where name={interfaz}"
    )

    verificar_ip = conexion.send_command(
        f"/ip address print terse where interface={interfaz}"
    )

    verificado = (
        bool(verificar_bridge.strip())
        and f"address={direccion_ip}" in verificar_ip
    )

    if cambios:
        print(
            f"[CAMBIO] {interfaz}: "
            + ", ".join(cambios)
        )
    else:
        print(
            f"[SIN CAMBIOS] {interfaz} ya existe correctamente"
        )

    return {
        "interfaz": interfaz,
        "ip": direccion_ip,
        "cambios": cambios,
        "verificado": verificado,
    }

def limpiar_loopback(conexion, numero):
    if numero < 1 or numero > 254:
        raise ValueError(
            "El numero de lista debe estar entre 1 y 254"
        )

    interfaz = f"lo-ssh-{numero}"

    salida_ip = conexion.send_command(
        f"/ip address print terse where interface={interfaz}"
    )

    if salida_ip.strip():
        conexion.send_command(
            f"/ip address remove [find interface={interfaz}]"
        )
        print(
            f"[LIMPIAR] IP eliminada de {interfaz}"
        )

    salida_bridge = conexion.send_command(
        f"/interface bridge print terse where name={interfaz}"
    )

    if salida_bridge.strip():
        conexion.send_command(
            f"/interface bridge remove [find name={interfaz}]"
        )
        print(
            f"[LIMPIAR] Bridge {interfaz} eliminado"
        )
    else:
        print(
            f"[LIMPIAR] {interfaz} no existe"
        )

    return {
        "interfaz": interfaz,
        "limpiado": True,
    }

def conectar_equipo(equipo, numero=None, limpiar=False):
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

            configuracion = None

            if (
                equipo.get("rol") == "escritura"
                and numero is not None
            ):
                if limpiar:
                    configuracion = limpiar_loopback(
                        conexion,
                        numero
                    )
                else:
                    configuracion = asegurar_loopback(
                        conexion,
                        numero
                    )

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
        "configuracion": configuracion,
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
        "configuracion": configuracion,
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
        "configuracion": configuracion,
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
        "configuracion": configuracion,
        }


def mostrar_resumen(resultados):
    print("\nRESUMEN DE ESTADO")
    print("-" * 85)

    print(
        f"{'Equipo':<15}"
        f"{'IP':<18}"
        f"{'Estado':<25}"
        f"{'Interfaces':<12}"
        f"{'Gateway':<15}"
    )

    print("-" * 85)

    for resultado in resultados:
        datos = resultado.get("datos", {})

        interfaces = datos.get("interfaces", [])
        cantidad_interfaces = len(interfaces)

        ruta_default = datos.get("ruta_default", {})
        gateway = ruta_default.get("gateway") or "-"

        print(
            f"{resultado['equipo']:<15}"
            f"{resultado['ip']:<18}"
            f"{resultado['estado']:<25}"
            f"{cantidad_interfaces:<12}"
            f"{gateway:<15}"
        )

    print("-" * 85)

def main():
    parser = argparse.ArgumentParser(
        description="Laboratorio 1 - Netmiko"
    )

    parser.add_argument(
        "-n",
        "--numero",
        type=int,
        help="Numero de lista N para R6"
    )

    parser.add_argument(
        "--limpiar",
        action="store_true",
        help="Elimina solo los objetos creados por este estudiante"
    )

    args = parser.parse_args()

    equipos = cargar_inventario()
    resultados = []

    for equipo in equipos:
        resultado = conectar_equipo(
            equipo,
            args.numero,
            args.limpiar
        )

        resultados.append(resultado)

    with open(
        "reporte_estado.json",
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            resultados,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    print(
        "\nReporte generado: reporte_estado.json"
    )

    mostrar_resumen(resultados)


if __name__ == "__main__":
    main()

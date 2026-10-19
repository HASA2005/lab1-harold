# Laboratorio 1 - Redes Programables

## Inventario, Estado y Configuración Segura con Python + SSH

**Curso:** ITIEL-13 - Redes Programables  
**Estudiante:** Harold Saborío  
**Periodo:** III - 2026

## Descripción

Este proyecto utiliza Python, Netmiko y SSH para administrar equipos de red definidos en un inventario YAML.

El script permite:

- Leer equipos desde `inventario.yaml`.
- Obtener credenciales de forma segura.
- Conectarse por SSH utilizando Netmiko.
- Consultar el estado del MikroTik.
- Convertir la información obtenida a datos estructurados.
- Generar un reporte JSON.
- Mostrar un resumen en consola.
- Crear una interfaz loopback de forma idempotente.
- Eliminar únicamente los objetos creados por el estudiante mediante `--limpiar`.

## Requisitos

- Python 3
- Netmiko
- PyYAML

## Instalación

Crear el entorno virtual:

```bash
python3 -m venv .venv

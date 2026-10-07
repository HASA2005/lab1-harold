import yaml


def cargar_inventario():
    with open("inventario.yaml", "r", encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo)

    return datos["equipos"]


def main():
    equipos = cargar_inventario()

    for equipo in equipos:
        print(equipo)


if __name__ == "__main__":
    main()

from ClashLib.Clash import Clash
import sys

if __name__ == "__main__":
    # obtener argumentos
    args = sys.argv[1:]
    if len(args) == 0:
        print("Uso: python run.py <player> (1 o 2)")
        sys.exit(1)
    else:
        player = args[0]
        if player not in ["1", "2"]:
            print("Jugador inválido. Use '1' o '2'.")
            sys.exit(1)
        print(f"Jugador: {player}")
        game = Clash(player)
        game.run()
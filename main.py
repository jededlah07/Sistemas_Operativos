import tkinter as tk
from ventana import Ventana


def main():
    raiz = tk.Tk()
    raiz.resizable(False, False)
    Ventana(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
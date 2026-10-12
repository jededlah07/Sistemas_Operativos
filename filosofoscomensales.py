import math
import queue
import random
import threading
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

PENSANDO = "pensando"
HAMBRIENTO = "hambriento"
COMIENDO = "comiendo"

COLORES = {
    PENSANDO: "#6fa8dc",
    HAMBRIENTO: "#f6b26b",
    COMIENDO: "#93c47d",
}

MINIMO = 2
MAXIMO = 12
CANTIDAD_INICIAL = 5

AVISO_HAMBRE = 5
PELIGRO_HAMBRE = 10
PAUSA_DEADLOCK = 1.0
MAX_LINEAS_LOG = 500
FONDO_NORMAL = "white"
FONDO_DEADLOCK = "#fde0e0"


class Mesa:
    def __init__(self, cantidad, modo_deadlock=False):
        self.cantidad = cantidad
        self.modo_deadlock = modo_deadlock
        self.tenedores = [threading.Lock() for _ in range(cantidad)]
        self.asientos = threading.Semaphore(cantidad - 1)
        self.barrera = threading.Barrier(cantidad)
        self.estado = [PENSANDO] * cantidad
        self.comidas = [0] * cantidad
        self.tenedor_ocupado = [False] * cantidad
        self.espera = [0.0] * cantidad
        self.espera_maxima = [0.0] * cantidad
        self.candado_datos = threading.Lock()
        self.mensajes = queue.Queue()
        self.activo = True
        self.corriendo = threading.Event()
        self.corriendo.set()
        self.velocidad = 1.0
        self.ultimo_tick = time.monotonic()

    def pausar(self):
        self.corriendo.clear()

    def reanudar(self):
        self.corriendo.set()

    def detener(self):
        self.activo = False
        self.corriendo.set()
        self.barrera.abort()

    def esperar(self, segundos):
        restante = segundos
        while restante > 0 and self.activo:
            self.corriendo.wait()
            time.sleep(0.05)
            restante -= 0.05 * self.velocidad

    def registrar(self, mensaje, etiqueta="normal"):
        self.mensajes.put((time.strftime("%H:%M:%S"), mensaje, etiqueta))

    def cambiar_estado(self, numero, nuevo_estado):
        with self.candado_datos:
            self.estado[numero] = nuevo_estado
            if nuevo_estado != HAMBRIENTO:
                self.espera[numero] = 0.0

    def marcar_tenedor(self, numero_tenedor, ocupado):
        with self.candado_datos:
            self.tenedor_ocupado[numero_tenedor] = ocupado

    def sumar_comida(self, numero):
        with self.candado_datos:
            self.comidas[numero] += 1

    def tomar_tenedor(self, filosofo, tenedor):
        while self.activo:
            if self.tenedores[tenedor].acquire(timeout=0.1):
                self.marcar_tenedor(tenedor, True)
                self.registrar(f"Filosofo {filosofo + 1} toma el tenedor {tenedor + 1}")
                return True
        return False

    def soltar_tenedor(self, tenedor):
        self.marcar_tenedor(tenedor, False)
        self.tenedores[tenedor].release()

    def pedir_asiento(self):
        while self.activo:
            if self.asientos.acquire(timeout=0.1):
                return True
        return False

    def esperar_a_los_demas(self):
        try:
            self.barrera.wait()
        except threading.BrokenBarrierError:
            return False
        return True

    def actualizar_esperas(self):
        ahora = time.monotonic()
        paso = ahora - self.ultimo_tick
        self.ultimo_tick = ahora
        if not self.activo or not self.corriendo.is_set():
            return
        with self.candado_datos:
            for i in range(self.cantidad):
                if self.estado[i] == HAMBRIENTO:
                    self.espera[i] += paso * self.velocidad
                    self.espera_maxima[i] = max(self.espera_maxima[i], self.espera[i])

    def hay_bloqueo(self):
        with self.candado_datos:
            return (self.activo
                    and all(e == HAMBRIENTO for e in self.estado)
                    and all(self.tenedor_ocupado))

    def leer_datos(self):
        with self.candado_datos:
            return (list(self.estado), list(self.comidas),
                    list(self.tenedor_ocupado), list(self.espera),
                    list(self.espera_maxima))


class Filosofo(threading.Thread):
    def __init__(self, numero, mesa):
        super().__init__(daemon=True)
        self.numero = numero
        self.nombre = f"Filosofo {numero + 1}"
        self.mesa = mesa
        self.izquierdo = numero
        self.derecho = (numero + 1) % mesa.cantidad
        self.primera_vez = True

    def pensar(self):
        self.mesa.cambiar_estado(self.numero, PENSANDO)
        self.mesa.registrar(f"{self.nombre} empieza a pensar")
        self.mesa.esperar(random.uniform(1, 3))

    def tener_hambre(self):
        self.mesa.cambiar_estado(self.numero, HAMBRIENTO)
        self.mesa.registrar(f"{self.nombre} tiene hambre y busca tenedores", "hambre")

    def comer(self):
        self.mesa.cambiar_estado(self.numero, COMIENDO)
        self.mesa.sumar_comida(self.numero)
        self.mesa.registrar(f"{self.nombre} esta comiendo", "comer")
        self.mesa.esperar(random.uniform(1, 2))
        if self.mesa.activo:
            self.mesa.registrar(f"{self.nombre} termina de comer y suelta los tenedores")

    def usar_tenedores(self, primero, segundo, pausa):
        mesa = self.mesa
        if not mesa.tomar_tenedor(self.numero, primero):
            return
        try:
            if pausa:
                mesa.esperar(pausa)
            if not mesa.tomar_tenedor(self.numero, segundo):
                return
            try:
                self.comer()
            finally:
                mesa.soltar_tenedor(segundo)
        finally:
            mesa.soltar_tenedor(primero)

    def comer_seguro(self):
        if not self.mesa.pedir_asiento():
            return
        try:
            primero = min(self.izquierdo, self.derecho)
            segundo = max(self.izquierdo, self.derecho)
            self.usar_tenedores(primero, segundo, 0)
        finally:
            self.mesa.asientos.release()

    def comer_sin_proteccion(self):
        self.usar_tenedores(self.izquierdo, self.derecho, PAUSA_DEADLOCK)

    def sincronizar_primera_vez(self):
        if not self.primera_vez:
            return True
        self.primera_vez = False
        return self.mesa.esperar_a_los_demas()

    def run(self):
        while self.mesa.activo:
            self.pensar()
            if not self.mesa.activo:
                break
            if self.mesa.modo_deadlock:
                if not self.sincronizar_primera_vez():
                    break
                self.tener_hambre()
                self.comer_sin_proteccion()
            else:
                self.tener_hambre()
                self.comer_seguro()


class Ventana:
    def __init__(self, raiz):
        self.raiz = raiz
        self.mesa = None
        self.filosofos = []
        self.circulos = []
        self.textos = []
        self.lineas_tenedores = []
        self.ticks_bloqueo = 0
        self.deadlock_avisado = False

        self.centro = 270
        self.radio_mesa = 130
        self.radio_filosofos = 195

        self.raiz.title("Filosofos Comensales")
        self.raiz.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.lienzo = tk.Canvas(raiz, width=540, height=540, bg=FONDO_NORMAL)
        self.lienzo.pack(side="left", padx=10, pady=10)

        self.crear_panel()
        self.iniciar()
        self.actualizar_interfaz()

    def crear_panel(self):
        panel = tk.Frame(self.raiz)
        panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        fila = tk.Frame(panel)
        fila.pack(anchor="w")
        tk.Label(fila, text="Cantidad de filosofos",
                 font=("Arial", 10, "bold")).pack(side="left")
        self.cantidad = tk.IntVar(value=CANTIDAD_INICIAL)
        tk.Spinbox(fila, from_=MINIMO, to=MAXIMO, width=5,
                   textvariable=self.cantidad).pack(side="left", padx=8)

        botones = tk.Frame(panel)
        botones.pack(anchor="w", pady=8)
        tk.Button(botones, text="Reiniciar / Aplicar",
                  command=self.iniciar).pack(side="left", padx=(0, 4))
        self.boton_pausa = tk.Button(botones, text="Pausar", width=9,
                                     command=self.pausar)
        self.boton_pausa.pack(side="left", padx=4)
        tk.Button(botones, text="Detener", width=9,
                  command=self.detener).pack(side="left", padx=4)

        fila_velocidad = tk.Frame(panel)
        fila_velocidad.pack(anchor="w")
        tk.Label(fila_velocidad, text="Velocidad",
                 font=("Arial", 10, "bold")).pack(side="left")
        self.escala = tk.Scale(fila_velocidad, from_=0.25, to=4.0,
                               resolution=0.25, orient="horizontal",
                               length=200, command=self.cambiar_velocidad)
        self.escala.set(1.0)
        self.escala.pack(side="left", padx=8)

        self.modo_deadlock = tk.BooleanVar(value=False)
        tk.Checkbutton(panel, text="Modo Deadlock (sin proteccion)",
                       variable=self.modo_deadlock,
                       command=self.iniciar).pack(anchor="w", pady=(6, 0))

        self.etiqueta_modo = tk.Label(panel, text="", font=("Arial", 10, "bold"))
        self.etiqueta_modo.pack(anchor="w")
        self.etiqueta_estado = tk.Label(panel, text="", font=("Arial", 10))
        self.etiqueta_estado.pack(anchor="w")
        self.etiqueta_hambre = tk.Label(panel, text="", font=("Arial", 10))
        self.etiqueta_hambre.pack(anchor="w")
        self.etiqueta_alerta = tk.Label(panel, text="", fg="red",
                                        font=("Arial", 10, "bold"))
        self.etiqueta_alerta.pack(anchor="w")

        leyenda = tk.Frame(panel)
        leyenda.pack(anchor="w", pady=4)
        for estado, color in COLORES.items():
            tk.Label(leyenda, bg=color, width=2).pack(side="left", padx=(0, 3))
            tk.Label(leyenda, text=estado).pack(side="left", padx=(0, 8))
        tk.Label(panel, text=f"Borde dorado: hambre > {AVISO_HAMBRE}s   "
                             f"Borde rojo: hambre > {PELIGRO_HAMBRE}s",
                 font=("Arial", 8)).pack(anchor="w")

        tk.Label(panel, text="Registro de eventos",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(8, 2))
        self.log = ScrolledText(panel, width=52, height=16, wrap="word",
                                font=("Courier", 9), state="disabled")
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("normal", foreground="black")
        self.log.tag_config("hambre", foreground="#b45f06")
        self.log.tag_config("comer", foreground="#38761d")
        self.log.tag_config("sistema", foreground="gray")
        self.log.tag_config("alerta", foreground="red",
                            font=("Courier", 9, "bold"))

    def leer_cantidad(self):
        try:
            cantidad = int(self.cantidad.get())
        except (tk.TclError, ValueError):
            cantidad = CANTIDAD_INICIAL
        cantidad = max(MINIMO, min(MAXIMO, cantidad))
        self.cantidad.set(cantidad)
        return cantidad

    def iniciar(self):
        cantidad = self.leer_cantidad()
        self.detener()

        modo_deadlock = self.modo_deadlock.get()
        self.mesa = Mesa(cantidad, modo_deadlock)
        self.mesa.velocidad = float(self.escala.get())
        self.filosofos = [Filosofo(i, self.mesa) for i in range(cantidad)]
        self.ticks_bloqueo = 0
        self.deadlock_avisado = False

        self.dibujar_mesa()

        nombre_modo = "Modo Deadlock" if modo_deadlock else "Modo Seguro"
        self.agregar_linea(
            f"--- Nueva simulacion: {cantidad} filosofos, {nombre_modo} ---",
            "sistema")
        self.etiqueta_modo.config(
            text=f"Modo: {nombre_modo}",
            fg="red" if modo_deadlock else "#38761d")

        for filosofo in self.filosofos:
            filosofo.start()

        self.boton_pausa.config(text="Pausar", state="normal")
        self.etiqueta_estado.config(text="Estado: ejecutando")

    def pausar(self):
        if self.mesa is None or not self.mesa.activo:
            return
        if self.mesa.corriendo.is_set():
            self.mesa.pausar()
            self.boton_pausa.config(text="Reanudar")
            self.etiqueta_estado.config(text="Estado: en pausa")
            self.agregar_linea("--- Simulacion en pausa ---", "sistema")
        else:
            self.mesa.reanudar()
            self.boton_pausa.config(text="Pausar")
            self.etiqueta_estado.config(text="Estado: ejecutando")
            self.agregar_linea("--- Simulacion reanudada ---", "sistema")

    def detener(self):
        if self.mesa is None or not self.mesa.activo:
            return
        self.mesa.detener()
        for filosofo in self.filosofos:
            filosofo.join(timeout=1)
        self.mostrar_log()
        self.agregar_linea("--- Simulacion detenida ---", "sistema")
        self.boton_pausa.config(text="Pausar", state="disabled")
        self.etiqueta_estado.config(text="Estado: detenido")

    def cambiar_velocidad(self, valor):
        if self.mesa is not None:
            self.mesa.velocidad = float(valor)

    def agregar_linea(self, texto, etiqueta="normal"):
        self.log.config(state="normal")
        self.log.insert("end", texto + "\n", etiqueta)
        lineas = int(self.log.index("end-1c").split(".")[0])
        if lineas > MAX_LINEAS_LOG:
            self.log.delete("1.0", f"{lineas - MAX_LINEAS_LOG + 1}.0")
        self.log.see("end")
        self.log.config(state="disabled")

    def mostrar_log(self):
        while True:
            try:
                hora, mensaje, etiqueta = self.mesa.mensajes.get_nowait()
            except queue.Empty:
                break
            self.agregar_linea(f"[{hora}] {mensaje}", etiqueta)

    def posicion(self, indice, radio, desfase=0.0):
        cantidad = self.mesa.cantidad
        angulo = 2 * math.pi * (indice + desfase) / cantidad - math.pi / 2
        x = self.centro + radio * math.cos(angulo)
        y = self.centro + radio * math.sin(angulo)
        return x, y

    def dibujar_mesa(self):
        self.lienzo.delete("all")
        self.circulos = []
        self.textos = []
        self.lineas_tenedores = []

        cantidad = self.mesa.cantidad
        c = self.centro
        r = self.radio_mesa
        self.lienzo.create_oval(c - r, c - r, c + r, c + r,
                                fill="#e6d3b3", outline="#8b6b3d", width=3)

        for i in range(cantidad):
            x1, y1 = self.posicion(i, self.radio_mesa - 40, 0.5)
            x2, y2 = self.posicion(i, self.radio_mesa - 5, 0.5)
            linea = self.lienzo.create_line(x1, y1, x2, y2,
                                            width=5, fill="gray")
            self.lineas_tenedores.append(linea)
            xt, yt = self.posicion(i, self.radio_mesa + 14, 0.5)
            self.lienzo.create_text(xt, yt, text=f"T{i + 1}",
                                    font=("Arial", 8))

        distancia = 2 * self.radio_filosofos * math.sin(math.pi / cantidad)
        tamano = min(40, int(distancia * 0.45))

        for i in range(cantidad):
            x, y = self.posicion(i, self.radio_filosofos)
            circulo = self.lienzo.create_oval(
                x - tamano, y - tamano, x + tamano, y + tamano,
                fill=COLORES[PENSANDO], outline="black", width=2)
            texto = self.lienzo.create_text(x, y, text="",
                                            font=("Arial", 8, "bold"))
            self.circulos.append(circulo)
            self.textos.append(texto)

    def dibujar_estados(self):
        estados, comidas, ocupados, esperas, maximas = self.mesa.leer_datos()

        for i in range(len(estados)):
            if esperas[i] >= PELIGRO_HAMBRE:
                borde, grosor = "red", 4
            elif esperas[i] >= AVISO_HAMBRE:
                borde, grosor = "#7f6000", 3
            else:
                borde, grosor = "black", 2

            self.lienzo.itemconfig(self.circulos[i], fill=COLORES[estados[i]],
                                   outline=borde, width=grosor)
            self.lienzo.itemconfig(
                self.textos[i],
                text=(f"Filosofo {i + 1}\n{estados[i]}\n"
                      f"Comidas: {comidas[i]}\nEspera: {esperas[i]:.1f}s"))

        for i in range(len(ocupados)):
            color = "red" if ocupados[i] else "gray"
            self.lienzo.itemconfig(self.lineas_tenedores[i], fill=color)

        mayor = max(maximas)
        quien = maximas.index(mayor) + 1
        self.etiqueta_hambre.config(
            text=f"Mayor espera: {mayor:.1f}s (Filosofo {quien})")

    def revisar_deadlock(self):
        if self.mesa.hay_bloqueo():
            self.ticks_bloqueo += 1
        else:
            self.ticks_bloqueo = 0

        if self.ticks_bloqueo >= 5:
            if not self.deadlock_avisado:
                self.deadlock_avisado = True
                self.agregar_linea(
                    "DEADLOCK: cada filosofo tiene un tenedor y espera el otro",
                    "alerta")
            self.lienzo.config(bg=FONDO_DEADLOCK)
            self.etiqueta_alerta.config(text="DEADLOCK: la simulacion esta congelada")
        else:
            self.lienzo.config(bg=FONDO_NORMAL)
            self.etiqueta_alerta.config(text="")

    def actualizar_interfaz(self):
        if self.mesa is not None:
            self.mesa.actualizar_esperas()
            self.mostrar_log()
            self.revisar_deadlock()
            self.dibujar_estados()

        self.raiz.after(100, self.actualizar_interfaz)

    def cerrar(self):
        self.detener()
        self.raiz.destroy()


def main():
    raiz = tk.Tk()
    Ventana(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
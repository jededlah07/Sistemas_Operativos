import threading
import time
import tkinter as tk

try:
    import psutil
    PSUTIL = True
except ImportError:
    PSUTIL = False

from estilos import (
    FONDO_PANEL, BORDE_PANEL, BTN_BG, BTN_FG,
    FUENTE_BOLD, FUENTE_METRICA, LOG_SISTEMA,
    METODO_COLORES, COLOR_PENSANDO, COLOR_HAMBRIENTO, COLOR_COMIENDO,
)
from mesa import PENSANDO, HAMBRIENTO, COMIENDO


class PanelMetricas(tk.Frame):
    def __init__(self, padre, **kwargs):
        super().__init__(padre, bg=FONDO_PANEL, **kwargs)
        self.mesa    = None
        self._proceso = psutil.Process() if PSUTIL else None
        self._vars   = {}
        self._construir()


    def _construir(self):
        tk.Label(self, text="Métricas en tiempo real",
                 bg=FONDO_PANEL, fg="#ffffff",
                 font=FUENTE_BOLD).pack(anchor="w", pady=(6, 2), padx=8)

        self._sep()

        filas = [
            ("metodo",      "Método activo"),
            ("tiempo",      "Tiempo corriendo"),
            ("hilos",       "Hilos activos"),
            ("comidas",     "Comidas totales"),
            ("throughput",  "Throughput (com/s)"),
            ("espera_prom", "Espera promedio"),
            ("espera_max",  "Mayor espera"),
            ("cpu",         "CPU del proceso"),
            ("deadlocks",   "Deadlocks detectados"),
        ]

        for clave, etiqueta in filas:
            self._fila(clave, etiqueta)

        self._sep()

        tk.Label(self, text="Distribución de estados",
                 bg=FONDO_PANEL, fg="#aaaaaa",
                 font=FUENTE_METRICA).pack(anchor="w", padx=8, pady=(4, 0))

        self._barra_estados()

    def _sep(self):
        tk.Frame(self, bg=BORDE_PANEL, height=1).pack(
            fill="x", padx=8, pady=4)

    def _fila(self, clave, etiqueta):
        fila = tk.Frame(self, bg=FONDO_PANEL)
        fila.pack(fill="x", padx=8, pady=1)

        tk.Label(fila, text=etiqueta + ":",
                 bg=FONDO_PANEL, fg="#aaaaaa",
                 font=FUENTE_METRICA, width=22,
                 anchor="w").pack(side="left")

        var = tk.StringVar(value="—")
        tk.Label(fila, textvariable=var,
                 bg=FONDO_PANEL, fg="#ffffff",
                 font=FUENTE_METRICA,
                 anchor="w").pack(side="left")

        self._vars[clave] = var

    def _barra_estados(self):
        self._canvas_barra = tk.Canvas(
            self, bg=FONDO_PANEL, height=18,
            highlightthickness=0)
        self._canvas_barra.pack(fill="x", padx=8, pady=(2, 6))

        leyenda = tk.Frame(self, bg=FONDO_PANEL)
        leyenda.pack(anchor="w", padx=8, pady=(0, 6))

        for color, texto in [
            (COLOR_PENSANDO,   "Pensando"),
            (COLOR_HAMBRIENTO, "Hambriento"),
            (COLOR_COMIENDO,   "Comiendo"),
        ]:
            tk.Label(leyenda, bg=color, width=2,
                     relief="flat").pack(side="left", padx=(0, 2))
            tk.Label(leyenda, text=texto,
                     bg=FONDO_PANEL, fg="#aaaaaa",
                     font=FUENTE_METRICA).pack(side="left", padx=(0, 10))


    def set_mesa(self, mesa):
        self.mesa = mesa

    def actualizar(self):
        if self.mesa is None:
            return

        mesa = self.mesa
        estados, comidas, _, esperas, maximas = mesa.leer_datos()

        colores_metodo = METODO_COLORES
        metodo = mesa.metodo
        self._vars["metodo"].set(metodo.capitalize())

        t = mesa.tiempo_corriendo()
        mins, segs = divmod(int(t), 60)
        self._vars["tiempo"].set(f"{mins:02d}:{segs:02d}")

        import threading as _t
        self._vars["hilos"].set(str(_t.active_count()))

        total = sum(comidas)
        self._vars["comidas"].set(str(total))

        self._vars["throughput"].set(f"{mesa.throughput():.2f}")

        self._vars["espera_prom"].set(f"{mesa.espera_promedio():.1f} s")

        if maximas:
            m = max(maximas)
            quien = maximas.index(m) + 1
            self._vars["espera_max"].set(f"{m:.1f} s  (F{quien})")
        else:
            self._vars["espera_max"].set("—")

        if PSUTIL:
            try:
                cpu = self._proceso.cpu_percent(interval=None)
                self._vars["cpu"].set(f"{cpu:.1f} %")
            except Exception:
                self._vars["cpu"].set("—")
        else:
            self._vars["cpu"].set("sin psutil")

        self._vars["deadlocks"].set(str(mesa.deadlocks))

        self._dibujar_barra(estados)

    def _dibujar_barra(self, estados):
        c = self._canvas_barra
        c.delete("all")
        ancho = c.winfo_width()
        if ancho < 2 or not estados:
            return

        n = len(estados)
        conteo = {
            PENSANDO:   estados.count(PENSANDO),
            HAMBRIENTO: estados.count(HAMBRIENTO),
            COMIENDO:   estados.count(COMIENDO),
        }
        colores_estado = {
            PENSANDO:   COLOR_PENSANDO,
            HAMBRIENTO: COLOR_HAMBRIENTO,
            COMIENDO:   COLOR_COMIENDO,
        }

        x = 0
        for estado, color in colores_estado.items():
            proporcion = conteo[estado] / n
            w = int(ancho * proporcion)
            if w > 0:
                c.create_rectangle(x, 0, x + w, 18,
                                   fill=color, outline="")
                if w > 24:
                    c.create_text(x + w // 2, 9,
                                  text=str(conteo[estado]),
                                  fill="#1e1e1e",
                                  font=FUENTE_METRICA)
                x += w

import math
import queue
import random
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from estilos import (
    FONDO_APP, FONDO_PANEL, FONDO_LIENZO, FONDO_DEADLOCK,
    BORDE_PANEL, BORDE_MESA, COLOR_MESA,
    BTN_BG, BTN_FG, BTN_ACTIVE,
    FUENTE_TITULO, FUENTE_LABEL, FUENTE_BOLD, FUENTE_LOG,
    COLOR_PENSANDO, COLOR_HAMBRIENTO, COLOR_COMIENDO,
    COLOR_TENEDOR_LIBRE, COLOR_TENEDOR_OCUPADO,
    BORDE_NORMAL, BORDE_AVISO, BORDE_PELIGRO,
    LOG_NORMAL, LOG_HAMBRE, LOG_COMER, LOG_SISTEMA, LOG_ALERTA,
    METODO_COLORES, AVISO_HAMBRE, PELIGRO_HAMBRE,
    MINIMO, MAXIMO, CANTIDAD_INICIAL, MAX_LINEAS_LOG,
)
from mesa import Mesa, PENSANDO, HAMBRIENTO, COMIENDO
from filosofo import Filosofo
from metricas import PanelMetricas

COLORES_ESTADO = {
    PENSANDO:   COLOR_PENSANDO,
    HAMBRIENTO: COLOR_HAMBRIENTO,
    COMIENDO:   COLOR_COMIENDO,
}

METODOS = ["seguro", "arbitro", "asimetrico", "deadlock"]

ETIQUETAS_METODO = {
    "seguro":     "Semáforo + Orden",
    "arbitro":    "Árbitro (Camarero)",
    "asimetrico": "Asimétrico",
    "deadlock":   "Sin protección",
}


class Ventana:
    def __init__(self, raiz):
        self.raiz      = raiz
        self.mesa      = None
        self.filosofos = []

        self.circulos        = []
        self.textos          = []
        self.lineas_tenedores = []

        self.ticks_bloqueo   = 0
        self.deadlock_avisado = False

        self.centro           = 270
        self.radio_mesa       = 130
        self.radio_filosofos  = 195

        self._configurar_raiz()
        self._construir_ui()
        self.iniciar()
        self._loop()

 
    def _configurar_raiz(self):
        self.raiz.title("Filósofos Comensales")
        self.raiz.configure(bg=FONDO_APP)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)

 
    def _construir_ui(self):
        self.lienzo = tk.Canvas(
            self.raiz, width=540, height=540,
            bg=FONDO_LIENZO, highlightthickness=0)
        self.lienzo.pack(side="left", padx=10, pady=10)

        panel = tk.Frame(self.raiz, bg=FONDO_PANEL)
        panel.pack(side="left", fill="both", expand=True,
                   padx=(0, 10), pady=10)

        self._construir_controles(panel)
        self._construir_log(panel)
        self.panel_metricas = PanelMetricas(panel)
        self.panel_metricas.pack(fill="x")

    def _construir_controles(self, padre):
        sec = tk.Frame(padre, bg=FONDO_PANEL)
        sec.pack(fill="x", padx=8, pady=8)

        tk.Label(sec, text="Filósofos Comensales",
                 bg=FONDO_PANEL, fg="#ffffff",
                 font=FUENTE_TITULO).pack(anchor="w")

        tk.Frame(sec, bg=BORDE_PANEL, height=1).pack(
            fill="x", pady=6)

        fila = tk.Frame(sec, bg=FONDO_PANEL)
        fila.pack(anchor="w", pady=2)
        tk.Label(fila, text="Filósofos:",
                 bg=FONDO_PANEL, fg="#aaaaaa",
                 font=FUENTE_LABEL).pack(side="left")
        self.var_cantidad = tk.IntVar(value=CANTIDAD_INICIAL)
        tk.Spinbox(fila, from_=MINIMO, to=MAXIMO, width=4,
                   textvariable=self.var_cantidad,
                   bg=BTN_BG, fg=BTN_FG,
                   buttonbackground=BTN_BG,
                   relief="flat").pack(side="left", padx=6)

        tk.Label(sec, text="Método:",
                 bg=FONDO_PANEL, fg="#aaaaaa",
                 font=FUENTE_LABEL).pack(anchor="w", pady=(6, 2))

        self.var_metodo = tk.StringVar(value="seguro")
        fila_metodos = tk.Frame(sec, bg=FONDO_PANEL)
        fila_metodos.pack(anchor="w")

        self._botones_metodo = {}
        for m in METODOS:
            color = METODO_COLORES[m]
            b = tk.Button(
                fila_metodos,
                text=ETIQUETAS_METODO[m],
                bg=BTN_BG, fg="#ffffff",
                activebackground=color,
                activeforeground="#ffffff",
                relief="flat", padx=6, pady=3,
                font=FUENTE_METRICA if hasattr(self, '_') else ("Segoe UI", 9),
                command=lambda met=m: self._cambiar_metodo(met),
            )
            b.pack(side="left", padx=(0, 4), pady=2)
            self._botones_metodo[m] = b

        self.lbl_metodo = tk.Label(
            sec, text="", bg=FONDO_PANEL,
            fg="#ffffff", font=FUENTE_BOLD)
        self.lbl_metodo.pack(anchor="w", pady=(4, 0))

        tk.Frame(sec, bg=BORDE_PANEL, height=1).pack(
            fill="x", pady=6)

        fila_vel = tk.Frame(sec, bg=FONDO_PANEL)
        fila_vel.pack(anchor="w")
        tk.Label(fila_vel, text="Velocidad:",
                 bg=FONDO_PANEL, fg="#aaaaaa",
                 font=FUENTE_LABEL).pack(side="left")
        self.escala = tk.Scale(
            fila_vel, from_=0.25, to=4.0,
            resolution=0.25, orient="horizontal",
            length=160, bg=FONDO_PANEL,
            fg="#ffffff", highlightthickness=0,
            troughcolor=BTN_BG,
            command=self._cambiar_velocidad)
        self.escala.set(1.0)
        self.escala.pack(side="left", padx=6)

        fila_btn = tk.Frame(sec, bg=FONDO_PANEL)
        fila_btn.pack(anchor="w", pady=6)

        self.btn_pausa = self._btn(fila_btn, "Pausar",  self._pausar)
        self.btn_pausa.pack(side="left", padx=(0, 4))
        self._btn(fila_btn, "Reiniciar", self.iniciar).pack(
            side="left", padx=4)
        self._btn(fila_btn, "Detener", self._detener).pack(
            side="left", padx=4)

        self.lbl_estado = tk.Label(
            sec, text="", bg=FONDO_PANEL,
            fg="#aaaaaa", font=FUENTE_LABEL)
        self.lbl_estado.pack(anchor="w")

        self.lbl_alerta = tk.Label(
            sec, text="", bg=FONDO_PANEL,
            fg=LOG_ALERTA, font=FUENTE_BOLD)
        self.lbl_alerta.pack(anchor="w")

    def _btn(self, padre, texto, cmd):
        return tk.Button(
            padre, text=texto, command=cmd,
            bg=BTN_BG, fg=BTN_FG,
            activebackground=BTN_ACTIVE,
            activeforeground=BTN_FG,
            relief="flat", padx=8, pady=3,
            font=("Segoe UI", 9))

    def _construir_log(self, padre):
        tk.Label(padre, text="Registro de eventos",
                 bg=FONDO_PANEL, fg="#aaaaaa",
                 font=FUENTE_BOLD).pack(
            anchor="w", padx=8, pady=(4, 2))

        self.log = ScrolledText(
            padre, width=50, height=10,
            wrap="word", font=FUENTE_LOG,
            bg="#1a1a1a", fg=LOG_NORMAL,
            insertbackground="#ffffff",
            state="disabled")
        self.log.pack(fill="x", padx=8, pady=(0, 4))

        self.log.tag_config("normal",  foreground=LOG_NORMAL)
        self.log.tag_config("hambre",  foreground=LOG_HAMBRE)
        self.log.tag_config("comer",   foreground=LOG_COMER)
        self.log.tag_config("sistema", foreground=LOG_SISTEMA)
        self.log.tag_config("alerta",  foreground=LOG_ALERTA,
                            font=("Courier New", 9, "bold"))


    def _cambiar_metodo(self, metodo):
        self.var_metodo.set(metodo)
        self.iniciar()

    def _resaltar_boton_activo(self, metodo):
        for m, b in self._botones_metodo.items():
            if m == metodo:
                b.config(bg=METODO_COLORES[m])
            else:
                b.config(bg=BTN_BG)

    def iniciar(self):
        self._detener()

        cantidad = self._leer_cantidad()
        metodo   = self.var_metodo.get()

        self.mesa = Mesa(cantidad, metodo)
        self.mesa.velocidad = float(self.escala.get())
        self.filosofos = [Filosofo(i, self.mesa) for i in range(cantidad)]
        self.panel_metricas.set_mesa(self.mesa)

        self.ticks_bloqueo    = 0
        self.deadlock_avisado = False

        self._dibujar_mesa()
        self._resaltar_boton_activo(metodo)

        etiqueta = ETIQUETAS_METODO.get(metodo, metodo)
        color    = METODO_COLORES.get(metodo, "#ffffff")
        self.lbl_metodo.config(text=f"▶ {etiqueta}", fg=color)
        self.lbl_estado.config(text="Estado: ejecutando")
        self.lbl_alerta.config(text="")

        self._agregar_linea(
            f"--- {cantidad} filósofos · {etiqueta} ---", "sistema")

        for f in self.filosofos:
            f.start()

        self.btn_pausa.config(text="Pausar", state="normal")

    def _pausar(self):
        if self.mesa is None or not self.mesa.activo:
            return
        if self.mesa.corriendo.is_set():
            self.mesa.pausar()
            self.btn_pausa.config(text="Reanudar")
            self.lbl_estado.config(text="Estado: en pausa")
            self._agregar_linea("--- Pausa ---", "sistema")
        else:
            self.mesa.reanudar()
            self.btn_pausa.config(text="Pausar")
            self.lbl_estado.config(text="Estado: ejecutando")
            self._agregar_linea("--- Reanudado ---", "sistema")

    def _detener(self):
        if self.mesa is None or not self.mesa.activo:
            return
        self.mesa.detener()
        for f in self.filosofos:
            f.join(timeout=1)
        self._vaciar_log()
        self._agregar_linea("--- Detenido ---", "sistema")
        self.btn_pausa.config(text="Pausar", state="disabled")
        self.lbl_estado.config(text="Estado: detenido")

    def _cambiar_velocidad(self, valor):
        if self.mesa:
            self.mesa.velocidad = float(valor)

    def _leer_cantidad(self):
        try:
            n = int(self.var_cantidad.get())
        except (tk.TclError, ValueError):
            n = CANTIDAD_INICIAL
        n = max(MINIMO, min(MAXIMO, n))
        self.var_cantidad.set(n)
        return n


    def _dibujar_mesa(self):
        self.lienzo.delete("all")
        self.circulos         = []
        self.textos           = []
        self.lineas_tenedores = []

        n  = self.mesa.cantidad
        c  = self.centro
        r  = self.radio_mesa

        # mesa
        self.lienzo.create_oval(
            c - r, c - r, c + r, c + r,
            fill=COLOR_MESA, outline=BORDE_MESA, width=3)


        for i in range(n):
            x1, y1 = self._pos(i, r - 40, 0.5)
            x2, y2 = self._pos(i, r - 5,  0.5)
            linea  = self.lienzo.create_line(
                x1, y1, x2, y2,
                width=5, fill=COLOR_TENEDOR_LIBRE)
            self.lineas_tenedores.append(linea)
            xt, yt = self._pos(i, r + 14, 0.5)
            self.lienzo.create_text(
                xt, yt, text=f"T{i+1}",
                fill="#777777",
                font=("Segoe UI", 8))

        distancia = 2 * self.radio_filosofos * math.sin(math.pi / n)
        tamano    = min(40, int(distancia * 0.45))

        for i in range(n):
            x, y = self._pos(i, self.radio_filosofos)
            circ = self.lienzo.create_oval(
                x - tamano, y - tamano,
                x + tamano, y + tamano,
                fill=COLORES_ESTADO[PENSANDO],
                outline=BORDE_NORMAL, width=2)
            texto = self.lienzo.create_text(
                x, y, text="",
                font=("Segoe UI", 8, "bold"),
                fill="#1e1e1e")
            self.circulos.append(circ)
            self.textos.append(texto)

    def _pos(self, indice, radio, desfase=0.0):
        import math
        n     = self.mesa.cantidad
        angulo = (2 * math.pi * (indice + desfase) / n) - math.pi / 2
        x = self.centro + radio * math.cos(angulo)
        y = self.centro + radio * math.sin(angulo)
        return x, y

    def _dibujar_estados(self):
        estados, comidas, ocupados, esperas, maximas = self.mesa.leer_datos()

        for i in range(len(estados)):
            if esperas[i] >= PELIGRO_HAMBRE:
                borde, grosor = BORDE_PELIGRO, 4
            elif esperas[i] >= AVISO_HAMBRE:
                borde, grosor = BORDE_AVISO, 3
            else:
                borde, grosor = BORDE_NORMAL, 2

            self.lienzo.itemconfig(
                self.circulos[i],
                fill=COLORES_ESTADO[estados[i]],
                outline=borde, width=grosor)
            self.lienzo.itemconfig(
                self.textos[i],
                text=(f"F{i+1}\n{estados[i]}\n"
                      f"🍽 {comidas[i]}\n"
                      f"⏱ {esperas[i]:.1f}s"))

        for i in range(len(ocupados)):
            color = COLOR_TENEDOR_OCUPADO if ocupados[i] else COLOR_TENEDOR_LIBRE
            self.lienzo.itemconfig(self.lineas_tenedores[i], fill=color)

    def _revisar_deadlock(self):
        if self.mesa.hay_bloqueo():
            self.ticks_bloqueo += 1
        else:
            self.ticks_bloqueo = 0

        if self.ticks_bloqueo >= 5:
            if not self.deadlock_avisado:
                self.deadlock_avisado = True
                self.mesa.registrar_deadlock()
                self._agregar_linea(
                    "DEADLOCK: todos esperan un tenedor", "alerta")
            self.lienzo.config(bg=FONDO_DEADLOCK)
            self.lbl_alerta.config(
                text="⚠ DEADLOCK detectado")
        else:
            self.lienzo.config(bg=FONDO_LIENZO)
            self.lbl_alerta.config(text="")


    def _agregar_linea(self, texto, etiqueta="normal"):
        self.log.config(state="normal")
        self.log.insert("end", texto + "\n", etiqueta)
        lineas = int(self.log.index("end-1c").split(".")[0])
        if lineas > MAX_LINEAS_LOG:
            self.log.delete("1.0", f"{lineas - MAX_LINEAS_LOG + 1}.0")
        self.log.see("end")
        self.log.config(state="disabled")

    def _vaciar_log(self):
        if self.mesa is None:
            return
        while True:
            try:
                hora, msg, etq = self.mesa.mensajes.get_nowait()
                self._agregar_linea(f"[{hora}] {msg}", etq)
            except Exception:
                break


    def _loop(self):
        if self.mesa is not None:
            self.mesa.actualizar_esperas()
            self._vaciar_log()
            self._revisar_deadlock()
            self._dibujar_estados()
            self.panel_metricas.actualizar()
        self.raiz.after(100, self._loop)

    def _cerrar(self):
        self._detener()
        self.raiz.destroy()
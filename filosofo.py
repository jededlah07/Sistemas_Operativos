import random
import threading

from mesa import PENSANDO, HAMBRIENTO, COMIENDO
from estilos import PAUSA_DEADLOCK


class Filosofo(threading.Thread):
    def __init__(self, numero, mesa):
        super().__init__(daemon=True)
        self.numero    = numero
        self.nombre    = f"Filosofo {numero + 1}"
        self.mesa      = mesa
        self.izquierdo = numero
        self.derecho   = (numero + 1) % mesa.cantidad
        self.primera_vez = True


    def pensar(self):
        self.mesa.cambiar_estado(self.numero, PENSANDO)
        self.mesa.registrar(f"{self.nombre} piensa", "normal")
        self.mesa.esperar(random.uniform(1, 3))

    def tener_hambre(self):
        self.mesa.cambiar_estado(self.numero, HAMBRIENTO)
        self.mesa.registrar(f"{self.nombre} tiene hambre", "hambre")

    def comer(self):
        self.mesa.cambiar_estado(self.numero, COMIENDO)
        self.mesa.sumar_comida(self.numero)
        self.mesa.registrar(f"{self.nombre} come", "comer")
        self.mesa.esperar(random.uniform(1, 2))
        if self.mesa.activo:
            self.mesa.registrar(f"{self.nombre} suelta tenedores")


    def usar_tenedores(self, primero, segundo, pausa=0):
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

    def comer_sin_proteccion(self):
        self.usar_tenedores(self.izquierdo, self.derecho, PAUSA_DEADLOCK)

    def sincronizar_primera_vez(self):
        if not self.primera_vez:
            return True
        self.primera_vez = False
        return self.mesa.esperar_barrera()

    def comer_seguro(self):
        if not self.mesa.pedir_asiento():
            return
        try:
            primero = min(self.izquierdo, self.derecho)
            segundo = max(self.izquierdo, self.derecho)
            self.usar_tenedores(primero, segundo, 0)
        finally:
            self.mesa.liberar_asiento()

    def comer_arbitro(self):
        if not self.mesa.pedir_asiento():
            return
        try:
            self.usar_tenedores(self.izquierdo, self.derecho, 0)
        finally:
            self.mesa.liberar_asiento()

    def comer_asimetrico(self):
        if self.numero % 2 == 0:
            primero, segundo = self.izquierdo, self.derecho
        else:
            primero, segundo = self.derecho, self.izquierdo
        self.usar_tenedores(primero, segundo, 0)


    def run(self):
        metodos = {
            "deadlock":   self._ciclo_deadlock,
            "seguro":     self._ciclo_seguro,
            "arbitro":    self._ciclo_arbitro,
            "asimetrico": self._ciclo_asimetrico,
        }
        ciclo = metodos.get(self.mesa.metodo, self._ciclo_seguro)
        while self.mesa.activo:
            ciclo()

    def _ciclo_deadlock(self):
        self.pensar()
        if not self.mesa.activo:
            return
        if not self.sincronizar_primera_vez():
            return
        self.tener_hambre()
        self.comer_sin_proteccion()

    def _ciclo_seguro(self):
        self.pensar()
        if not self.mesa.activo:
            return
        self.tener_hambre()
        self.comer_seguro()

    def _ciclo_arbitro(self):
        self.pensar()
        if not self.mesa.activo:
            return
        self.tener_hambre()
        self.comer_arbitro()

    def _ciclo_asimetrico(self):
        self.pensar()
        if not self.mesa.activo:
            return
        self.tener_hambre()
        self.comer_asimetrico()

import queue
import threading
import time

from estilos import AVISO_HAMBRE, PELIGRO_HAMBRE, PAUSA_DEADLOCK

PENSANDO   = "pensando"
HAMBRIENTO = "hambriento"
COMIENDO   = "comiendo"


class Mesa:
    def __init__(self, cantidad, metodo="seguro"):
        self.cantidad        = cantidad
        self.metodo          = metodo
        self.tenedores       = [threading.Lock() for _ in range(cantidad)]
        self.asientos        = threading.Semaphore(cantidad - 1)
        self.barrera         = threading.Barrier(cantidad)
        self.estado          = [PENSANDO] * cantidad
        self.comidas         = [0] * cantidad
        self.tenedor_ocupado = [False] * cantidad
        self.espera          = [0.0] * cantidad
        self.espera_maxima   = [0.0] * cantidad
        self.deadlocks       = 0
        self.candado_datos   = threading.Lock()
        self.mensajes        = queue.Queue()
        self.activo          = True
        self.corriendo       = threading.Event()
        self.corriendo.set()
        self.velocidad       = 1.0
        self.ultimo_tick     = time.monotonic()
        self.inicio          = time.monotonic()


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

    def tiempo_corriendo(self):
        return time.monotonic() - self.inicio


    def cambiar_estado(self, numero, nuevo):
        with self.candado_datos:
            self.estado[numero] = nuevo
            if nuevo != HAMBRIENTO:
                self.espera[numero] = 0.0

    def marcar_tenedor(self, indice, ocupado):
        with self.candado_datos:
            self.tenedor_ocupado[indice] = ocupado

    def sumar_comida(self, numero):
        with self.candado_datos:
            self.comidas[numero] += 1

    def actualizar_esperas(self):
        ahora = time.monotonic()
        paso  = ahora - self.ultimo_tick
        self.ultimo_tick = ahora
        if not self.activo or not self.corriendo.is_set():
            return
        with self.candado_datos:
            for i in range(self.cantidad):
                if self.estado[i] == HAMBRIENTO:
                    self.espera[i]        += paso * self.velocidad
                    self.espera_maxima[i]  = max(self.espera_maxima[i],
                                                 self.espera[i])


    def tomar_tenedor(self, filosofo, indice):
        while self.activo:
            if self.tenedores[indice].acquire(timeout=0.1):
                self.marcar_tenedor(indice, True)
                self.registrar(
                    f"Filosofo {filosofo + 1} toma tenedor {indice + 1}")
                return True
        return False

    def soltar_tenedor(self, indice):
        self.marcar_tenedor(indice, False)
        self.tenedores[indice].release()


    def pedir_asiento(self):
        while self.activo:
            if self.asientos.acquire(timeout=0.1):
                return True
        return False

    def liberar_asiento(self):
        self.asientos.release()


    def esperar_barrera(self):
        try:
            self.barrera.wait()
            return True
        except threading.BrokenBarrierError:
            return False


    def hay_bloqueo(self):
        with self.candado_datos:
            return (self.activo
                    and all(e == HAMBRIENTO for e in self.estado)
                    and all(self.tenedor_ocupado))

    def registrar_deadlock(self):
        with self.candado_datos:
            self.deadlocks += 1

    def throughput(self):
        t = self.tiempo_corriendo()
        total = sum(self.comidas)
        return total / t if t > 0 else 0.0

    def espera_promedio(self):
        with self.candado_datos:
            maximas = [x for x in self.espera_maxima if x > 0]
            return sum(maximas) / len(maximas) if maximas else 0.0

    def leer_datos(self):
        with self.candado_datos:
            return (list(self.estado),
                    list(self.comidas),
                    list(self.tenedor_ocupado),
                    list(self.espera),
                    list(self.espera_maxima))


    def registrar(self, mensaje, etiqueta="normal"):
        self.mensajes.put((time.strftime("%H:%M:%S"), mensaje, etiqueta))
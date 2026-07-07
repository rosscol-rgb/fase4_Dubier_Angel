# -*- coding: utf-8 -*-
"""
=============================================================================
 SOFTWARE FJ | PLATAFORMA DE GESTION DE SERVICIOS Y RESERVAS
=============================================================================
 Solucion de consola construida en Python 3 con Programacion Orientada a
 Objetos y SIN motor de base de datos. Administra tres entidades:

     * Clientes
     * Servicios  (Sala de reunion, Equipo tecnologico, Asesoria profesional)
     * Reservas

 Pilares de POO cubiertos:
     - Abstraccion : clases abstractas 'ElementoNegocio' y 'Servicio'.
     - Herencia    : clientes, servicios y reservas heredan de la base.
     - Polimorfismo: cada servicio redefine costo(), detalle() y verificar().
     - Encapsulacion: atributos privados protegidos por properties.
     - Sobrecarga  : constructor alternativo (classmethod) y despacho de
                     metodos por tipo con functools.singledispatchmethod,
                     ademas de variantes de calculo con parametros opcionales.

 Manejo de excepciones:
     - Excepciones personalizadas propias del dominio.
     - Bloques try/except, try/except/else y try/except/finally.
     - Encadenamiento de excepciones con 'raise ... from ...'.
     - Todo error o evento se escribe en un archivo de bitacora (log).

 Regla de oro: la plataforma NUNCA se cae. Ante cualquier error se registra
 en la bitacora y la ejecucion continua de manera estable.
=============================================================================
"""

from __future__ import annotations   # Anotaciones de tipo diferidas

import os
import re
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from functools import singledispatchmethod
from datetime import datetime


# =============================================================================
# BLOQUE 1 | BITACORA DE EVENTOS (LOGGING)
# =============================================================================
# Se crea una unica bitacora para toda la plataforma. Registra tanto los
# eventos correctos como los errores, con su traza cuando corresponde.
# -----------------------------------------------------------------------------

ARCHIVO_BITACORA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bitacora_softwarefj.log"
)


def preparar_bitacora() -> logging.Logger:
    """Inicializa y devuelve la bitacora central de la plataforma."""
    bitacora = logging.getLogger("PlataformaFJ")
    bitacora.setLevel(logging.DEBUG)

    # Se previene la duplicidad de manejadores en ejecuciones repetidas.
    if bitacora.handlers:
        return bitacora

    patron = logging.Formatter(
        "[%(asctime)s] (%(levelname)s) %(name)s :: %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )

    # Salida a archivo: guarda todo el detalle (nivel DEBUG hacia arriba).
    a_archivo = logging.FileHandler(ARCHIVO_BITACORA, mode="a", encoding="utf-8")
    a_archivo.setLevel(logging.DEBUG)
    a_archivo.setFormatter(patron)
    bitacora.addHandler(a_archivo)

    # Salida a pantalla: unicamente incidencias (WARNING o superior).
    a_pantalla = logging.StreamHandler()
    a_pantalla.setLevel(logging.WARNING)
    a_pantalla.setFormatter(patron)
    bitacora.addHandler(a_pantalla)

    return bitacora


BITACORA = preparar_bitacora()


# =============================================================================
# BLOQUE 2 | EXCEPCIONES PROPIAS DEL DOMINIO
# =============================================================================
# Todas las excepciones del negocio descienden de 'SoftwareFJExcepcion', lo
# que permite capturarlas en conjunto o de forma individual y encadenarlas.
# -----------------------------------------------------------------------------

class SoftwareFJExcepcion(Exception):
    """Excepcion raiz de la plataforma Software FJ."""


class DatoInvalidoError(SoftwareFJExcepcion):
    """Un valor recibido no cumple el formato o el rango esperado."""


class CampoRequeridoError(SoftwareFJExcepcion):
    """Falta un campo obligatorio para completar la operacion."""


class ServicioInactivoError(SoftwareFJExcepcion):
    """El servicio existe pero se encuentra fuera de operacion."""


class ReservaError(SoftwareFJExcepcion):
    """Problema surgido durante la gestion de una reserva."""


class TransicionInvalidaError(SoftwareFJExcepcion):
    """Se intento un cambio de estado no permitido en la reserva."""


class CalculoError(SoftwareFJExcepcion):
    """El calculo de un costo arrojo un resultado inconsistente."""


# =============================================================================
# BLOQUE 3 | UTILIDADES DE VALIDACION
# =============================================================================
# Las reglas de validacion se centralizan aqui para reutilizarlas desde las
# distintas clases (alta cohesion, sin repetir codigo).
# -----------------------------------------------------------------------------

class Validaciones:
    """Coleccion de validadores estaticos reutilizables."""

    _CORREO = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
    _DIGITOS = re.compile(r"^\d+$")
    _LETRAS = re.compile(r"^[A-Za-zAEIOUaeiouNn ]+$")

    @staticmethod
    def requerido(valor, campo: str):
        """Verifica que un campo obligatorio venga con contenido."""
        if valor is None or str(valor).strip() == "":
            raise CampoRequeridoError(f"El campo '{campo}' es obligatorio.")
        return str(valor).strip()

    @staticmethod
    def solo_letras(valor, campo: str) -> str:
        texto = Validaciones.requerido(valor, campo)
        if not Validaciones._LETRAS.fullmatch(texto):
            raise DatoInvalidoError(f"El campo '{campo}' solo admite letras: '{valor}'.")
        return texto

    @staticmethod
    def solo_digitos(valor, campo: str, minimo: int, maximo: int) -> str:
        texto = Validaciones.requerido(valor, campo)
        if not Validaciones._DIGITOS.fullmatch(texto):
            raise DatoInvalidoError(f"El campo '{campo}' solo admite digitos: '{valor}'.")
        if not (minimo <= len(texto) <= maximo):
            raise DatoInvalidoError(
                f"El campo '{campo}' debe tener entre {minimo} y {maximo} digitos."
            )
        return texto

    @staticmethod
    def correo(valor) -> str:
        texto = Validaciones.requerido(valor, "correo").lower()
        if not Validaciones._CORREO.fullmatch(texto):
            raise DatoInvalidoError(f"Correo electronico invalido: '{valor}'.")
        return texto

    @staticmethod
    def numero_positivo(valor, campo: str) -> float:
        """Convierte a numero y exige que sea estrictamente positivo."""
        try:
            numero = float(valor)
        except (TypeError, ValueError) as origen:
            # Encadenamiento: se preserva la causa tecnica original.
            raise DatoInvalidoError(
                f"El campo '{campo}' debe ser numerico, se recibio: {valor!r}"
            ) from origen
        if numero <= 0:
            raise DatoInvalidoError(f"El campo '{campo}' debe ser mayor que cero.")
        return numero


# =============================================================================
# BLOQUE 4 | CLASE ABSTRACTA BASE
# =============================================================================
# 'ElementoNegocio' representa cualquier objeto administrable de la plataforma
# y provee un folio consecutivo y una marca temporal de alta.
# -----------------------------------------------------------------------------

class ElementoNegocio(ABC):
    """Entidad general y abstracta de la plataforma Software FJ."""

    _folio_actual: int = 100   # Los folios inician en 101 para diferenciarlos.

    def __init__(self) -> None:
        ElementoNegocio._folio_actual += 1
        self._folio: int = ElementoNegocio._folio_actual
        self._alta: datetime = datetime.now()

    @property
    def folio(self) -> int:
        """Folio unico e inmutable del elemento."""
        return self._folio

    @property
    def alta(self) -> datetime:
        """Fecha y hora de alta del elemento."""
        return self._alta

    @abstractmethod
    def verificar(self) -> None:
        """Comprueba la validez interna. Lanza excepcion si algo falla."""
        raise NotImplementedError

    @abstractmethod
    def detalle(self) -> str:
        """Devuelve una linea descriptiva del elemento (polimorfismo)."""
        raise NotImplementedError


# =============================================================================
# BLOQUE 5 | CLIENTE
# =============================================================================
# Encapsula los datos personales. Cada atributo se protege con una property
# que delega la validacion en el bloque de utilidades.
# -----------------------------------------------------------------------------

class Cliente(ElementoNegocio):
    """Cliente de la plataforma con datos personales validados."""

    def __init__(self, nombre: str, cedula: str, correo: str, celular: str) -> None:
        super().__init__()
        self.nombre = nombre     # Cada asignacion pasa por su validador.
        self.cedula = cedula
        self.correo = correo
        self.celular = celular
        BITACORA.info("Alta de cliente en memoria | folio=%s cedula=%s",
                      self.folio, cedula)

    # -------- Constructor alternativo (una forma de sobrecarga) ----------
    @classmethod
    def desde_diccionario(cls, datos: dict) -> "Cliente":
        """Crea un Cliente a partir de un diccionario de datos.

        Es una variante del constructor: misma clase, distinta forma de
        instanciar (patron de sobrecarga de constructores en Python).
        """
        faltantes = [c for c in ("nombre", "cedula", "correo", "celular")
                     if c not in datos]
        if faltantes:
            raise CampoRequeridoError(
                f"Faltan campos para crear el cliente: {', '.join(faltantes)}."
            )
        return cls(datos["nombre"], datos["cedula"], datos["correo"], datos["celular"])

    # ------------------------------ Properties ---------------------------
    @property
    def nombre(self) -> str:
        return self.__nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self.__nombre = Validaciones.solo_letras(valor, "nombre").title()

    @property
    def cedula(self) -> str:
        return self.__cedula

    @cedula.setter
    def cedula(self, valor: str) -> None:
        self.__cedula = Validaciones.solo_digitos(valor, "cedula", 6, 15)

    @property
    def correo(self) -> str:
        return self.__correo

    @correo.setter
    def correo(self, valor: str) -> None:
        self.__correo = Validaciones.correo(valor)

    @property
    def celular(self) -> str:
        return self.__celular

    @celular.setter
    def celular(self, valor: str) -> None:
        self.__celular = Validaciones.solo_digitos(valor, "celular", 7, 15)

    # --------------------------- Metodos abstractos ----------------------
    def verificar(self) -> None:
        # Reasignar por las properties vuelve a ejecutar las validaciones.
        self.nombre = self.__nombre
        self.cedula = self.__cedula
        self.correo = self.__correo
        self.celular = self.__celular

    def detalle(self) -> str:
        return (f"Cliente {self.folio} | {self.nombre} | CC {self.cedula} "
                f"| {self.correo} | Cel {self.celular}")


# =============================================================================
# BLOQUE 6 | SERVICIO (CLASE ABSTRACTA)
# =============================================================================
# Define el contrato de todo servicio. Incorpora el metodo sobrecargado
# '_ajustar' (despacho por tipo) para aplicar impuestos y descuentos.
# -----------------------------------------------------------------------------

class Servicio(ElementoNegocio, ABC):
    """Contrato abstracto compartido por todos los servicios."""

    IVA: float = 0.19   # Impuesto por defecto (19%).

    def __init__(self, titulo: str, tarifa: float, activo: bool = True) -> None:
        super().__init__()
        self._titulo = Validaciones.requerido(titulo, "titulo del servicio")
        self.tarifa = tarifa            # Property con validacion.
        self._activo = bool(activo)

    @property
    def titulo(self) -> str:
        return self._titulo

    @property
    def tarifa(self) -> float:
        return self.__tarifa

    @tarifa.setter
    def tarifa(self, valor: float) -> None:
        self.__tarifa = Validaciones.numero_positivo(valor, "tarifa")

    @property
    def activo(self) -> bool:
        return self._activo

    @activo.setter
    def activo(self, valor: bool) -> None:
        self._activo = bool(valor)

    # ---------------- Sobrecarga real por despacho de tipos --------------
    # 'singledispatchmethod' elige la implementacion segun el TIPO del primer
    # argumento. Asi el mismo nombre '_ajustar' se comporta distinto cuando
    # recibe un descuento (float) o una configuracion completa (dict).
    @singledispatchmethod
    def _ajustar(self, ajuste, subtotal: float) -> float:
        raise CalculoError(f"Tipo de ajuste no soportado: {type(ajuste).__name__}")

    @_ajustar.register
    def _(self, ajuste: float, subtotal: float) -> float:
        """Variante 1: solo descuento porcentual, impuesto por defecto."""
        if not (0.0 <= ajuste <= 1.0):
            raise CalculoError(f"Descuento fuera de rango [0-1]: {ajuste}")
        total = subtotal * (1 + self.IVA) * (1 - ajuste)
        return self._validar_total(total)

    @_ajustar.register
    def _(self, ajuste: dict, subtotal: float) -> float:
        """Variante 2: impuesto y descuento personalizados."""
        impuesto = ajuste.get("impuesto", self.IVA)
        descuento = ajuste.get("descuento", 0.0)
        if not (0.0 <= impuesto <= 1.0):
            raise CalculoError(f"Impuesto fuera de rango [0-1]: {impuesto}")
        if not (0.0 <= descuento <= 1.0):
            raise CalculoError(f"Descuento fuera de rango [0-1]: {descuento}")
        total = subtotal * (1 + impuesto) * (1 - descuento)
        return self._validar_total(total)

    @staticmethod
    def _validar_total(total: float) -> float:
        """Blindaje final: ningun total puede ser negativo."""
        if total < 0:
            raise CalculoError("El total calculado resulto negativo.")
        return round(total, 2)

    def _preparar_ajuste(self, impuesto, descuento):
        """Decide que variante de '_ajustar' se invocara.

        Si no se pide un impuesto especial se envia un float (variante 1);
        de lo contrario se envia un dict (variante 2). Este metodo demuestra
        como la sobrecarga se resuelve segun el tipo de dato.
        """
        return descuento if impuesto is None else {"impuesto": impuesto,
                                                    "descuento": descuento}

    # ---------------------- Metodos abstractos ---------------------------
    @abstractmethod
    def costo(self, duracion: float, impuesto: float | None = None,
              descuento: float = 0.0) -> float:
        """Calcula el costo del servicio (redefinido por cada subclase)."""
        raise NotImplementedError

    @abstractmethod
    def descripcion_servicio(self) -> str:
        """Descripcion propia del servicio (polimorfismo)."""
        raise NotImplementedError

    # ---------------------- Metodos de ElementoNegocio -------------------
    def verificar(self) -> None:
        if not self._activo:
            raise ServicioInactivoError(f"El servicio '{self._titulo}' esta inactivo.")

    def detalle(self) -> str:
        estado = "ACTIVO" if self._activo else "INACTIVO"
        return f"Servicio {self.folio} | {self.descripcion_servicio()} | ({estado})"


# =============================================================================
# BLOQUE 7 | SERVICIOS ESPECIALIZADOS
# =============================================================================

class SalaReunion(Servicio):
    """Servicio de reserva de salas. Se cobra por hora de uso."""

    def __init__(self, titulo: str, valor_hora: float, aforo: int,
                 activo: bool = True) -> None:
        super().__init__(titulo, valor_hora, activo)
        if not isinstance(aforo, int) or aforo <= 0:
            raise DatoInvalidoError(f"Aforo de sala invalido: {aforo!r} (entero > 0).")
        self._aforo = aforo

    def costo(self, duracion: float, impuesto: float | None = None,
              descuento: float = 0.0) -> float:
        horas = Validaciones.numero_positivo(duracion, "horas")
        subtotal = self.tarifa * horas
        return self._ajustar(self._preparar_ajuste(impuesto, descuento), subtotal)

    def descripcion_servicio(self) -> str:
        return (f"Sala '{self.titulo}' | Aforo {self._aforo} personas "
                f"| ${self.tarifa:,.0f}/hora")


class EquipoTecnologico(Servicio):
    """Servicio de alquiler de equipos. Se cobra por dia y por unidad."""

    def __init__(self, titulo: str, valor_dia: float, unidades: int,
                 activo: bool = True) -> None:
        super().__init__(titulo, valor_dia, activo)
        if not isinstance(unidades, int) or unidades <= 0:
            raise DatoInvalidoError(f"Unidades invalidas: {unidades!r} (entero > 0).")
        self._unidades = unidades

    def costo(self, duracion: float, impuesto: float | None = None,
              descuento: float = 0.0) -> float:
        dias = Validaciones.numero_positivo(duracion, "dias")
        subtotal = self.tarifa * dias * self._unidades
        return self._ajustar(self._preparar_ajuste(impuesto, descuento), subtotal)

    def descripcion_servicio(self) -> str:
        return (f"Equipo '{self.titulo}' | {self._unidades} unidad(es) "
                f"| ${self.tarifa:,.0f}/dia")


class AsesoriaProfesional(Servicio):
    """Servicio de asesoria. El valor depende de las horas y del perfil."""

    # Factor de precio segun el perfil del asesor.
    PERFILES = {"basico": 1.0, "avanzado": 1.6, "experto": 2.2}

    def __init__(self, titulo: str, valor_hora: float, especialidad: str,
                 perfil: str, activo: bool = True) -> None:
        super().__init__(titulo, valor_hora, activo)
        self._especialidad = Validaciones.requerido(especialidad, "especialidad")
        perfil = str(perfil).strip().lower() if perfil else ""
        if perfil not in self.PERFILES:
            raise DatoInvalidoError(
                f"Perfil invalido: '{perfil}'. Opciones: {', '.join(self.PERFILES)}."
            )
        self._perfil = perfil

    def costo(self, duracion: float, impuesto: float | None = None,
              descuento: float = 0.0) -> float:
        horas = Validaciones.numero_positivo(duracion, "horas")
        subtotal = self.tarifa * horas * self.PERFILES[self._perfil]
        return self._ajustar(self._preparar_ajuste(impuesto, descuento), subtotal)

    def descripcion_servicio(self) -> str:
        return (f"Asesoria '{self.titulo}' | {self._especialidad} "
                f"| Perfil {self._perfil} | ${self.tarifa:,.0f}/hora")


# =============================================================================
# BLOQUE 8 | RESERVA Y SUS ESTADOS
# =============================================================================

class Estado(Enum):
    """Estados del ciclo de vida de una reserva."""
    NUEVA = auto()
    APROBADA = auto()
    ANULADA = auto()
    LIQUIDADA = auto()


class Reserva(ElementoNegocio):
    """Vincula un cliente con un servicio, una duracion y un estado."""

    def __init__(self, cliente: Cliente, servicio: Servicio, duracion: float,
                 descuento: float = 0.0) -> None:
        super().__init__()
        if cliente is None:
            raise CampoRequeridoError("La reserva necesita un cliente.")
        if servicio is None:
            raise CampoRequeridoError("La reserva necesita un servicio.")
        self._cliente = cliente
        self._servicio = servicio
        self._duracion = duracion
        self._descuento = descuento
        self._estado = Estado.NUEVA
        self._valor: float | None = None
        BITACORA.info("Reserva generada | folio=%s (cliente %s, servicio %s)",
                      self.folio, cliente.folio, servicio.folio)

    @property
    def estado(self) -> Estado:
        return self._estado

    @property
    def valor(self) -> float | None:
        return self._valor

    # ---------------------- Ciclo de vida --------------------------------
    def aprobar(self) -> None:
        """Aprueba la reserva. Emplea try/except/else.

        El bloque 'else' solo corre si la validacion previa no lanzo errores.
        """
        try:
            self._cliente.verificar()
            self._servicio.verificar()   # Lanza ServicioInactivoError si aplica.
            if self._estado is not Estado.NUEVA:
                raise TransicionInvalidaError(
                    f"Solo se aprueba una reserva NUEVA (actual: {self._estado.name})."
                )
        except SoftwareFJExcepcion:
            raise   # Se propaga para que la capa superior la registre.
        else:
            self._estado = Estado.APROBADA
            BITACORA.info("Reserva %s APROBADA.", self.folio)

    def anular(self) -> None:
        """Anula la reserva si el estado lo permite."""
        if self._estado in (Estado.ANULADA, Estado.LIQUIDADA):
            raise TransicionInvalidaError(
                f"No se puede anular una reserva en estado {self._estado.name}."
            )
        self._estado = Estado.ANULADA
        BITACORA.info("Reserva %s ANULADA.", self.folio)

    def liquidar(self, impuesto: float | None = None) -> float:
        """Liquida (cobra) la reserva. Emplea try/except/finally.

        El bloque 'finally' deja siempre constancia del intento de liquidacion.
        """
        try:
            if self._estado is not Estado.APROBADA:
                raise ReservaError(
                    f"Solo se liquida una reserva APROBADA (actual: {self._estado.name})."
                )
            # Polimorfismo: cada servicio calcula su costo a su manera.
            self._valor = self._servicio.costo(
                self._duracion, impuesto=impuesto, descuento=self._descuento
            )
            self._estado = Estado.LIQUIDADA
            BITACORA.info("Reserva %s LIQUIDADA por $%.2f", self.folio, self._valor)
            return self._valor
        except SoftwareFJExcepcion as origen:
            # Encadenamiento: la ReservaError conserva la causa tecnica.
            raise ReservaError(f"No se pudo liquidar la reserva {self.folio}.") from origen
        finally:
            BITACORA.debug("Intento de liquidacion finalizado | reserva=%s", self.folio)

    def verificar(self) -> None:
        if self._duracion is None:
            raise CampoRequeridoError("La reserva necesita una duracion.")
        self._cliente.verificar()
        self._servicio.verificar()

    def detalle(self) -> str:
        valor = f"${self._valor:,.2f}" if self._valor is not None else "sin liquidar"
        return (f"Reserva {self.folio} | {self._cliente.nombre} -> "
                f"{self._servicio.titulo} | {self._estado.name} | {valor}")


# =============================================================================
# BLOQUE 9 | ADMINISTRADOR DE LA PLATAFORMA (LISTAS EN MEMORIA)
# =============================================================================
# Mantiene las colecciones de clientes, servicios y reservas. Cada metodo
# esta protegido para que ningun error interrumpa la plataforma.
# -----------------------------------------------------------------------------

class PlataformaFJ:
    """Coordina en memoria a clientes, servicios y reservas."""

    def __init__(self) -> None:
        self._clientes: list[Cliente] = []
        self._servicios: list[Servicio] = []
        self._reservas: list[Reserva] = []
        BITACORA.info("Plataforma Software FJ lista.")

    # ---------------------- Alta de clientes -----------------------------
    def afiliar_cliente(self, **datos) -> Cliente | None:
        """Afilia un cliente. Devuelve el cliente o None ante un error.

        Usa try/except/else: el 'else' agrega a la lista solo si todo salio
        bien. Acepta los datos por palabras clave para mayor flexibilidad.
        """
        try:
            cliente = Cliente.desde_diccionario(datos)
            if any(c.cedula == cliente.cedula for c in self._clientes):
                raise DatoInvalidoError(
                    f"Ya existe un cliente con cedula {cliente.cedula}."
                )
        except SoftwareFJExcepcion as err:
            BITACORA.error("Afiliacion rechazada: %s", err)
            return None
        except Exception as err:   # Salvaguarda ante fallos imprevistos.
            BITACORA.critical("Error inesperado al afiliar cliente: %s", err)
            return None
        else:
            self._clientes.append(cliente)
            BITACORA.info("Cliente afiliado: %s", cliente.detalle())
            return cliente

    # ---------------------- Alta de servicios ----------------------------
    def publicar_servicio(self, constructor) -> Servicio | None:
        """Publica un servicio construido por la funcion 'constructor'.

        Delegar la creacion en una funcion permite atrapar aqui cualquier
        error de construccion y mantener la plataforma en pie.
        """
        try:
            servicio = constructor()
        except SoftwareFJExcepcion as err:
            BITACORA.error("Publicacion de servicio rechazada: %s", err)
            return None
        except Exception as err:
            BITACORA.critical("Error inesperado al publicar servicio: %s", err)
            return None
        else:
            self._servicios.append(servicio)
            BITACORA.info("Servicio publicado: %s", servicio.detalle())
            return servicio

    # ---------------------- Gestion de reservas --------------------------
    def gestionar_reserva(self, cliente: Cliente, servicio: Servicio,
                          duracion, descuento: float = 0.0,
                          impuesto: float | None = None) -> Reserva | None:
        """Crea, aprueba y liquida una reserva de forma totalmente protegida."""
        try:
            reserva = Reserva(cliente, servicio, duracion, descuento)
            self._reservas.append(reserva)   # Se conserva aunque luego falle.
            reserva.aprobar()
            valor = reserva.liquidar(impuesto=impuesto)
        except SoftwareFJExcepcion as err:
            BITACORA.error("Reserva no concretada: %s", err)
            if err.__cause__:   # Se registra tambien la causa encadenada.
                BITACORA.error("   causa raiz -> %s", err.__cause__)
            return None
        except Exception as err:
            BITACORA.critical("Error inesperado en la reserva: %s", err)
            return None
        else:
            BITACORA.info("Reserva concretada por $%.2f", valor)
            return reserva

    # ---------------------- Reporte --------------------------------------
    def reporte(self) -> str:
        """Genera un reporte textual del estado de la plataforma."""
        marco = "=" * 72
        lineas = [marco, "REPORTE GENERAL | PLATAFORMA SOFTWARE FJ", marco]
        lineas.append(f"Clientes afiliados  : {len(self._clientes)}")
        lineas.append(f"Servicios publicados: {len(self._servicios)}")
        lineas.append(f"Reservas gestionadas: {len(self._reservas)}")
        lineas.append("-" * 72)
        for r in self._reservas:
            lineas.append("  " + r.detalle())
        lineas.append(marco)
        return "\n".join(lineas)


# =============================================================================
# BLOQUE 10 | DEMOSTRACION (MAS DE 10 OPERACIONES, VALIDAS E INVALIDAS)
# =============================================================================
# Se ejecutan operaciones correctas e incorrectas para evidenciar que la
# plataforma controla los errores y sigue funcionando sin detenerse.
# -----------------------------------------------------------------------------

def correr_demostracion() -> None:
    """Ejecuta una bateria de operaciones mezclando exitos y fallos."""
    print("\n************************************************************")
    print("*   PLATAFORMA SOFTWARE FJ | DEMOSTRACION DE OPERACIONES   *")
    print("************************************************************\n")

    plataforma = PlataformaFJ()

    # ---------- CLIENTES (validos e invalidos) -----------------------------
    print(">> Afiliacion de clientes...\n")
    # 1. Valido
    cliente_a = plataforma.afiliar_cliente(
        nombre="Mariana Rojas", cedula="1024578963",
        correo="mariana.rojas@empresa.com", celular="3012223344")
    # 2. Valido
    cliente_b = plataforma.afiliar_cliente(
        nombre="Julian Torres", cedula="79564123",
        correo="julian.torres@correo.com", celular="3208887766")
    # 3. Invalido: nombre con simbolos
    plataforma.afiliar_cliente(
        nombre="R@ul#", cedula="11223344",
        correo="raul@x.com", celular="3001010101")
    # 4. Invalido: correo mal formado
    plataforma.afiliar_cliente(
        nombre="Sofia Mesa", cedula="22334455",
        correo="sofia_sin_arroba", celular="3002020202")
    # 5. Invalido: falta la cedula (campo requerido)
    plataforma.afiliar_cliente(
        nombre="Andres Leon", correo="andres@x.com", celular="3003030303")

    # ---------- SERVICIOS (validos e invalidos) ----------------------------
    print("\n>> Publicacion de servicios...\n")
    # 6. Valido: sala
    sala = plataforma.publicar_servicio(
        lambda: SalaReunion("Auditorio Norte", valor_hora=60000, aforo=40))
    # 7. Valido: equipo
    equipo = plataforma.publicar_servicio(
        lambda: EquipoTecnologico("Portatiles Gama Alta", valor_dia=45000, unidades=5))
    # 8. Valido: asesoria
    asesoria = plataforma.publicar_servicio(
        lambda: AsesoriaProfesional("Ciberseguridad", valor_hora=150000,
                                    especialidad="Pentesting", perfil="experto"))
    # 9. Invalido: aforo cero
    plataforma.publicar_servicio(
        lambda: SalaReunion("Sala Cero", valor_hora=30000, aforo=0))
    # 10. Invalido: perfil inexistente
    plataforma.publicar_servicio(
        lambda: AsesoriaProfesional("Cloud", valor_hora=90000,
                                    especialidad="AWS", perfil="gurú"))
    # 11. Valido pero inactivo (para provocar una reserva fallida)
    sala_inactiva = plataforma.publicar_servicio(
        lambda: SalaReunion("Sala Mantenimiento", valor_hora=50000,
                            aforo=10, activo=False))

    # ---------- RESERVAS (exitosas y fallidas) -----------------------------
    print("\n>> Gestion de reservas...\n")
    # 12. Exitosa: sala por 4 horas
    plataforma.gestionar_reserva(cliente_a, sala, duracion=4)
    # 13. Exitosa: equipo por 3 dias con 15% de descuento
    plataforma.gestionar_reserva(cliente_b, equipo, duracion=3, descuento=0.15)
    # 14. Exitosa: asesoria por 6 horas con impuesto reducido del 5%
    plataforma.gestionar_reserva(cliente_a, asesoria, duracion=6, impuesto=0.05)
    # 15. Fallida: servicio inactivo
    plataforma.gestionar_reserva(cliente_b, sala_inactiva, duracion=2)
    # 16. Fallida: duracion cero
    plataforma.gestionar_reserva(cliente_a, sala, duracion=0)
    # 17. Fallida: duracion de tipo texto
    plataforma.gestionar_reserva(cliente_b, equipo, duracion="tres")
    # 18. Fallida: descuento imposible del 200%
    plataforma.gestionar_reserva(cliente_a, asesoria, duracion=2, descuento=2.0)

    # ---------- REPORTE FINAL ---------------------------------------------
    print("\n" + plataforma.reporte())
    print(f"\n[i] Eventos y errores registrados en:\n    {ARCHIVO_BITACORA}\n")
    print("La plataforma termino ESTABLE, sin caerse ante ningun error.")


# =============================================================================
# BLOQUE 11 | PUNTO DE ARRANQUE
# =============================================================================
if __name__ == "__main__":
    # Ultima red de proteccion: ni un fallo catastrofico impide un cierre
    # ordenado de la ejecucion (try/except/finally global).
    try:
        BITACORA.info(">>> ARRANQUE DE LA PLATAFORMA <<<")
        correr_demostracion()
    except Exception as fatal:
        BITACORA.critical("Fallo fatal no controlado: %s", fatal)
        print(f"\n[!] Fallo fatal, revise la bitacora: {fatal}")
    finally:
        BITACORA.info(">>> CIERRE DE LA PLATAFORMA <<<")

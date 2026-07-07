# Plataforma Software FJ | Gestión de Servicios y Reservas

Solución de consola escrita en **Python 3** que administra clientes, servicios y reservas para la empresa **Software FJ**, aplicando Programación Orientada a Objetos y un **manejo avanzado de excepciones**, sin utilizar ningún motor de base de datos. Toda la información se maneja en memoria mediante objetos y listas; los archivos solo se usan para la bitácora de eventos y errores.

La premisa central del diseño es la estabilidad: ante cualquier error, la incidencia se registra en la bitácora y la ejecución **continúa sin interrumpirse**.

---

## 1. Resultado de aprendizaje

Implementar el manejo de excepciones en aplicaciones orientadas a objetos, buscando estabilidad y robustez, con una gestión adecuada de errores. Cada error queda registrado en un archivo de bitácora y la aplicación jamás se detiene.

---

## 2. Cómo ejecutar

**Requisitos:** Python 3.8 o superior. Solo se emplea la librería estándar (`os`, `re`, `logging`, `abc`, `enum`, `functools`, `datetime`); no hay dependencias externas.

```bash
python plataforma_fj.py
```

Al correr, se ejecuta una demostración con más de 10 operaciones (correctas e incorrectas) y se crea de manera automática el archivo `bitacora_softwarefj.log` en la misma carpeta.

---

## 3. Estructura

```
plataforma_fj/
├── plataforma_fj.py          # Codigo fuente completo y ejecutable
├── bitacora_softwarefj.log   # Bitacora (se crea sola al ejecutar)
└── README.md                 # Este documento
```

El código está organizado en **once bloques numerados y comentados en español**, lo que facilita ubicar cada concepto durante la revisión.

---

## 4. Diseño orientado a objetos

| Pilar | Aplicación concreta |
|-------|---------------------|
| **Abstracción** | Clases abstractas `ElementoNegocio` y `Servicio`, con métodos abstractos `verificar()`, `detalle()`, `costo()` y `descripcion_servicio()`. |
| **Herencia** | `Cliente`, los tres servicios y `Reserva` heredan de `ElementoNegocio`; los servicios además heredan de `Servicio`. |
| **Polimorfismo** | Cada servicio redefine `costo()` y `descripcion_servicio()`. La reserva liquida el costo sin conocer el tipo concreto del servicio. |
| **Encapsulación** | Datos personales y tarifas se guardan en atributos privados (`__nombre`, `__tarifa`) y se acceden mediante *properties* que validan cada asignación. |
| **Sobrecarga** | Tres mecanismos: constructor alternativo `Cliente.desde_diccionario()`, despacho de método por tipo con `functools.singledispatchmethod` (`_ajustar`), y variantes de cálculo mediante parámetros opcionales (`impuesto`, `descuento`). |

### Jerarquía de clases

```
ElementoNegocio (abstracta)
├── Cliente
├── Servicio (abstracta)
│   ├── SalaReunion
│   ├── EquipoTecnologico
│   └── AsesoriaProfesional
└── Reserva

PlataformaFJ    (administrador con las listas internas)
Validaciones    (utilidades estaticas de validacion)
```

---

## 5. Componentes principales

**`ElementoNegocio`** (abstracta): entidad general con folio consecutivo único y fecha de alta. Obliga a implementar `verificar()` y `detalle()`.

**`Validaciones`**: clase de utilidades con validadores estáticos reutilizables (`requerido`, `solo_letras`, `solo_digitos`, `correo`, `numero_positivo`). Centraliza las reglas para no repetir código.

**`Cliente`**: encapsula nombre, cédula, correo y celular. Ofrece además el constructor alternativo `desde_diccionario()`.

**`Servicio`** (abstracta): define el contrato de los servicios e incorpora el método sobrecargado `_ajustar()`, que aplica impuestos y descuentos según el tipo de dato recibido.

**Servicios especializados:**
* `SalaReunion`: se cobra por hora, según el aforo.
* `EquipoTecnologico`: se cobra por día multiplicado por el número de unidades.
* `AsesoriaProfesional`: se cobra por hora ajustada por un factor según el perfil (básico, avanzado o experto).

**`Reserva`**: vincula cliente, servicio, duración y estado (`NUEVA`, `APROBADA`, `ANULADA`, `LIQUIDADA`). Implementa `aprobar()`, `anular()` y `liquidar()`.

**`PlataformaFJ`**: administrador que mantiene las listas internas y expone `afiliar_cliente()`, `publicar_servicio()`, `gestionar_reserva()` y `reporte()`. Cada método está protegido para que ningún error detenga la plataforma.

---

## 6. Manejo de excepciones

### Jerarquía personalizada

```
SoftwareFJExcepcion (raiz del dominio)
├── DatoInvalidoError
├── CampoRequeridoError
├── ServicioInactivoError
├── ReservaError
├── TransicionInvalidaError
└── CalculoError
```

### Técnicas implementadas

| Técnica | Dónde se encuentra |
|---------|--------------------|
| **Excepciones personalizadas** | Bloque 2: jerarquía que desciende de `SoftwareFJExcepcion`. |
| **try / except** | Todos los métodos del administrador `PlataformaFJ`. |
| **try / except / else** | `Reserva.aprobar()` y `PlataformaFJ.afiliar_cliente()`: el `else` se ejecuta solo si no hubo error. |
| **try / except / finally** | `Reserva.liquidar()`: el `finally` deja siempre constancia del intento. |
| **Encadenamiento de excepciones** | `raise ... from ...` en `Validaciones.numero_positivo`, en el despacho de `_ajustar` y en `Reserva.liquidar`, preservando la causa original. |
| **Red de seguridad global** | El bloque `if __name__ == "__main__"` envuelve todo en un `try/except/finally`. |

### Bitácora (logs)

Se usa el módulo estándar `logging` con dos salidas:
* **Archivo** `bitacora_softwarefj.log`: registra todo el detalle (nivel DEBUG en adelante), incluyendo eventos exitosos y errores con su causa raíz.
* **Pantalla**: muestra únicamente incidencias (nivel WARNING o superior).

---

## 7. Demostración incluida

La función `correr_demostracion()` ejecuta más de **10 operaciones** combinando casos válidos e inválidos:

* **Clientes:** afiliaciones correctas y rechazadas (nombre con símbolos, correo mal formado, cédula ausente).
* **Servicios:** publicaciones correctas de los tres tipos y rechazadas (aforo cero, perfil inexistente).
* **Reservas:** reservas exitosas (con descuento, con impuesto reducido) y fallidas (servicio inactivo, duración cero, duración no numérica, descuento imposible).

En cada fallo la incidencia se registra y la plataforma sigue operando hasta emitir un reporte final.

---

## 8. Ejemplo de salida (reporte)

```
========================================================================
REPORTE GENERAL | PLATAFORMA SOFTWARE FJ
========================================================================
Clientes afiliados  : 2
Servicios publicados: 4
Reservas gestionadas: 7
------------------------------------------------------------------------
  Reserva 111 | Mariana Rojas -> Auditorio Norte | LIQUIDADA | $285,600.00
  Reserva 112 | Julian Torres -> Portatiles Gama Alta | LIQUIDADA | $682,762.50
  Reserva 113 | Mariana Rojas -> Ciberseguridad | LIQUIDADA | $2,079,000.00
  Reserva 114 | Julian Torres -> Sala Mantenimiento | NUEVA | sin liquidar
  ...
========================================================================

La plataforma termino ESTABLE, sin caerse ante ningun error.
```

---

## 9. Buenas prácticas aplicadas

* Validaciones centralizadas y reutilizables en la clase `Validaciones`.
* Separación de responsabilidades entre entidades, servicios y administrador.
* Uso de *properties* para blindar el acceso a los datos.
* Sobrecarga expresada de tres maneras idiomáticas de Python.
* Comentarios en español, nombres claros y sin dependencias ni base de datos.

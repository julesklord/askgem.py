# AskGem Proposed Features

This document outlines new features proposed for AskGem, aiming to enhance its capabilities as a CLI coding agent.

## 1. Análisis de Código Estático Profundo

**Descripción:** Implementar la capacidad de analizar la estructura sintáctica y semántica del código fuente. Esto incluye la identificación de clases, funciones, métodos, variables, sus tipos, y las relaciones entre ellos (dependencias, herencia).
**Beneficios:**

* **Refactorización Inteligente:** Permite realizar cambios de código más seguros y precisos (ej. renombrar un símbolo en todo el proyecto).
* **Detección Temprana de Errores:** Identificación de posibles errores de lógica o violaciones de patrones de diseño antes de la ejecución.
* **Generación de Código Contextual:** Mejorar la capacidad de generar fragmentos de código que se ajusten al contexto existente.
* **Comprensión del Proyecto:** Proporcionar una visión más clara de la arquitectura y el flujo de un proyecto.

## 2. Integración Avanzada con Control de Versiones (Git)

**Descripción:** Ampliar las interacciones con Git más allá de la ejecución básica de comandos, para incluir funcionalidades de asistencia y automatización en el flujo de trabajo de control de versiones.
**Beneficios:**

* **Mensajes de Commit Sugeridos:** Generar borradores de mensajes de commit basados en los cambios detectados en el código.
* **Resolución Asistida de Conflictos:** Guiar al usuario en la resolución de conflictos de fusión, sugiriendo opciones o automatizando resoluciones simples.
* **Gestión de Ramas Simplificada:** Crear, cambiar y fusionar ramas de manera más intuitiva.
* **Revisiones de Código Básicas:** Identificar y señalar diferencias clave o posibles problemas en los cambios propuestos.

## 3. Generación y Ejecución de Pruebas Unitarias

**Descripción:** Desarrollar la capacidad de generar automáticamente esqueletos de pruebas unitarias para funciones o módulos específicos, y luego ejecutar estas pruebas y reportar los resultados.
**Beneficios:**

* **Aumento de la Cobertura de Pruebas:** Facilitar la creación de pruebas, incentivando una mayor cobertura.
* **Detección Rápida de Regresiones:** Asegurar que los nuevos cambios no introduzcan errores en funcionalidades existentes.
* **Desarrollo Orientado a Pruebas (TDD):** Apoyar el flujo de trabajo de TDD al simplificar la creación y ejecución de pruebas.

## 4. Asistencia en Depuración

**Descripción:** Cuando se detecta un error de ejecución o un comando falla, analizar los mensajes de error y los logs para identificar la causa raíz y sugerir posibles soluciones o puntos de depuración.
**Beneficios:**

* **Resolución de Errores Más Rápida:** Reducir el tiempo y esfuerzo dedicado a la depuración.
* **Diagnóstico Preciso:** Proporcionar información contextual sobre la naturaleza del problema.
* **Sugerencias de Solución:** Ofrecer pasos a seguir o modificaciones de código para corregir el error.

## 5. Refactorización Asistida Inteligente

**Descripción:** Utilizando el análisis de código estático, ofrecer y aplicar refactorizaciones comunes de manera segura y automática, como renombrar variables, extraer métodos o mover código.
**Beneficios:**

* **Mejora Continua del Código:** Facilitar el mantenimiento y la mejora de la calidad del código sin introducir errores.
* **Consistencia del Código:** Asegurar que las refactorizaciones se apliquen de manera uniforme en todo el proyecto.
* **Productividad del Desarrollador:** Reducir la carga manual y repetitiva de las tareas de refactorización.

--

## Segunda Revision

 1. Manejo de Errores: El bloque try...except Exception as exc es demasiado genérico. Sería mejor capturar excepciones más específicas para diferentes tipos de fallos (red, API, validación   de herramientas) y así ofrecer mensajes de error más precisos y estrategias de recuperación (ej., reintentos automáticos).
 2. Tipado de Configuración: La configuración (config: Any) podría beneficiarse de un dataclass o una interfaz (AgentConfig) con tipos claros para sus propiedades, mejorando la robustez y
   la legibilidad.
 3. Observabilidad: Añadir más puntos de logging con niveles de detalle apropiados (DEBUG, INFO) en momentos clave del ciclo de vida del agente. Considerar métricas de rendimiento
   (latencia de herramientas, tiempo de respuesta del modelo).
 4. Gestión de Planes: Podría implementarse un sistema más robusto para los planes de ejecución, con soporte para múltiples planes, versiones o un formato más estructurado (YAML/JSON),junto con herramientas CLI para su gestión.
 5. Refactorización de _perform_context_snap: La modificación temporal del historial dentro de este método podría ser más limpia si el Summarizer aceptara una copia del historial o si el
   método fuera diseñado para ser inmutable.
 6. Validación de Resultados de Herramientas: Sería beneficioso añadir una capa de validación para los resultados de las herramientas (all_results) para asegurar que cumplen con un esquema   esperado, previniendo errores posteriores.

# Datos sinteticos para la tesis

El comando seed_demo_tesis completa un escenario academico ficticio para
desarrollo, demostracion y sustentacion. No debe ejecutarse sobre una base
institucional en produccion.

Ejecucion:

    python manage.py seed_demo_tesis --confirm

El escenario incluye acciones de seguimiento pendientes, vencidas y completadas
para `alumno.prueba.sga`, con avances del estudiante, acompanamiento del apoderado
y cierre docente. El comando es idempotente y no envia correos reales.

El conjunto contiene dos secciones de secundaria, cuatro cursos por seccion,
doce matriculas activas, apoderados vinculados, cuatro bimestres y registros
de asistencia, calificaciones, participacion, observaciones, incidencias y
notificaciones.

La carga es idempotente: usa identificadores estables y actualiza los datos
del escenario cuando ya existen. Los correos example.com, documentos,
telefonos y nombres agregados por el comando son sinteticos.

Antes de una implementacion real en la institucion se debe utilizar una base
limpia y migrar solamente informacion autorizada.

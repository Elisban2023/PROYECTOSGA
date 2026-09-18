import json
import xml.etree.ElementTree as ElementTree
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from django.conf import settings
from rest_framework.exceptions import APIException


class ServicioCloudNoDisponible(APIException):
    status_code = 503
    default_detail = "El almacenamiento cloud no esta disponible temporalmente."
    default_code = "cloud_unavailable"


class AwsSignedURLService:
    def __init__(self):
        self._validar_configuracion()
        self.base_url = settings.API_SIGNED_URL
        self.region = settings.API_SIGNED_URL_ZONE
        self.timeout = settings.API_SIGNED_URL_TIMEOUT
        self.credentials = Credentials(
            settings.API_SIGNED_URL_ACCESSKEY,
            settings.API_SIGNED_URL_SECRETKEY,
            settings.API_SIGNED_URL_SESSION_TOKEN or None,
        )

    def obtener_url_carga(self, clave_s3):
        return self._solicitar("GET", "putsignedurl", clave_s3)

    def obtener_url_descarga(self, clave_s3):
        return self._solicitar("GET", "getsignedurl", clave_s3)

    def eliminar_objeto(self, clave_s3):
        return self._solicitar("DELETE", "deleteobject", clave_s3, espera_url=False)

    def subir_bytes(self, clave_s3, contenido, content_type="application/octet-stream"):
        signed_url = self.obtener_url_carga(clave_s3)
        headers = obtener_headers_carga(signed_url, content_type)
        request = Request(
            signed_url,
            data=contenido,
            method="PUT",
            headers=headers,
        )
        self._abrir(request)

    def descargar_bytes(self, clave_s3, limite=None):
        signed_url = self.obtener_url_descarga(clave_s3)
        request = Request(signed_url, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                contenido = response.read(None if limite is None else limite + 1)
        except HTTPError as exc:
            raise self._error_http_seguro(exc) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ServicioCloudNoDisponible() from exc
        if limite is not None and len(contenido) > limite:
            raise ServicioCloudNoDisponible("El archivo cloud supera el limite permitido.")
        return contenido

    def _solicitar(self, metodo, recurso, clave_s3, espera_url=True):
        if not clave_s3 or clave_s3.startswith("/") or ".." in clave_s3.split("/"):
            raise ServicioCloudNoDisponible("La clave del archivo cloud no es valida.")
        url = f"{self.base_url}/{recurso}?{urlencode({'file': clave_s3})}"
        aws_request = AWSRequest(method=metodo, url=url)
        SigV4Auth(self.credentials, "execute-api", self.region).add_auth(aws_request)
        prepared = aws_request.prepare()
        request = Request(
            prepared.url,
            method=metodo,
            headers=dict(prepared.headers.items()),
        )
        raw = self._abrir(request)
        if not raw:
            return {} if not espera_url else self._respuesta_invalida()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ServicioCloudNoDisponible("El servicio cloud devolvio una respuesta invalida.") from exc
        if not espera_url:
            return payload
        signed_url = self._buscar_url(payload)
        if not signed_url:
            return self._respuesta_invalida()
        return signed_url

    def _abrir(self, request):
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise self._error_http_seguro(exc) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ServicioCloudNoDisponible() from exc

    @staticmethod
    def _buscar_url(payload):
        if not isinstance(payload, dict):
            return None
        for key in ("SignedURL", "signedURL", "signedUrl", "url"):
            if isinstance(payload.get(key), str):
                return payload[key]
        for key in ("data", "Data", "body"):
            nested = payload.get(key)
            if isinstance(nested, str):
                try:
                    nested = json.loads(nested)
                except json.JSONDecodeError:
                    continue
            result = AwsSignedURLService._buscar_url(nested)
            if result:
                return result
        return None

    @staticmethod
    def _respuesta_invalida():
        raise ServicioCloudNoDisponible("El servicio cloud no devolvio una URL temporal valida.")

    @staticmethod
    def _error_http_seguro(exc):
        codigo_servicio = None
        try:
            cuerpo = exc.read(4096)
            if cuerpo:
                try:
                    raiz = ElementTree.fromstring(cuerpo)
                    codigo_servicio = raiz.findtext("Code")
                except ElementTree.ParseError:
                    payload = json.loads(cuerpo.decode("utf-8"))
                    codigo_servicio = payload.get("code") or payload.get("Code")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            codigo_servicio = None
        referencia = codigo_servicio or f"HTTP_{exc.code}"
        return ServicioCloudNoDisponible(
            f"El servicio cloud rechazo la operacion ({referencia})."
        )

    @staticmethod
    def _validar_configuracion():
        requeridas = (
            settings.AWS_S3_ENABLED,
            settings.API_SIGNED_URL,
            settings.API_SIGNED_URL_ACCESSKEY,
            settings.API_SIGNED_URL_SECRETKEY,
            settings.API_SIGNED_URL_ZONE,
        )
        if not all(requeridas):
            raise ServicioCloudNoDisponible("El almacenamiento cloud no esta configurado.")


def obtener_headers_carga(signed_url, content_type_predeterminado="application/octet-stream"):
    parametros = parse_qs(urlsplit(signed_url).query)
    content_type = parametros.get("Content-Type", [content_type_predeterminado])[0]
    return {"Content-Type": content_type}
